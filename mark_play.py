#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
# mark_play.py
# Multi-athlete: choose an athlete folder under athletes/, mark clips on a standardized proxy.
#
# Structure (already created by you):
#   athletes/<athlete_name>/
#     ├─ clips_in/     (place source videos here)
#     ├─ work/         (created by this script)
#     ├─ output/       (unused here; renderer writes final here)
#     └─ project.json
#
# Features:
#   - Scans athletes/ and shows a numbered menu to pick an athlete folder.
#   - Builds standardized video-only proxies (1920 wide, CFR 30, setsar=1, -noautorotate).
#   - Full transport controls + mouse-wheel radius, presets, etc.
#   - Saves standardized coords (marker_x_std / marker_y_std) + spot_frame_std.
#
# Controls (window focused):
#   Space .......... Play/Pause
#   , / . .......... Step -1 / +1 frame (paused)
#   ← / → .......... Seek -0.5s / +0.5s
#   ↑ / ↓ .......... Seek -5s / +5s
#   [ / ] .......... Playback speed down/up  (0.25x, 0.5x, 1x, 1.5x, 2x, 4x)
#   g .............. Go to time (seconds)
#   s .............. Set spot_time & spot_frame_std = current frame
#   a .............. Set start_trim = current time
#   b .............. Set end_trim = clip_end - current time
#   + / - .......... Increase / decrease ring radius (std px)
#   Mouse wheel .... Adjust ring radius (Shift+wheel = larger steps)
#   1..5 ........... Radius presets (40, 60, 72, 90, 120 px)
#   < / > .......... Decrease / increase zoom (1.0x to 2.0x)
#   0 .............. Reset zoom to 1.0x
#   Left click ..... Set ring center at cursor (standardized coords)
#   r .............. Reset marker & trims & spot & zoom
#   Enter .......... Accept this clip (uses current frame if you never pressed 's')
#   q / Esc ........ Skip this clip
#
# Usage:
#   python mark_play.py
#   python mark_play.py --athlete "jane_smith"
#   python mark_play.py --dir athletes/jane_smith
#
# Requires: OpenCV (cv2), FFmpeg

import argparse
import cv2
import json
import pathlib
import subprocess
import sys
from typing import List, Dict, Any

# Import FFmpeg utilities for bundled binary detection
try:
    from ffmpeg_utils import get_ffmpeg_path
    FFMPEG_CMD = get_ffmpeg_path() or "ffmpeg"
except ImportError:
    # Fallback to system binary if ffmpeg_utils not available
    FFMPEG_CMD = "ffmpeg"

# Import clip sync utilities for marking status detection
from clip_sync import is_clip_marked, get_clip_filename

ROOT = pathlib.Path.cwd()
ATHLETES = ROOT / "athletes"

TARGET_W = 1920
FPS = 30
CRF = 18
RADIUS_MIN = 6
RADIUS_MAX = 600
ZOOM_MIN = 1.0
ZOOM_MAX = 2.0
ZOOM_STEP = 0.1
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi"}

def run(cmd: list[str]):
    print("•", " ".join(cmd))
    if subprocess.call(cmd) != 0:
        raise RuntimeError("Command failed")

def find_athletes() -> list[pathlib.Path]:
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

def validate_athlete_dir(base: pathlib.Path) -> dict[str, pathlib.Path]:
    clips_in = base / "clips_in"
    work = base / "work"
    output = base / "output"
    prox = work / "proxies"
    for p in (clips_in, output):
        if not p.exists():
            print(f"Missing required folder: {p}")
            raise SystemExit(1)
    work.mkdir(exist_ok=True)
    prox.mkdir(parents=True, exist_ok=True)
    return {"clips_in": clips_in, "work": work, "output": output, "prox": prox}

def list_clips(clips_in: pathlib.Path) -> List[pathlib.Path]:
    return sorted([p for p in clips_in.iterdir() if p.suffix.lower() in VIDEO_EXTS])

def build_proxy(src: pathlib.Path, dst: pathlib.Path):
    """Standardize to 1920x?, 30fps, setsar=1, -noautorotate, H.264, video-only."""
    vf = f"scale={TARGET_W}:-2:flags=bicubic,fps={FPS},setsar=1"
    run([FFMPEG_CMD,"-y","-noautorotate","-i",str(src),
         "-vf",vf,
         "-c:v","libx264","-preset","veryfast","-crf",str(CRF),
         "-pix_fmt","yuv420p",
         "-an",
         str(dst)])

def get_meta(cap):
    fps = cap.get(cv2.CAP_PROP_FPS) or FPS
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or TARGET_W)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)
    dur = total_frames / fps if total_frames > 0 else 0.0
    return fps, total_frames, w, h, dur

def clamp(v, a, b): return max(a, min(b, v))

def draw_hud(frame, t, fps, frame_idx, total_frames, rate, paused,
             radius_disp, start_trim, end_trim, spot_time, spot_frame, marker_disp, zoom=1.0):
    overlay = frame.copy()
    line1 = f"t={t:.2f}s  fps={fps:.2f}  frame={frame_idx}/{max(0,total_frames-1)}  rate={rate:.2f}x  {'PAUSED' if paused else 'PLAY'}"
    zoom_str = f"zoom={zoom:.1f}x  " if zoom > 1.0 else ""
    line2 = f"{zoom_str}radius={radius_disp}px  start_trim={start_trim:.2f}s  end_trim={end_trim:.2f}s  spot={spot_time:.2f}s  spot_f={spot_frame if spot_frame is not None else '-'}"
    cv2.putText(overlay, line1, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2, cv2.LINE_AA)
    cv2.putText(overlay, line2, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2, cv2.LINE_AA)
    if marker_disp:
        cv2.circle(overlay, marker_disp, radius_disp, (0,0,255), 3)
    cv2.addWeighted(overlay, 1.0, frame, 0.0, 0, frame)
    return frame

def find_intro_files(intro_dir: pathlib.Path) -> dict:
    """Find image and video files in the intro directory."""
    if not intro_dir.exists():
        return {"images": [], "videos": []}
    
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}
    
    images = []
    videos = []
    
    for file in intro_dir.iterdir():
        if file.is_file():
            ext = file.suffix.lower()
            if ext in image_exts:
                images.append(file)
            elif ext in video_exts:
                videos.append(file)
    
    return {"images": sorted(images), "videos": sorted(videos)}

def choose_intro_media(intro_files: dict) -> pathlib.Path | None:
    """Interactively choose an intro media file from available options."""
    images = intro_files["images"]
    videos = intro_files["videos"]
    
    if not images and not videos:
        return None
    
    print("\nAvailable intro media files:")
    options = []
    
    if images:
        print("  Pictures:")
        for i, img in enumerate(images, 1):
            print(f"    {i}. {img.name}")
            options.append(img)
    
    if videos:
        print("  Videos:")
        start_num = len(images) + 1
        for i, vid in enumerate(videos, start_num):
            print(f"    {i}. {vid.name}")
            options.append(vid)
    
    print("  n. No intro media (text-only slate)")
    
    while True:
        choice = input("Choose intro media (number or 'n'): ").strip().lower()
        if choice == 'n':
            return None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(options):
                return options[idx-1]
        print("Invalid choice. Try again.")

def autosave(project_path: pathlib.Path, project: Dict[str, Any]):
    project_path.write_text(json.dumps(project, indent=2))
    print(f"  ↳ autosaved {project_path}")

def mark_on_proxy(orig_path: pathlib.Path, proxy_path: pathlib.Path, clip_index: int):
    cap = cv2.VideoCapture(str(proxy_path))
    if not cap.isOpened():
        print(f"Could not open proxy: {proxy_path}")
        return None

    fps, total_frames, w, h, dur = get_meta(cap)

    disp_max_w, disp_max_h = 1280, 720
    scale = min(disp_max_w / w, disp_max_h / h, 1.0)
    disp_w, disp_h = int(round(w * scale)), int(round(h * scale))

    win = f"[{clip_index}] {orig_path.name}"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, disp_w, disp_h)

    current_frame = 0
    playing = True
    rate_options = [0.25, 0.5, 1.0, 1.5, 2.0, 4.0]
    rate_idx = 2
    radius = 72
    marker = (w//2, h//2)
    spot_time = 0.0
    spot_frame_std = None
    start_trim = 0.0
    end_trim = 0.0
    zoom = 1.0

    def on_mouse(event, x, y, flags, param):
        nonlocal marker, radius
        if event == cv2.EVENT_LBUTTONDOWN:
            fx = int(round(x / max(scale, 1e-6)))
            fy = int(round(y / max(scale, 1e-6)))
            fx = clamp(fx, 0, w - 1)
            fy = clamp(fy, 0, h - 1)
            marker = (fx, fy)
        elif event == cv2.EVENT_MOUSEWHEEL:
            step = 12 if (flags & cv2.EVENT_FLAG_SHIFTKEY) else 6
            if flags > 0:
                radius = clamp(radius + step, RADIUS_MIN, RADIUS_MAX)
            else:
                radius = clamp(radius - step, RADIUS_MIN, RADIUS_MAX)

    cv2.setMouseCallback(win, on_mouse)

    print(f"\n=== Marking (proxy): {orig_path.name} ===")
    print("Space: play/pause | ,/. frame step | ←/→ ±0.5s | ↑/↓ ±5s | [/] speed | g goto | s set spot | a/b trims")
    print("+/- or mouse wheel to change radius (Shift+wheel = larger step), presets 1=40 2=60 3=72 4=90 5=120")
    print("</> zoom in/out (1.0-2.0x) | 0 reset zoom | Click to set ring | r reset | Enter accept | q/Esc skip")

    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ok, frame = cap.read()
        if not ok:
            current_frame = clamp(current_frame, 0, max(0, total_frames-1))
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
            ok, frame = cap.read()
            playing = False
            if not ok:
                break

        t = current_frame / fps if fps > 0 else 0.0
        disp = cv2.resize(frame, (disp_w, disp_h), interpolation=cv2.INTER_LINEAR)

        # Draw zoom preview overlay (darken area outside zoom region)
        if zoom > 1.0:
            visible_w = int(w / zoom)
            visible_h = int(h / zoom)
            cx, cy = w // 2, h // 2
            left = cx - visible_w // 2
            top = cy - visible_h // 2
            right = cx + visible_w // 2
            bottom = cy + visible_h // 2

            # Convert to display coordinates
            left_d = int(left * scale)
            top_d = int(top * scale)
            right_d = int(right * scale)
            bottom_d = int(bottom * scale)

            # Create semi-transparent overlay outside zoom area
            overlay = disp.copy()
            cv2.rectangle(overlay, (0, 0), (disp_w, top_d), (0, 0, 0), -1)  # Top
            cv2.rectangle(overlay, (0, bottom_d), (disp_w, disp_h), (0, 0, 0), -1)  # Bottom
            cv2.rectangle(overlay, (0, top_d), (left_d, bottom_d), (0, 0, 0), -1)  # Left
            cv2.rectangle(overlay, (right_d, top_d), (disp_w, bottom_d), (0, 0, 0), -1)  # Right
            cv2.addWeighted(overlay, 0.5, disp, 0.5, 0, disp)

            # Draw border around visible area
            cv2.rectangle(disp, (left_d, top_d), (right_d, bottom_d), (0, 255, 255), 2)

        marker_disp = (int(round(marker[0] * scale)), int(round(marker[1] * scale)))
        radius_disp = int(round(radius * scale))
        disp = draw_hud(disp, t, fps, current_frame, total_frames,
                        rate_options[rate_idx], not playing,
                        radius_disp, start_trim, end_trim,
                        spot_time, spot_frame_std, marker_disp, zoom)
        cv2.imshow(win, disp)

        if playing:
            step = max(1, int(round(rate_options[rate_idx])))
            current_frame = clamp(current_frame + step, 0, max(0, total_frames-1))

        key = cv2.waitKey(1 if playing else 20) & 0xFF
        if key == 255:
            continue

        if key in (ord('q'), 27):
            cap.release()
            cv2.destroyWindow(win)
            return None
        elif key == ord(' '):
            playing = not playing
        elif key == ord(',') and not playing:
            current_frame = clamp(current_frame - 1, 0, max(0, total_frames-1))
        elif key == ord('.') and not playing:
            current_frame = clamp(current_frame + 1, 0, max(0, total_frames-1))
        elif key == 81:   # Left
            current_frame = clamp(current_frame - int(0.5 * fps), 0, max(0, total_frames-1))
        elif key == 83:   # Right
            current_frame = clamp(current_frame + int(0.5 * fps), 0, max(0, total_frames-1))
        elif key == 82:   # Up
            current_frame = clamp(current_frame - int(5 * fps), 0, max(0, total_frames-1))
        elif key == 84:   # Down
            current_frame = clamp(current_frame + int(5 * fps), 0, max(0, total_frames-1))
        elif key == ord('['):
            rate_idx = max(0, rate_idx - 1)
        elif key == ord(']'):
            rate_idx = min(len(rate_options)-1, rate_idx + 1)
        elif key == ord('g'):
            try:
                secs = float(input("Go to time (seconds): ").strip())
                current_frame = clamp(int(round(secs * fps)), 0, max(0, total_frames-1))
            except Exception:
                pass
        elif key == ord('s'):
            spot_time = current_frame / fps if fps > 0 else 0.0
            spot_frame_std = current_frame
            print(f"spot_time = {spot_time:.3f}s  |  spot_frame_std = {spot_frame_std}")
        elif key == ord('a'):
            start_trim = current_frame / fps if fps > 0 else 0.0
            print(f"start_trim = {start_trim:.3f}s")
        elif key == ord('b'):
            now = current_frame / fps if fps > 0 else 0.0
            end_trim = max(0.0, dur - now)
            print(f"end_trim = {end_trim:.3f}s")
        elif key == ord('+'):
            radius = clamp(radius + 6, RADIUS_MIN, RADIUS_MAX)
        elif key == ord('-'):
            radius = clamp(radius - 6, RADIUS_MIN, RADIUS_MAX)
        elif key in (ord('1'), ord('2'), ord('3'), ord('4'), ord('5')):
            presets = {ord('1'):40, ord('2'):60, ord('3'):72, ord('4'):90, ord('5'):120}
            radius = presets[key]
            print(f"radius preset -> {radius}px")
        elif key == ord('<') or key == ord(',') and playing:  # < key (zoom out)
            zoom = round(clamp(zoom - ZOOM_STEP, ZOOM_MIN, ZOOM_MAX), 1)
            print(f"zoom = {zoom:.1f}x")
        elif key == ord('>') or key == ord('.') and playing:  # > key (zoom in)
            zoom = round(clamp(zoom + ZOOM_STEP, ZOOM_MIN, ZOOM_MAX), 1)
            print(f"zoom = {zoom:.1f}x")
        elif key == ord('0'):  # Reset zoom
            zoom = 1.0
            print("zoom reset to 1.0x")
        elif key in (ord('r'), ord('R')):
            marker = (w//2, h//2); radius = 72
            start_trim = 0.0; end_trim = 0.0
            spot_time = 0.0; spot_frame_std = None
            zoom = 1.0
            print("Reset marker, trims, spot, and zoom.")
        elif key == 13:  # Enter
            if spot_frame_std is None:
                spot_frame_std = current_frame
                spot_time = current_frame / fps if fps > 0 else 0.0
                print(f"(auto) spot_time = {spot_time:.3f}s  |  spot_frame_std = {spot_frame_std}")
            # Warn if marker may be outside zoomed region
            if zoom > 1.0:
                visible_w = int(w / zoom)
                visible_h = int(h / zoom)
                cx, cy = w // 2, h // 2
                left = cx - visible_w // 2
                right = cx + visible_w // 2
                top = cy - visible_h // 2
                bottom = cy + visible_h // 2
                if not (left <= marker[0] <= right and top <= marker[1] <= bottom):
                    print(f"WARNING: Marker at ({marker[0]}, {marker[1]}) may be outside zoomed region!")
            cap.release()
            cv2.destroyWindow(win)
            return {
                "file": str(orig_path),
                "std_file": str(proxy_path),
                "marker_x_std": int(marker[0]),
                "marker_y_std": int(marker[1]),
                "radius_std": int(radius),
                "start_trim": float(start_trim),
                "end_trim": float(end_trim),
                "spot_time": float(spot_time),
                "spot_frame_std": int(spot_frame_std),
                "zoom_std": float(zoom),
            }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--athlete", type=str, help="Athlete folder name under ./athletes")
    ap.add_argument("--dir", type=str, help="Full path to athlete folder")

    # Player information arguments (for GUI mode)
    ap.add_argument("--player-name", type=str, help="Player name")
    ap.add_argument("--title", type=str, help="Title (optional)")
    ap.add_argument("--position", type=str, help="Playing position")
    ap.add_argument("--grad-year", type=str, help="Graduation year")
    ap.add_argument("--club-team", type=str, help="Club team")
    ap.add_argument("--high-school", type=str, help="High school")
    ap.add_argument("--height-weight", type=str, help="Height and weight")
    ap.add_argument("--gpa", type=str, help="GPA")
    ap.add_argument("--email", type=str, help="Email address")
    ap.add_argument("--phone", type=str, help="Phone number")
    ap.add_argument("--include-intro", action="store_true", help="Include intro screen")
    ap.add_argument("--intro-media", type=str, help="Path to intro media file (relative to athlete directory)")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing project without asking")
    ap.add_argument("--all", action="store_true",
                    help="Re-mark all clips, ignoring existing marks (default: only mark new/unmarked)")

    args = ap.parse_args()

    # Resolve athlete base directory
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

    paths = validate_athlete_dir(base)
    # Ensure intro directory exists
    intro_dir = base / "intro"
    intro_dir.mkdir(exist_ok=True)
    clips = list_clips(paths["clips_in"])
    if not clips:
        print(f"No clips found in {paths['clips_in']}")
        sys.exit(0)

    project_path = base / "project.json"

    # Check if using GUI mode (any player argument provided)
    gui_mode = any([
        args.player_name, args.position, args.grad_year, args.club_team,
        args.high_school, args.height_weight, args.gpa, args.email, args.phone,
        args.include_intro, args.overwrite
    ])

    # Determine marking mode: new-only (default) or all
    # --all overrides --new-only
    mark_all = args.all
    existing_project = None

    # If project exists, handle accordingly
    if project_path.exists():
        try:
            existing_project = json.loads(project_path.read_text())
        except json.JSONDecodeError as e:
            print(f"Error: project.json is corrupted: {e}")
            print("Please fix or delete the file and try again.")
            sys.exit(1)

        if mark_all:
            # --all flag: confirm overwrite
            if gui_mode and args.overwrite:
                print(f"Re-marking all clips (overwriting existing marks): {project_path}")
            else:
                ans = input(f"{project_path} exists. Re-mark ALL clips? [y/N]: ").strip().lower()
                if ans != "y":
                    print("Aborted.")
                    sys.exit(0)
        else:
            # Default: new-only mode - preserve existing marks
            print(f"Existing project found. Will mark only new/unmarked clips.")
            print(f"Use --all to re-mark all clips.")

    elif gui_mode and args.overwrite:
        # No existing project, GUI mode - proceed normally
        pass
    elif not gui_mode:
        # No existing project, interactive mode - proceed normally
        pass

    # Handle intro and player info
    # In new-only mode with existing project, use existing data
    if existing_project and not mark_all:
        # Use existing player/intro data from project
        include_intro = existing_project.get("include_intro", True)
        player = existing_project.get("player", {})
        intro_media_path = existing_project.get("intro_media")
    elif gui_mode:
        include_intro = args.include_intro
        player = {}
        intro_media_path = args.intro_media if args.intro_media else None
        if include_intro:
            player["name"] = args.player_name or ""
            player["title"] = args.title or ""
            player["position"] = args.position or ""
            player["grad_year"] = args.grad_year or ""
            player["club_team"] = args.club_team or ""
            player["high_school"] = args.high_school or ""
            player["height_weight"] = args.height_weight or ""
            player["gpa"] = args.gpa or ""
            player["email"] = args.email or ""
            player["phone"] = args.phone or ""
    else:
        include_intro = input("Include intro screen? [Y/n]: ").strip().lower() != "n"
        player = {}
        if include_intro:
            print("Enter player info (leave blank to omit a line):")
            player["name"] = input("Name: ").strip()
            player["position"] = input("Position: ").strip()
            player["grad_year"] = input("Grad Year: ").strip()
            player["club_team"] = input("Club Team: ").strip()
            player["high_school"] = input("High School: ").strip()
            player["height_weight"] = input("Height/Weight: ").strip()
            player["gpa"] = input("GPA: ").strip()
            player["email"] = input("Email: ").strip()
            player["phone"] = input("Phone: ").strip()
        
        # Handle intro media selection
        intro_media_path = None
        intro_dir = base / "intro"
        intro_files = find_intro_files(intro_dir)
        if intro_files["images"] or intro_files["videos"]:
            intro_media = choose_intro_media(intro_files)
            if intro_media:
                intro_media_path = str(intro_media.relative_to(base))
                print(f"Selected intro media: {intro_media.name}")
            else:
                print("Using text-only slate")
        else:
            print("No intro media files found - using text-only slate")

    # Initialize or update project structure
    if existing_project and not mark_all:
        # New-only mode: preserve existing project structure
        project = existing_project.copy()
        # Update player info only if provided in GUI mode
        if gui_mode and include_intro:
            project["player"] = player
            project["include_intro"] = include_intro
            if intro_media_path:
                project["intro_media"] = intro_media_path
    else:
        # Fresh project or --all mode
        project = {"player": player, "include_intro": include_intro, "intro_media": intro_media_path, "clips": []}

    # Build map of clips_in files for lookup
    clips_in_files = {src.name: src for src in clips}

    # Determine which clips need marking, preserving project.json order
    clips_to_mark: List[pathlib.Path] = []
    marked_count = 0

    if existing_project and not mark_all:
        # Preserve order from project.json
        existing_clips = existing_project.get("clips", [])
        for clip in existing_clips:
            filename = get_clip_filename(clip)
            if is_clip_marked(clip):
                print(f"✓ Already marked: {filename}")
                marked_count += 1
            elif filename in clips_in_files:
                # Unmarked clip that exists in clips_in - needs marking
                clips_to_mark.append(clips_in_files[filename])

        # Also check for new clips in clips_in/ not in project.json
        existing_filenames = {get_clip_filename(c) for c in existing_clips}
        for src in clips:
            if src.name not in existing_filenames:
                clips_to_mark.append(src)
    else:
        # Fresh project or --all mode - mark all clips
        clips_to_mark = list(clips)

    if not clips_to_mark:
        print("\nAll clips are already marked. Nothing to do.")
        print(f"Use --all to re-mark all clips.")
        sys.exit(0)

    print(f"\n{len(clips_to_mark)} clip(s) to mark, {marked_count} already marked.")

    # Build a map for updating clips in place
    newly_marked: Dict[str, Dict[str, Any]] = {}

    # Mark the clips that need it
    for idx, src in enumerate(clips_to_mark, 1):
        # Generate unique proxy filename based on source name
        proxy_name = f"proxy_{src.stem}_std.mp4"
        proxy = paths["prox"] / proxy_name

        # Check if proxy already exists and is valid
        if proxy.exists():
            print(f"Reusing existing proxy: {proxy.name}")
        else:
            try:
                build_proxy(src, proxy)
            except Exception as e:
                print(f"Proxy build failed for {src.name}: {e}")
                continue

        data = mark_on_proxy(src, proxy, idx)
        if data is not None:
            newly_marked[src.name] = data
        else:
            print(f"Skipped: {src.name}")

    # Update project clips, preserving order from project.json
    if existing_project and not mark_all:
        # Update existing clips in place with new marking data
        updated_clips = []
        for clip in project.get("clips", []):
            filename = get_clip_filename(clip)
            if filename in newly_marked:
                # Replace with newly marked data, preserve section if set
                new_clip = newly_marked[filename]
                if clip.get("section"):
                    new_clip["section"] = clip["section"]
                updated_clips.append(new_clip)
            else:
                # Keep existing clip data
                updated_clips.append(clip)

        # Append any new clips that weren't in project.json
        existing_filenames = {get_clip_filename(c) for c in project.get("clips", [])}
        for filename, data in newly_marked.items():
            if filename not in existing_filenames:
                updated_clips.append(data)

        project["clips"] = updated_clips
    else:
        # Fresh project - just use newly marked clips
        project["clips"] = list(newly_marked.values())

    project_path.write_text(json.dumps(project, indent=2))
    newly_marked_count = len(newly_marked)
    print(f"\nSaved {project_path}. Marked {newly_marked_count} new clip(s).")
    print(f"Next: python render_highlight.py --dir \"{base}\"")

if __name__ == "__main__":
    main()

