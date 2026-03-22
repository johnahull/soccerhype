# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Core rendering logic and CLI entry point."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

from utils.structure import (
    detect_structure,
    is_v2_structure,
    resolve_athlete_dir,
    resolve_project_dir,
    get_project_data,
    list_projects,
    get_intro_dir,
    get_merged_project_data,
)
from constants import SECTIONS, OVERLAY_DURATION_DEFAULT, OVERLAY_DURATION_MIN, OVERLAY_MARGIN

from render.utils import (
    ATHLETES, ensure_dirs, clear_work_dir, resolve_path,
    choose_athlete_interactive, choose_project_interactive,
)
from render.proxy import ensure_proxy, proxy_fps, to_frame, duration_of
from render.slate import find_intro_files, choose_intro_media, make_slate
from render.video import (
    make_freeze_with_spot, add_lower_third_overlay, concat_videos,
)


def main():
    from version import __version__
    ap = argparse.ArgumentParser(description="Render highlights for an athlete (audio-free)")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.add_argument("--athlete", type=str, help="Athlete folder name under ./athletes")
    ap.add_argument("--project", type=str, help="Project name (for v2 multi-project athletes)")
    ap.add_argument("--dir", type=str, help="Full path to athlete or project folder")
    ap.add_argument("--keep-work", action="store_true")
    ap.add_argument("--reset-intro", action="store_true", help="Reset intro media selection")
    ap.add_argument("--slate-template", type=str, default=None,
                    help="Slate template name (classic, modern, bold, cinematic, clean)")
    args = ap.parse_args()

    athlete_dir = None
    project_dir = None

    if args.dir:
        given_path = pathlib.Path(args.dir).resolve()
        if not given_path.exists() or not given_path.is_dir():
            print(f"Invalid directory: {given_path}")
            sys.exit(1)

        athlete_dir = resolve_athlete_dir(given_path)
        if athlete_dir is None:
            print(f"Could not determine athlete from path: {given_path}")
            sys.exit(1)

        if is_v2_structure(athlete_dir):
            project_dir = resolve_project_dir(given_path)
            if project_dir is None:
                project_dir = choose_project_interactive(athlete_dir)
                if project_dir is None:
                    sys.exit(0)
        else:
            project_dir = athlete_dir

    elif args.athlete:
        athlete_dir = (ATHLETES / args.athlete).resolve()
        if not athlete_dir.exists() or not athlete_dir.is_dir():
            print(f"Invalid athlete directory: {athlete_dir}")
            sys.exit(1)

        if is_v2_structure(athlete_dir):
            if args.project:
                project_dir = athlete_dir / "projects" / args.project
                if not project_dir.exists():
                    print(f"Project not found: {project_dir}")
                    print(f"Available projects: {', '.join(p.name for p in list_projects(athlete_dir))}")
                    sys.exit(1)
            else:
                project_dir = choose_project_interactive(athlete_dir)
                if project_dir is None:
                    sys.exit(0)
        else:
            project_dir = athlete_dir

    else:
        athlete_dir = choose_athlete_interactive()
        if athlete_dir is None:
            sys.exit(0)

        if is_v2_structure(athlete_dir):
            project_dir = choose_project_interactive(athlete_dir)
            if project_dir is None:
                sys.exit(0)
        else:
            project_dir = athlete_dir

    base = project_dir

    if not base.exists() or not base.is_dir():
        print(f"Invalid project directory: {base}")
        sys.exit(1)

    ensure_dirs(base)
    project_path = base / "project.json"
    work = base / "work"
    output = base / "output"

    if not project_path.exists():
        print(f"{project_path} not found. Run mark_play.py first.")
        sys.exit(1)

    # Load project data
    structure_type = detect_structure(base)
    if structure_type == "v2":
        data = get_merged_project_data(base)
    else:
        data = json.loads(project_path.read_text())

    include_intro = bool(data.get("include_intro", True))

    # Get intro directory
    intro_dir = get_intro_dir(base)

    # Handle intro media selection
    if include_intro:
        if args.reset_intro or ("intro_media" not in data):
            print(f"\n🎬 Resetting intro media selection for {base.name}")

            intro_files = find_intro_files(intro_dir)
            intro_media_path = None

            if intro_files["images"] or intro_files["videos"]:
                intro_media = choose_intro_media(intro_files)
                if intro_media:
                    if structure_type == "v2":
                        intro_media_path = str(intro_media.relative_to(athlete_dir))
                    else:
                        intro_media_path = str(intro_media.relative_to(base))
                    print(f"Selected intro media: {intro_media.name}")
                else:
                    print("Using text-only slate")
            else:
                print("No intro media files found - using text-only slate")

            raw_data = json.loads(project_path.read_text())
            raw_data["intro_media"] = intro_media_path
            project_path.write_text(json.dumps(raw_data, indent=2))
            data["intro_media"] = intro_media_path
        else:
            intro_media_path = data.get("intro_media")
            if intro_media_path:
                print(f"Using intro media: {pathlib.Path(intro_media_path).name}")
            else:
                print("Using text-only slate")

    processed = []
    seen_sections = set()

    for i, c in enumerate(data.get("clips", []), 1):
        std_path = resolve_path(base, c.get("std_file"))
        if std_path is None:
            std_path = base / "work" / "proxies" / f"clip{i:02d}_std.mp4"

        src_path = resolve_path(base, c.get("file"))
        if src_path is None:
            raise RuntimeError(f"Clip {i}: source 'file' missing in project.json")
        ensure_proxy(src_path, std_path)

        mx = int(c.get("marker_x_std", c.get("marker_x", 960)))
        my = int(c.get("marker_y_std", c.get("marker_y", 540)))
        radius_std = int(c.get("radius_std", c.get("radius", 72)))
        spot_frame_std = int(c.get("spot_frame_std", -1))
        if spot_frame_std < 0:
            fps = proxy_fps(std_path)
            spot_frame_std = to_frame(float(c.get("spot_time", 0.0)), fps)

        zoom_std = float(c.get("zoom_std", 1.0))

        out = work / f"clip{i:02d}_done.mp4"
        make_freeze_with_spot(std_path, mx, my, radius_std, out,
                              float(c.get("start_trim", 0.0)),
                              float(c.get("end_trim", 0.0)),
                              spot_frame_std, work,
                              zoom=zoom_std,
                              still_dur=1.25)

        # Apply section overlay
        clip_section = c.get("section")
        if clip_section and clip_section not in seen_sections:
            if clip_section not in SECTIONS:
                print(f"Warning: Invalid section '{clip_section}' in clip {i:02d}, skipping overlay")
                clip_section = None

        if clip_section and clip_section not in seen_sections:
            print(f"[section] Adding lower-third overlay: {clip_section}")
            out_with_section = work / f"clip{i:02d}_sectioned.mp4"
            clip_dur = duration_of(out)
            overlay_dur = min(OVERLAY_DURATION_DEFAULT, max(OVERLAY_DURATION_MIN, clip_dur - OVERLAY_MARGIN))
            overlay_dur = min(overlay_dur, clip_dur)

            try:
                add_lower_third_overlay(out, out_with_section, clip_section, duration=overlay_dur)
                out = out_with_section
                seen_sections.add(clip_section)
            except (subprocess.CalledProcessError, ValueError, OSError, IOError) as e:
                print(f"Warning: Failed to add overlay for '{clip_section}' on clip {i:02d}: {e}")
                print(f"Continuing with clip without overlay...")

        processed.append(out)

    if not processed:
        print("No processed clips.")
        sys.exit(0)

    body = work / "body.mp4"
    concat_videos(processed, body)

    outputs = [body]
    if include_intro:
        slate = work / "slate.mp4"

        intro_media = None
        intro_media_path = data.get("intro_media")
        if intro_media_path:
            if structure_type == "v2":
                intro_media = athlete_dir / intro_media_path
            else:
                intro_media = base / intro_media_path
            if not intro_media.exists():
                print(f"Warning: Intro media file not found: {intro_media}")
                intro_media = None

        slate_template = args.slate_template or data.get("slate_template")
        make_slate(data.get("player", {}), slate, work, intro_media, template_name=slate_template)
        outputs = [slate, body]

    final = output / "final.mp4"
    concat_videos(outputs, final)

    if not args.keep_work:
        clear_work_dir(work)

    print(f"\n✅ Final video saved to {final.resolve()}")
    if args.keep_work:
        print(f"ℹ️ Kept intermediates in {work}")


if __name__ == "__main__":
    main()
