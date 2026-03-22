# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Shared utilities for the SoccerHype render package."""

from __future__ import annotations

import os
import pathlib
import platform
import shutil
import subprocess

# Import FFmpeg utilities for bundled binary detection
try:
    from ffmpeg_utils import get_ffmpeg_path, get_ffprobe_path
    _ffmpeg_path = get_ffmpeg_path()
    _ffprobe_path = get_ffprobe_path()
    FFMPEG_CMD = _ffmpeg_path or "ffmpeg"
    FFPROBE_CMD = _ffprobe_path or "ffprobe"
except ImportError:
    FFMPEG_CMD = "ffmpeg"
    FFPROBE_CMD = "ffprobe"

# Import structure detection utilities
from utils.structure import (
    is_v2_structure,
    list_projects,
    get_project_data,
)

ROOT = pathlib.Path.cwd()
ATHLETES = ROOT / "athletes"

# Render / proxy params
FPS = 30
CRF = 18
PROXY_W = 1920
VIDEO_ONLY = True


def escape_drawtext(text: str) -> str:
    """Escape special characters for FFmpeg drawtext filter."""
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("%", "\\%")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    text = text.replace("'", "'\\''")
    return text


def find_dejavu_font() -> str:
    """Find DejaVu Sans Bold font across different platforms."""
    system = platform.system()

    candidates = []
    allowed_dirs = []

    if system == "Linux":
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        ]
        allowed_dirs = ["/usr/share/fonts", "/usr/local/share/fonts"]
    elif system == "Darwin":
        candidates = [
            "/System/Library/Fonts/Supplemental/DejaVuSans-Bold.ttf",
            "/Library/Fonts/DejaVuSans-Bold.ttf",
            str(pathlib.Path.home() / "Library/Fonts/DejaVuSans-Bold.ttf"),
        ]
        allowed_dirs = ["/System/Library/Fonts", "/Library/Fonts",
                       str(pathlib.Path.home() / "Library/Fonts")]
    elif system == "Windows":
        candidates = [
            "C:/Windows/Fonts/DejaVuSans-Bold.ttf",
            str(pathlib.Path.home() / "AppData/Local/Microsoft/Windows/Fonts/DejaVuSans-Bold.ttf"),
        ]
        allowed_dirs = ["C:/Windows/Fonts", "C:\\Windows\\Fonts",
                       str(pathlib.Path.home() / "AppData/Local/Microsoft/Windows/Fonts")]

    for font_path in candidates:
        font_file = pathlib.Path(font_path).resolve()
        if font_file.exists():
            if font_file.suffix.lower() not in ['.ttf', '.otf', '.ttc']:
                continue
            if not os.access(font_file, os.R_OK):
                continue
            font_str = str(font_file)
            if not any(font_str.startswith(allowed_dir) for allowed_dir in allowed_dirs):
                continue
            return str(font_file)

    print("Warning: DejaVu Sans Bold font not found, using FFmpeg default font")
    return ""


def run(cmd_list):
    """Run a command and raise on failure."""
    print("•", " ".join(map(str, cmd_list)))
    if subprocess.call(cmd_list) != 0:
        raise RuntimeError("Command failed")


def find_athletes() -> list[pathlib.Path]:
    """Find all athlete directories."""
    if not ATHLETES.exists():
        return []
    return sorted([p for p in ATHLETES.iterdir() if p.is_dir()])


def choose_athlete_interactive() -> pathlib.Path | None:
    """Interactively choose an athlete directory."""
    options = find_athletes()
    if not options:
        print("No athlete folders found under ./athletes/")
        return None
    print("\nSelect an athlete:")
    for i, p in enumerate(options, 1):
        if is_v2_structure(p):
            projects = list_projects(p)
            print(f"  {i}. {p.name} ({len(projects)} project{'s' if len(projects) != 1 else ''})")
        else:
            print(f"  {i}. {p.name}")
    print("  q. Quit")
    while True:
        choice = input("Enter number: ").strip().lower()
        if choice in ("q", "quit", "exit"):
            return None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        print("Invalid choice. Try again.")


def choose_project_interactive(athlete_dir: pathlib.Path) -> pathlib.Path | None:
    """Choose a project interactively for v2 athletes."""
    projects = list_projects(athlete_dir)

    if not projects:
        print(f"No projects found for {athlete_dir.name}")
        print(f"Create one with: python create_project.py --athlete \"{athlete_dir.name}\" --project \"Project Name\"")
        return None

    if len(projects) == 1:
        print(f"Using project: {projects[0].name}")
        return projects[0]

    print(f"\nSelect a project for {athlete_dir.name}:")
    for i, p in enumerate(projects, 1):
        project_data = get_project_data(p)
        clips = project_data.get("clips", [])
        final_exists = (p / "output" / "final.mp4").exists()
        status = "✓ Done" if final_exists else f"{len(clips)} clips"
        print(f"  {i}. {p.name} ({status})")

    print("  q. Quit")

    while True:
        choice = input("Enter number: ").strip().lower()
        if choice in ("q", "quit", "exit"):
            return None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(projects):
                return projects[idx - 1]
        print("Invalid choice. Try again.")


def ensure_dirs(base: pathlib.Path):
    """Ensure work and output directories exist."""
    (base / "work" / "proxies").mkdir(parents=True, exist_ok=True)
    (base / "output").mkdir(exist_ok=True)


def clear_work_dir(work: pathlib.Path):
    """Remove all files in the work directory."""
    for p in work.glob("*"):
        try:
            p.unlink()
        except IsADirectoryError:
            shutil.rmtree(p)


def resolve_path(base: pathlib.Path, p: str | None) -> pathlib.Path | None:
    """Resolve a relative path against a base directory."""
    if not p:
        return None
    path = pathlib.Path(p)
    return path if path.is_absolute() else (base / path)
