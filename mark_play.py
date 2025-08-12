#!/usr/bin/env python3
# mark_play.py
# Build standardized proxies and mark exact frame/coords for each clip.
#
# Proxies match render geometry/timing:
#   -noautorotate, setsar=1, scale=1920:-2, fps=30, H.264 (video only OK)
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
#   + / - .......... Increase / decrease ring radius (standardized px)
#   Left click ..... Set ring center at cursor (standardized coords)
#   r .............. Reset marker & trims & spot
#   Enter .......... Accept this clip (uses current frame if you never pressed 's')
#   q / Esc ........ Skip this clip
#
# Output: project.json with include_intro, player (optional), and per-clip fields:
#   file, std_file, marker_x_std, marker_y_std, radius_std,
#   start_trim, end_trim, spot_time, spot_frame_std
#
# Usage:
#   python mark_play.py
#
# Requires: OpenCV (cv2), FFmpeg installed on system.

import cv2
import pathlib
import json
import subprocess
import sys
from typing import List, Dict, Any

PROJECT_JSON = pathlib.Path("project.json")
SRC = pathlib.Path("clips_in")
WORK = pathlib.Path("work")
PROX = WORK / "proxies"

TARGET_W = 1920
FPS = 30
CRF = 18

def ensure_dirs():
    WORK.mkdir(exist_ok=True)
    PROX.mkdir(parents=True, exist_ok=True)

def list_clips() -> List[pathlib.Path]:
    return sorted([p for p in SRC.iterdir()
                   if p.suffix.lower() in (".mp4", ".mov", ".m4v", ".mkv", ".avi")])

def run(cmd):
    print("•", " ".join(cmd))
    if subprocess.call(cmd) != 0:
        raise RuntimeError("Command failed")

def build_proxy(src: pathlib.Path, dst: pathlib.Path):
    """Standardize to 1920x?, 30fps, setsar=1, -noautorotate, H.264 (video-only)."""
    vf = f"scale={TARGET_W}:-2:flags=bicubic,fps={FPS},setsar=1"
    run(["ffmpeg","-y","-noautorotate","-i",str(src),
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
             radius_disp, start_trim, end_trim, spot_time, spot_frame, marker_disp):
    overlay = frame.copy()
    line1 = f"t={t:.2f}s  fps={fps:.2f}  frame={frame_idx}/{max(0,total_frames-1)}  rate={rate:.2f}x  {'PAUSED' if paused else 'PLAY'}"
    line2 = f"radius={radius_disp}  start_trim={start_trim:.2f}s  end_trim={end_trim:.2f}s  spot={spot_time:.2f}s  spot_f={spot_frame if spot_frame is not None else '-'}"
    cv2.putText(overlay, line1, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2, cv2.LINE_AA)
    cv2.putText(overlay, line2, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2, cv2.LINE_AA)
    if marker_disp:
        cv2.circle(overlay, marker_disp, radius_disp, (0,0,255), 3)  # red ring preview
    cv2.addWeighted(overlay, 1.0, frame, 0.0, 0, frame)
    return frame

def autosave(project: Dict[str, Any]):
    try:
        PROJECT_JSON.write_text(json.dumps(project, indent=2))
        print("  ↳ autosaved project.json")
    except Exception as e:
        print(f"  ! autosave failed: {e}")

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

    def on_mouse(event, x, y, flags, param):
        nonlocal marker
        if event == cv2.EVENT_LBUTTONDOWN:
            fx = int(round(x / max(scale, 1e-6)))
            fy = int(round(y / max(scale, 1e-6)))
            fx = clamp(fx, 0, w - 1)
            fy = clamp(fy, 0, h - 1)
            marker = (fx, fy)

    cv2.setMouseCallback(win, on_mouse)

    print(f"\n=== Marking (proxy): {orig_path.name} ===")
    print("Space: play/pause | ,/. frame step | ←/→ ±0.5s | ↑/↓ ±5s | [/] speed | g goto | s set spot | a/b trims")
    print("+/- radius | click to set ring | r reset | Enter accept | q/Esc skip")

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
        marker_disp = (int(round(marker[0] * scale)), int(round(marker[1] * scale)))
        radius_disp = int(round(radius * scale))
        disp = draw_hud(disp, t, fps, current_frame, total_frames,
                        rate_options[rate_idx], not playing,
                        radius_disp, start_trim, end_trim,
                        spot_time, spot_frame_std, marker_disp)
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
            radius = min(600, radius + 4)
        elif key == ord('-'):
            radius = max(6, radius - 4)
        elif key in (ord('r'), ord('R')):
            marker = (w//2, h//2); radius = 72
            start_trim = 0.0; end_trim = 0.0
            spot_time = 0.0; spot_frame_std = None
            print("Reset marker, trims, and spot.")
        elif key == 13:  # Enter
            # If user never pressed 's', use current frame as spot
            if spot_frame_std is None:
                spot_frame_std = current_frame
                spot_time = current_frame / fps if fps > 0 else 0.0
                print(f"(auto) spot_time = {spot_time:.3f}s  |  spot_frame_std = {spot_frame_std}")
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
            }

def main():
    ensure_dirs()
    clips = list_clips()
    if not clips:
        print("No clips found in clips_in/")
        return

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

    project = {"player": player, "include_intro": include_intro, "clips": []}

    for idx, src in enumerate(clips, 1):
        proxy = PROX / f"clip{idx:02d}_std.mp4"
        try:
            build_proxy(src, proxy)
        except Exception as e:
            print(f"Proxy build failed for {src.name}: {e}")
            continue

        data = mark_on_proxy(src, proxy, idx)
        if data is not None:
            project["clips"].append(data)
            autosave(project)  # save progress after each accepted clip
        else:
            print(f"Skipped: {src.name}")

    # Final save
    try:
        PROJECT_JSON.write_text(json.dumps(project, indent=2))
        print(f"\nSaved {PROJECT_JSON}. Next: python render_highlight.py")
    except Exception as e:
        print(f"Failed to save {PROJECT_JSON}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

