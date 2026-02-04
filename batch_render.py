#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
# batch_render.py
# Batch runner for multi-athlete render_highlight.py
#
# Supports both v1 (legacy) and v2 (multi-project) folder structures.
# For v2 athletes, iterates through all projects.

import argparse
import pathlib
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

from utils.structure import (
    is_v2_structure,
    list_projects,
    get_project_data,
)

ROOT = pathlib.Path.cwd()
ATHLETES = ROOT / "athletes"


def discover_render_targets(names=None) -> List[Tuple[pathlib.Path, str]]:
    """
    Discover all render targets (project directories).

    For v1 athletes: Returns the athlete directory
    For v2 athletes: Returns each project directory

    Returns:
        List of (project_dir, display_name) tuples
    """
    targets = []

    if names:
        athlete_dirs = [ATHLETES / n for n in names]
    else:
        athlete_dirs = sorted([p for p in ATHLETES.iterdir() if p.is_dir()])

    for athlete_dir in athlete_dirs:
        if not athlete_dir.exists():
            continue

        if is_v2_structure(athlete_dir):
            # v2: Add each project as a separate target
            projects = list_projects(athlete_dir)
            for project_dir in projects:
                display_name = f"{athlete_dir.name}/{project_dir.name}"
                targets.append((project_dir, display_name))
        else:
            # v1: Athlete dir is the project
            targets.append((athlete_dir, athlete_dir.name))

    return targets


def discover_athletes(names=None):
    """Legacy function for backward compatibility."""
    if names:
        return [ATHLETES / n for n in names]
    return sorted([p for p in ATHLETES.iterdir() if p.is_dir()])


def should_skip(project_dir: pathlib.Path, display_name: str, force: bool) -> bool:
    proj = project_dir / "project.json"
    out = project_dir / "output" / "final.mp4"
    if not proj.exists():
        print(f"⏭️  Skip (no project.json): {display_name}")
        return True
    if out.exists() and not force:
        print(f"⏭️  Skip (final exists, use --force to re-render): {display_name}")
        return True
    return False


def render_one(project_dir: pathlib.Path, display_name: str, keep_work: bool, python: str) -> tuple[str, int]:
    cmd = [python, "render_highlight.py", "--dir", str(project_dir)]
    if keep_work:
        cmd.append("--keep-work")
    print("•", " ".join(cmd))
    proc = subprocess.run(cmd)
    return (display_name, proc.returncode)

def main():
    ap = argparse.ArgumentParser(description="Batch render all/selected athletes and projects.")
    ap.add_argument("--names", nargs="*", help="Specific athlete folder names under ./athletes")
    ap.add_argument("--jobs", type=int, default=1, help="Parallel renders (default 1)")
    ap.add_argument("--keep-work", action="store_true", help="Keep intermediates")
    ap.add_argument("--force", action="store_true", help="Re-render even if final.mp4 exists")
    ap.add_argument("--dry-run", action="store_true", help="List targets without running")
    ap.add_argument("--python", default="python", help="Python executable to run render_highlight.py")
    args = ap.parse_args()

    if not ATHLETES.exists():
        print("No ./athletes directory found.")
        return

    # Discover all render targets (supports both v1 and v2 structures)
    all_targets = discover_render_targets(args.names)
    if not all_targets:
        print("No athlete/project folders found to process.")
        return

    # Filter by presence of project.json / final.mp4 unless --force
    queue = [(project_dir, display_name)
             for project_dir, display_name in all_targets
             if not should_skip(project_dir, display_name, args.force)]

    if not queue:
        print("Nothing to do.")
        return

    print(f"\nBatch size: {len(queue)}  |  Parallel jobs: {args.jobs}\n")

    if args.dry_run:
        for project_dir, display_name in queue:
            print(f"DRY RUN → would render: {display_name}")
        return

    if args.jobs <= 1:
        # Sequential (safest, uses all cores per ffmpeg job)
        failures = 0
        for project_dir, display_name in queue:
            name, rc = render_one(project_dir, display_name, args.keep_work, args.python)
            if rc != 0:
                print(f"❌ Failed: {name} (rc={rc})")
                failures += 1
        print(f"\n✅ Done. {len(queue)-failures} succeeded, {failures} failed.")
    else:
        # Parallel (be mindful of CPU/GPU/IO load)
        failures = 0
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            futs = [ex.submit(render_one, project_dir, display_name, args.keep_work, args.python)
                    for project_dir, display_name in queue]
            for fut in as_completed(futs):
                name, rc = fut.result()
                if rc == 0:
                    print(f"✔ Success: {name}")
                else:
                    print(f"❌ Failed: {name} (rc={rc})")
                    failures += 1
        print(f"\n✅ Done. {len(queue)-failures} succeeded, {failures} failed.")

if __name__ == "__main__":
    main()

