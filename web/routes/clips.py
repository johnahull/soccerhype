# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Clip management API endpoints: upload, stream, marks, thumbnails."""

from __future__ import annotations

import pathlib
import subprocess
import shutil

from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Any, Optional

from utils.structure import (
    detect_structure,
    is_v2_structure,
    list_projects,
    get_project_data,
    save_project_data,
    resolve_athlete_dir,
)
from clip_sync import is_clip_marked, sync_clips, VIDEO_EXTS
from render.proxy import ensure_proxy, duration_of
from render.utils import FFMPEG_CMD, FFPROBE_CMD, PROXY_W, FPS, CRF

ROOT = pathlib.Path.cwd()
ATHLETES = ROOT / "athletes"

router = APIRouter()


class MarkData(BaseModel):
    marker_x_std: int
    marker_y_std: int
    radius_std: int = 72
    spot_time: float
    spot_frame_std: int
    start_trim: float = 0.0
    end_trim: float = 0.0
    zoom_std: float = 1.0
    section: Optional[str] = None


class OrderBody(BaseModel):
    filenames: list[str]


def _resolve_project(athlete: str, project: str) -> pathlib.Path:
    """Resolve and validate a project directory path."""
    safe_a = pathlib.Path(athlete)
    safe_p = pathlib.Path(project)
    if safe_a.parts != (athlete,) or safe_p.parts != (project,):
        raise HTTPException(400, "Invalid path components")

    athlete_dir = (ATHLETES / athlete).resolve()
    if not str(athlete_dir).startswith(str(ATHLETES.resolve())):
        raise HTTPException(400, "Invalid athlete name")
    if not athlete_dir.exists():
        raise HTTPException(404, f"Athlete '{athlete}' not found")

    structure = detect_structure(athlete_dir)
    if structure == "v2":
        project_dir = (athlete_dir / "projects" / project).resolve()
        if not str(project_dir).startswith(str(athlete_dir.resolve())):
            raise HTTPException(400, "Invalid project name")
    else:
        project_dir = athlete_dir

    if not project_dir.exists():
        raise HTTPException(404, f"Project '{project}' not found")
    return project_dir


@router.get("/projects/{athlete}/{project}/clips")
async def list_clips(athlete: str, project: str):
    """List clips with mark status."""
    project_dir = _resolve_project(athlete, project)
    data = get_project_data(project_dir)
    clips = data.get("clips", [])

    results = []
    for i, clip in enumerate(clips):
        file_path = clip.get("file", "")
        filename = pathlib.Path(file_path).name if file_path else f"clip_{i}"
        results.append({
            "index": i,
            "filename": filename,
            "marked": is_clip_marked(clip),
            "marker_x_std": clip.get("marker_x_std"),
            "marker_y_std": clip.get("marker_y_std"),
            "radius_std": clip.get("radius_std"),
            "spot_time": clip.get("spot_time"),
            "spot_frame_std": clip.get("spot_frame_std"),
            "start_trim": clip.get("start_trim", 0.0),
            "end_trim": clip.get("end_trim", 0.0),
            "zoom_std": clip.get("zoom_std", 1.0),
            "section": clip.get("section"),
            "missing": clip.get("_missing", False),
        })
    return results


@router.post("/projects/{athlete}/{project}/upload")
async def upload_clips(athlete: str, project: str, files: list[UploadFile] = File(...)):
    """Upload clip files to the project's clips_in/ folder."""
    project_dir = _resolve_project(athlete, project)
    clips_in = project_dir / "clips_in"
    clips_in.mkdir(parents=True, exist_ok=True)

    uploaded = []
    for f in files:
        ext = pathlib.Path(f.filename).suffix.lower()
        if ext not in VIDEO_EXTS:
            continue

        safe_name = pathlib.Path(f.filename).name
        if "/" in safe_name or "\\" in safe_name:
            continue

        dest = clips_in / safe_name
        with open(dest, "wb") as out:
            shutil.copyfileobj(f.file, out)
        uploaded.append(safe_name)

    # Sync clips after upload
    project_json = project_dir / "project.json"
    if project_json.exists():
        result = sync_clips(project_dir, save=True)
    else:
        result = {"added": uploaded, "removed": [], "unchanged": []}

    return {"uploaded": uploaded, "sync": result}


@router.post("/projects/{athlete}/{project}/sync")
async def sync_project_clips(athlete: str, project: str):
    """Sync clips_in/ folder with project.json."""
    project_dir = _resolve_project(athlete, project)
    try:
        result = sync_clips(project_dir, save=True)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(400, str(e))
    return result


@router.put("/projects/{athlete}/{project}/order")
async def save_clip_order(athlete: str, project: str, body: OrderBody):
    """Save clip order based on filename list."""
    project_dir = _resolve_project(athlete, project)
    data = get_project_data(project_dir)
    clips = data.get("clips", [])

    # Build lookup by filename
    by_name = {}
    for clip in clips:
        file_path = clip.get("file", "")
        name = pathlib.Path(file_path).name if file_path else ""
        if name:
            by_name[name] = clip

    # Reorder
    reordered = []
    for fname in body.filenames:
        if fname in by_name:
            reordered.append(by_name.pop(fname))

    # Append any remaining clips not in the new order
    reordered.extend(by_name.values())

    data["clips"] = reordered
    save_project_data(project_dir, data)
    return {"ok": True, "count": len(reordered)}


@router.get("/projects/{athlete}/{project}/clip/{idx}/video")
async def stream_video(athlete: str, project: str, idx: int, request: Request):
    """Stream proxy video file with range request support."""
    project_dir = _resolve_project(athlete, project)
    data = get_project_data(project_dir)
    clips = data.get("clips", [])

    if idx < 0 or idx >= len(clips):
        raise HTTPException(404, "Clip index out of range")

    clip = clips[idx]

    # Ensure proxy exists
    src_path = clip.get("file")
    if not src_path:
        raise HTTPException(404, "Clip has no source file")

    src = pathlib.Path(src_path)
    if not src.is_absolute():
        src = project_dir / src

    # Validate path is within project
    if not str(src.resolve()).startswith(str(project_dir.resolve())):
        raise HTTPException(400, "Invalid file path")

    if not src.exists():
        raise HTTPException(404, f"Source file not found: {src.name}")

    # Build proxy path
    std_file = clip.get("std_file")
    if std_file:
        proxy = pathlib.Path(std_file)
        if not proxy.is_absolute():
            proxy = project_dir / proxy
    else:
        proxy = project_dir / "work" / "proxies" / f"clip{idx+1:02d}_std.mp4"

    try:
        ensure_proxy(src, proxy)
    except RuntimeError as e:
        raise HTTPException(500, f"Proxy generation failed: {e}")

    # Update std_file in project data if not set
    if not std_file:
        clip["std_file"] = str(proxy.relative_to(project_dir))
        save_project_data(project_dir, data)

    if not proxy.exists():
        raise HTTPException(404, "Proxy file not found")

    file_size = proxy.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        # Parse range header
        range_spec = range_header.replace("bytes=", "")
        parts = range_spec.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if parts[1] else file_size - 1
        end = min(end, file_size - 1)
        length = end - start + 1

        def iter_range():
            with open(proxy, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(8192, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return StreamingResponse(
            iter_range(),
            status_code=206,
            media_type="video/mp4",
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
            },
        )

    return FileResponse(
        str(proxy),
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"},
    )


@router.get("/projects/{athlete}/{project}/clip/{idx}/thumb")
async def get_thumbnail(athlete: str, project: str, idx: int):
    """Get or generate thumbnail for a clip."""
    project_dir = _resolve_project(athlete, project)
    data = get_project_data(project_dir)
    clips = data.get("clips", [])

    if idx < 0 or idx >= len(clips):
        raise HTTPException(404, "Clip index out of range")

    clip = clips[idx]
    thumb_dir = project_dir / "work" / "thumbs"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = thumb_dir / f"thumb_{idx:03d}.jpg"

    if not thumb_path.exists():
        # Find source video
        src_path = clip.get("file")
        if not src_path:
            raise HTTPException(404, "No source file")
        src = pathlib.Path(src_path)
        if not src.is_absolute():
            src = project_dir / src
        if not src.exists():
            raise HTTPException(404, "Source file not found")

        # Generate thumbnail at 1 second mark
        cmd = [
            FFMPEG_CMD, "-y", "-ss", "1", "-i", str(src),
            "-vframes", "1", "-vf", "scale=320:-2",
            "-q:v", "5", str(thumb_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=30)
        if proc.returncode != 0 or not thumb_path.exists():
            # Try at 0 seconds
            cmd[3] = "0"
            subprocess.run(cmd, capture_output=True, timeout=30)

    if not thumb_path.exists():
        raise HTTPException(500, "Thumbnail generation failed")

    return FileResponse(str(thumb_path), media_type="image/jpeg")


@router.put("/projects/{athlete}/{project}/clip/{idx}/mark")
async def save_mark(athlete: str, project: str, idx: int, mark: MarkData):
    """Save mark data for a clip."""
    project_dir = _resolve_project(athlete, project)
    data = get_project_data(project_dir)
    clips = data.get("clips", [])

    if idx < 0 or idx >= len(clips):
        raise HTTPException(404, "Clip index out of range")

    clip = clips[idx]
    clip["marker_x_std"] = mark.marker_x_std
    clip["marker_y_std"] = mark.marker_y_std
    clip["radius_std"] = mark.radius_std
    clip["spot_time"] = mark.spot_time
    clip["spot_frame_std"] = mark.spot_frame_std
    clip["start_trim"] = mark.start_trim
    clip["end_trim"] = mark.end_trim
    clip["zoom_std"] = mark.zoom_std
    clip["marked"] = True
    if mark.section is not None:
        clip["section"] = mark.section

    save_project_data(project_dir, data)
    return {"ok": True, "index": idx}


@router.get("/projects/{athlete}/{project}/clip/{idx}/duration")
async def get_clip_duration(athlete: str, project: str, idx: int):
    """Get duration info for a clip."""
    project_dir = _resolve_project(athlete, project)
    data = get_project_data(project_dir)
    clips = data.get("clips", [])

    if idx < 0 or idx >= len(clips):
        raise HTTPException(404, "Clip index out of range")

    clip = clips[idx]
    std_file = clip.get("std_file")
    if std_file:
        proxy = pathlib.Path(std_file)
        if not proxy.is_absolute():
            proxy = project_dir / proxy
        if proxy.exists():
            dur = duration_of(proxy)
            return {"duration": dur, "fps": FPS}

    src_path = clip.get("file")
    if src_path:
        src = pathlib.Path(src_path)
        if not src.is_absolute():
            src = project_dir / src
        if src.exists():
            dur = duration_of(src)
            return {"duration": dur, "fps": FPS}

    return {"duration": 0, "fps": FPS}
