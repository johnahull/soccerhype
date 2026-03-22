# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Proxy generation and video probing utilities."""

from __future__ import annotations

import pathlib
import subprocess

from render.utils import FFMPEG_CMD, FFPROBE_CMD, FPS, CRF, PROXY_W


def duration_of(path: pathlib.Path) -> float:
    """Get duration of a video file in seconds."""
    p = subprocess.run(
        [FFPROBE_CMD, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nk=1:nw=1", str(path)],
        capture_output=True, text=True
    )
    try:
        return float(p.stdout.strip())
    except Exception:
        return 0.0


def proxy_fps(path: pathlib.Path) -> float:
    """Get the frame rate of a proxy video."""
    p = subprocess.run(
        [FFPROBE_CMD, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=avg_frame_rate",
         "-of", "default=nk=1:nw=1", str(path)],
        capture_output=True, text=True
    )
    s = p.stdout.strip()
    if "/" in s:
        a, b = s.split("/")
        try:
            return float(a) / float(b)
        except Exception:
            pass
    try:
        return float(s)
    except Exception:
        return 30.0


def proxy_frame_count(path: pathlib.Path) -> int:
    """Get total frame count of a proxy video."""
    p = subprocess.run(
        [FFPROBE_CMD, "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=nb_read_frames",
         "-of", "default=nk=1:nw=1", str(path)],
        capture_output=True, text=True
    )
    txt = p.stdout.strip()
    if txt.isdigit():
        return int(txt)
    fps = proxy_fps(path)
    dur = duration_of(path)
    return max(1, int(round(fps * dur)))


def to_frame(t: float, fps: float) -> int:
    """Convert time in seconds to frame number."""
    return max(0, int(round(t * fps)))


def ensure_proxy(src_path: pathlib.Path, std_path: pathlib.Path):
    """Create standardized proxy if it doesn't exist."""
    std_path.parent.mkdir(parents=True, exist_ok=True)
    if std_path.exists():
        return
    if not src_path.exists():
        raise RuntimeError(f"Source clip not found: {src_path}")

    cmd = [
        FFMPEG_CMD, "-y",
        "-i", str(src_path),
        "-vf", f"scale={PROXY_W}:-2,fps={FPS}",
        "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(CRF),
        "-pix_fmt", "yuv420p",
        str(std_path)
    ]
    print("•", " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        print(proc.stdout)
        raise RuntimeError(f"Failed to build proxy for {src_path}")
