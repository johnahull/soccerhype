#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
# clip_sync.py — Sync clips_in/ folder with project.json
#
# This module enables adding/removing clips without losing marking data.
# It compares the current clips_in/ contents with project.json and:
# - Detects new clips (in folder but not in project) -> adds placeholder entries
# - Detects removed clips (in project but not in folder) -> removes entries
# - Preserves existing marking data for unchanged clips
#
# Usage:
#   from clip_sync import sync_clips, is_clip_marked
#   result = sync_clips(athlete_base_path)
#   # result = {"added": [...], "removed": [...], "unchanged": [...]}

from __future__ import annotations

import json
import pathlib
import tempfile
from typing import Dict, List, Any

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi"}


def is_clip_marked(clip: Dict[str, Any]) -> bool:
    """Check if a clip has complete marking data.

    A clip is considered marked if it has all required marking fields:
    - marker_x_std, marker_y_std: Player position coordinates
    - spot_time: When to show the freeze-frame ring

    Returns:
        True if the clip has complete marking data, False otherwise.
    """
    required_fields = ['marker_x_std', 'marker_y_std', 'spot_time']
    return all(field in clip and clip[field] is not None for field in required_fields)


def get_clip_filename(clip: Dict[str, Any]) -> str:
    """Extract the filename from a clip entry.

    Handles both 'file' and 'std_file' paths, preferring 'file' as the
    canonical source filename.
    """
    file_path = clip.get("file") or clip.get("std_file") or ""
    return pathlib.Path(file_path).name


def list_clips_in_folder(clips_in: pathlib.Path) -> List[pathlib.Path]:
    """List all video files in the clips_in folder."""
    if not clips_in.exists():
        return []
    return sorted([p for p in clips_in.iterdir()
                   if p.is_file() and p.suffix.lower() in VIDEO_EXTS])


def create_placeholder_clip(file_path: pathlib.Path) -> Dict[str, Any]:
    """Create a placeholder clip entry for an unmarked clip.

    This creates a minimal entry that will be detected as unmarked
    by is_clip_marked() and processed by mark_play.py.
    """
    return {
        "file": str(file_path),
        "std_file": None,
        "marked": False
    }


def sync_clips(base: pathlib.Path, save: bool = True, auto_remove: bool = False) -> Dict[str, List[str]]:
    """Sync clips_in/ folder with project.json.

    Compares current clips_in/ contents with project.json clips list:
    - New clips (in folder but not in project): Added as placeholder entries
    - Removed clips (in project but not in folder): Removed from project
    - Existing clips: Preserved with their marking data

    Args:
        base: Path to the athlete directory (contains clips_in/ and project.json)
        save: If True, save the updated project.json (default: True)
        auto_remove: If True, silently remove clips whose files are missing.
                     If False (default), keep clip data with _missing flag to prevent data loss.

    Returns:
        Dictionary with sync results:
        {
            "added": [list of filenames added],
            "removed": [list of filenames removed],
            "unchanged": [list of filenames unchanged]
        }

    Raises:
        FileNotFoundError: If project.json doesn't exist
        ValueError: If clips_in/ directory doesn't exist
    """
    clips_in = base / "clips_in"
    project_path = base / "project.json"

    # Validate paths
    if not clips_in.exists():
        raise ValueError(f"clips_in/ directory not found: {clips_in}")

    if not project_path.exists():
        raise FileNotFoundError(f"project.json not found: {project_path}")

    # Load project data
    project = json.loads(project_path.read_text())
    existing_clips = project.get("clips", [])

    # Build map of existing clips by filename
    existing_by_name: Dict[str, Dict[str, Any]] = {}
    for clip in existing_clips:
        filename = get_clip_filename(clip)
        if filename:
            existing_by_name[filename] = clip

    # Get current files in clips_in/
    current_files = list_clips_in_folder(clips_in)
    current_filenames = {f.name for f in current_files}
    existing_filenames = set(existing_by_name.keys())

    # Calculate differences
    added_filenames = current_filenames - existing_filenames
    removed_filenames = existing_filenames - current_filenames
    unchanged_filenames = current_filenames & existing_filenames

    # Build new clips list preserving order of existing clips
    # then appending new clips at the end
    new_clips: List[Dict[str, Any]] = []

    # First, preserve existing clips in their original order
    for clip in existing_clips:
        filename = get_clip_filename(clip)
        if filename in unchanged_filenames:
            # Clip still exists - keep it
            new_clips.append(clip)
        elif filename in removed_filenames and not auto_remove:
            # Clip file missing but auto_remove=False - keep clip data (preserve marks)
            # Mark as missing so UI can warn user
            clip_copy = clip.copy()
            clip_copy["_missing"] = True
            new_clips.append(clip_copy)
        # If auto_remove=True, removed clips are silently dropped

    # Then append new clips
    for file_path in current_files:
        if file_path.name in added_filenames:
            new_clips.append(create_placeholder_clip(file_path))

    # Update project
    project["clips"] = new_clips

    # Save if requested (using atomic write for safety)
    if save:
        _atomic_write_json(project_path, project)

    return {
        "added": sorted(list(added_filenames)),
        "removed": sorted(list(removed_filenames)),
        "unchanged": sorted(list(unchanged_filenames))
    }


def _atomic_write_json(path: pathlib.Path, data: Dict[str, Any]) -> None:
    """Write JSON data atomically using temp file + rename pattern."""
    # Write to temp file in same directory (ensures same filesystem for rename)
    temp_fd = None
    temp_path = None
    try:
        temp_fd, temp_path_str = tempfile.mkstemp(
            dir=path.parent,
            prefix=".project_",
            suffix=".json.tmp"
        )
        temp_path = pathlib.Path(temp_path_str)

        # Write data
        import os
        os.write(temp_fd, json.dumps(data, indent=2).encode('utf-8'))
        os.close(temp_fd)
        temp_fd = None

        # Atomic rename
        temp_path.replace(path)
    finally:
        if temp_fd is not None:
            import os
            os.close(temp_fd)
        if temp_path and temp_path.exists():
            temp_path.unlink()


def get_sync_summary_message(result: Dict[str, List[str]]) -> str:
    """Generate a human-readable summary of sync results.

    Args:
        result: The result dictionary from sync_clips()

    Returns:
        A formatted message string describing the sync results.
    """
    added_count = len(result["added"])
    removed_count = len(result["removed"])
    unchanged_count = len(result["unchanged"])

    if added_count == 0 and removed_count == 0:
        return f"No changes detected ({unchanged_count} clips up to date)"

    parts = []
    if added_count > 0:
        parts.append(f"+{added_count} added")
    if removed_count > 0:
        parts.append(f"-{removed_count} removed")

    return f"Synced: {', '.join(parts)} ({unchanged_count} unchanged)"


# CLI interface for standalone usage
if __name__ == "__main__":
    import argparse
    import sys

    ROOT = pathlib.Path.cwd()
    ATHLETES = ROOT / "athletes"

    def find_athletes() -> List[pathlib.Path]:
        if not ATHLETES.exists():
            return []
        return sorted([p for p in ATHLETES.iterdir() if p.is_dir()])

    def choose_athlete_interactive() -> pathlib.Path | None:
        options = find_athletes()
        if not options:
            print("No athlete folders found under ./athletes/")
            return None
        print("\nSelect an athlete:")
        for i, p in enumerate(options, 1):
            print(f"  {i}. {p.name}")
        print("  q. Quit")
        while True:
            choice = input("Enter number: ").strip().lower()
            if choice in ("q", "quit", "exit"):
                return None
            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(options):
                    return options[idx-1]
            print("Invalid choice. Try again.")

    ap = argparse.ArgumentParser(
        description="Sync clips_in/ folder with project.json"
    )
    ap.add_argument("--athlete", type=str, help="Athlete folder name under ./athletes")
    ap.add_argument("--dir", type=str, help="Full path to athlete folder")
    ap.add_argument("--dry-run", action="store_true", help="Show what would change without saving")
    args = ap.parse_args()

    # Resolve athlete directory
    if args.dir:
        base = pathlib.Path(args.dir).resolve()
    elif args.athlete:
        base = (ATHLETES / args.athlete).resolve()
    else:
        base = choose_athlete_interactive()
        if base is None:
            sys.exit(0)

    if not base.exists() or not base.is_dir():
        print(f"Invalid athlete directory: {base}")
        sys.exit(1)

    try:
        result = sync_clips(base, save=not args.dry_run)

        print(f"\n{get_sync_summary_message(result)}")

        if result["added"]:
            print("\nAdded clips:")
            for name in result["added"]:
                print(f"  + {name}")

        if result["removed"]:
            print("\nRemoved clips:")
            for name in result["removed"]:
                print(f"  - {name}")

        if args.dry_run:
            print("\n(Dry run - no changes saved)")
        else:
            print(f"\nproject.json updated: {base / 'project.json'}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Run mark_play.py first to create initial project.json")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
