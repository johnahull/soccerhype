# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Render job API endpoints with WebSocket progress."""

from __future__ import annotations

import asyncio
import json
import pathlib
import re
import subprocess
import sys
import threading

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from utils.structure import (
    detect_structure,
    get_project_data,
    resolve_athlete_dir,
)

ROOT = pathlib.Path.cwd()
ATHLETES = ROOT / "athletes"

router = APIRouter()

# Track active render jobs: key = "athlete/project"
_render_jobs: dict[str, dict] = {}


def _resolve_project(athlete: str, project: str) -> pathlib.Path:
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
    else:
        project_dir = athlete_dir

    if not project_dir.exists():
        raise HTTPException(404, f"Project '{project}' not found")
    return project_dir


def _run_render(athlete: str, project: str, project_dir: pathlib.Path):
    """Run render in a background thread, updating job status."""
    job_key = f"{athlete}/{project}"
    job = _render_jobs[job_key]

    try:
        # Build render command
        cmd = [sys.executable, "render_highlight.py", "--dir", str(project_dir), "--keep-work"]
        job["status"] = "running"
        job["progress"] = 0

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(ROOT),
        )
        job["pid"] = proc.pid

        output_lines = []
        clip_pattern = re.compile(r"clip\s*(\d+)", re.IGNORECASE)
        data = get_project_data(project_dir)
        total_clips = len(data.get("clips", []))

        for line in proc.stdout:
            line = line.strip()
            if line:
                output_lines.append(line)
                job["output"] = output_lines[-20:]  # Keep last 20 lines

                # Estimate progress from clip processing
                match = clip_pattern.search(line)
                if match and total_clips > 0:
                    clip_num = int(match.group(1))
                    job["progress"] = min(95, int(clip_num / total_clips * 90))

        proc.wait()

        if proc.returncode == 0:
            final = project_dir / "output" / "final.mp4"
            if final.exists():
                job["status"] = "done"
                job["progress"] = 100
            else:
                job["status"] = "error"
                job["error"] = "Render completed but output file not found"
        else:
            job["status"] = "error"
            job["error"] = "\n".join(output_lines[-5:])

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


@router.post("/projects/{athlete}/{project}/render")
async def start_render(athlete: str, project: str):
    """Start a render job."""
    project_dir = _resolve_project(athlete, project)
    job_key = f"{athlete}/{project}"

    # Check if already rendering
    if job_key in _render_jobs and _render_jobs[job_key]["status"] == "running":
        raise HTTPException(409, "Render already in progress")

    # Verify clips exist and are marked
    data = get_project_data(project_dir)
    clips = data.get("clips", [])
    if not clips:
        raise HTTPException(400, "No clips to render")

    _render_jobs[job_key] = {
        "status": "starting",
        "progress": 0,
        "output": [],
        "error": None,
        "pid": None,
    }

    thread = threading.Thread(
        target=_run_render,
        args=(athlete, project, project_dir),
        daemon=True,
    )
    thread.start()

    return {"status": "started", "job_key": job_key}


@router.get("/projects/{athlete}/{project}/render/status")
async def render_status(athlete: str, project: str):
    """Get render job status (polling fallback)."""
    job_key = f"{athlete}/{project}"
    if job_key not in _render_jobs:
        # Check if output exists from a previous render
        project_dir = _resolve_project(athlete, project)
        final = project_dir / "output" / "final.mp4"
        if final.exists():
            return {"status": "done", "progress": 100}
        return {"status": "idle", "progress": 0}
    return _render_jobs[job_key]


@router.websocket("/projects/{athlete}/{project}/render/ws")
async def render_ws(websocket: WebSocket, athlete: str, project: str):
    """WebSocket for real-time render progress updates."""
    await websocket.accept()
    job_key = f"{athlete}/{project}"

    try:
        last_progress = -1
        last_status = ""
        while True:
            if job_key in _render_jobs:
                job = _render_jobs[job_key]
                if job["progress"] != last_progress or job["status"] != last_status:
                    last_progress = job["progress"]
                    last_status = job["status"]
                    await websocket.send_json({
                        "status": job["status"],
                        "progress": job["progress"],
                        "output": job.get("output", []),
                        "error": job.get("error"),
                    })
                if job["status"] in ("done", "error"):
                    break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass


@router.get("/projects/{athlete}/{project}/output")
async def download_output(athlete: str, project: str):
    """Download the rendered final.mp4."""
    project_dir = _resolve_project(athlete, project)
    final = project_dir / "output" / "final.mp4"
    if not final.exists():
        raise HTTPException(404, "No rendered output found. Render first.")
    return FileResponse(
        str(final),
        media_type="video/mp4",
        filename=f"{athlete}_{project}_highlight.mp4",
    )
