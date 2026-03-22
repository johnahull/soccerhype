"""Shared utilities for the SoccerHype GUI package."""

import pathlib
import subprocess

ROOT = pathlib.Path.cwd()
ATHLETES = ROOT / "athletes"

_VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

# Import enhanced error handling
try:
    from utils.error_handling import (
        ErrorHandler, initialize_error_handling, error_handler,
        ValidationHelper, ProgressReporter
    )
    ERROR_HANDLING_AVAILABLE = True
except ImportError:
    ERROR_HANDLING_AVAILABLE = False


def _extract_video_frame(video_path: pathlib.Path) -> pathlib.Path | None:
    """Extract a single frame from a video for use as a slate preview image.

    Returns path to a temporary PNG, or None on failure.
    """
    import tempfile
    tmp_fd = tempfile.NamedTemporaryFile(suffix=".png", prefix="slate_preview_", delete=False)
    tmp = pathlib.Path(tmp_fd.name)
    tmp_fd.close()
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "1", "-i", str(video_path),
             "-frames:v", "1", "-q:v", "2", str(tmp)],
            capture_output=True, timeout=10,
        )
        if tmp.exists() and tmp.stat().st_size > 0:
            return tmp
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    # Clean up temp file on failure
    tmp.unlink(missing_ok=True)
    return None
