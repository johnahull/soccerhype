#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
# mark_play_enhanced.py
# Enhanced version with auto-detection, smarter defaults, and improved UX
#
# New Features:
#   - Auto-detects new clips and suggests processing
#   - Template system for reusing player profiles
#   - Better progress indication and user feedback
#   - Smart defaults based on previous clips
#   - Enhanced keyboard shortcuts
#   - Frame-accurate scrubbing
#   - Zoom functionality
#   - Undo/redo for marker placement
#
# Enhanced Controls:
#   Space .......... Play/Pause
#   , / . .......... Step -1 / +1 frame (paused)
#   ← / → .......... Seek -0.5s / +0.5s
#   ↑ / ↓ .......... Seek -5s / +5s
#   [ / ] .......... Playback speed down/up (more granular: 0.1x, 0.25x, 0.5x, 1x, 1.5x, 2x, 4x)
#   g .............. Go to time (seconds)
#   s .............. Set spot_time & spot_frame_std = current frame
#   a .............. Set start_trim = current time
#   b .............. Set end_trim = clip_end - current time
#   + / - .......... Increase / decrease ring radius (std px)
#   Mouse wheel .... Adjust ring radius (Shift+wheel = larger steps)
#   1..5 ........... Radius presets (40, 60, 72, 90, 120 px)
#   Left click ..... Set ring center at cursor (standardized coords)
#   Right click .... Context menu with options
#   r .............. Reset marker & trims & spot
#   u .............. Undo last marker placement
#   y .............. Redo marker placement
#   z .............. Toggle zoom mode
#   p .............. Auto-detect player (experimental)
#   Enter .......... Accept this clip
#   q / Esc ........ Skip this clip
#   F1 ............. Show help

import argparse
import cv2
import json
import pathlib
import subprocess
import sys
import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

# Import FFmpeg utilities for bundled binary detection
try:
    from ffmpeg_utils import get_ffmpeg_path
    FFMPEG_CMD = get_ffmpeg_path() or "ffmpeg"
except ImportError:
    # Fallback to system binary if ffmpeg_utils not available
    FFMPEG_CMD = "ffmpeg"

ROOT = pathlib.Path.cwd()
ATHLETES = ROOT / "athletes"
TEMPLATES_DIR = ROOT / "templates"

TARGET_W = 1920
FPS = 30
CRF = 18
RADIUS_MIN = 6
RADIUS_MAX = 600
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}

# Enhanced playback speeds
SPEED_OPTIONS = [0.1, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]

class PlayerTemplate:
    """Manages player profile templates for reuse"""

    def __init__(self):
        TEMPLATES_DIR.mkdir(exist_ok=True)

    def save_template(self, name: str, player_data: Dict[str, Any]):
        """Save player profile as template"""
        template_file = TEMPLATES_DIR / f"{name}.json"
        template_file.write_text(json.dumps(player_data, indent=2))
        print(f"Template saved: {name}")

    def load_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Load player profile template"""
        template_file = TEMPLATES_DIR / f"{name}.json"
        if template_file.exists():
            return json.loads(template_file.read_text())
        return None

    def list_templates(self) -> List[str]:
        """List available templates"""
        return [f.stem for f in TEMPLATES_DIR.glob("*.json")]

class ClipDetector:
    """Detects and manages new clips"""

    @staticmethod
    def find_new_clips(clips_in: pathlib.Path, existing_clips: List[Dict]) -> List[pathlib.Path]:
        """Find clips not yet in project"""
        existing_files = {pathlib.Path(clip.get("file", "")).name for clip in existing_clips}
        all_clips = [p for p in clips_in.iterdir() if p.suffix.lower() in VIDEO_EXTS]
        return [clip for clip in all_clips if clip.name not in existing_files]

    @staticmethod
    def suggest_processing_order(clips: List[pathlib.Path]) -> List[pathlib.Path]:
        """Suggest optimal processing order based on filename patterns"""
        # Sort by modification time (newest first) and filename
        return sorted(clips, key=lambda x: (x.stat().st_mtime, x.name.lower()), reverse=True)

class SmartDefaults:
    """Provides intelligent defaults based on previous clips"""

    def __init__(self):
        self.last_radius = 72
        self.last_position = (960, 540)  # Center
        self.common_positions = []  # Track common player positions

    def update_from_clip(self, clip_data: Dict[str, Any]):
        """Learn from completed clip"""
        self.last_radius = clip_data.get("radius_std", self.last_radius)
        self.last_position = (
            clip_data.get("marker_x_std", self.last_position[0]),
            clip_data.get("marker_y_std", self.last_position[1])
        )
        self.common_positions.append(self.last_position)

        # Keep only last 10 positions
        if len(self.common_positions) > 10:
            self.common_positions = self.common_positions[-10:]

    def get_suggested_radius(self) -> int:
        """Get suggested radius based on history"""
        return self.last_radius

    def get_suggested_position(self) -> Tuple[int, int]:
        """Get suggested position based on history"""
        if len(self.common_positions) >= 3:
            # Return most common position area
            positions = np.array(self.common_positions[-5:])
            return tuple(map(int, np.mean(positions, axis=0)))
        return self.last_position

class MarkerHistory:
    """Manages undo/redo for marker placement"""

    def __init__(self):
        self.history = []
        self.current_index = -1
        self.max_history = 20

    def add_state(self, marker: Tuple[int, int], radius: int):
        """Add new state to history"""
        # Remove any future states if we're not at the end
        if self.current_index < len(self.history) - 1:
            self.history = self.history[:self.current_index + 1]

        self.history.append({"marker": marker, "radius": radius})

        # Limit history size
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
            self.current_index = len(self.history) - 1
        else:
            self.current_index = len(self.history) - 1

    def undo(self) -> Optional[Dict]:
        """Undo to previous state"""
        if self.current_index > 0:
            self.current_index -= 1
            return self.history[self.current_index]
        return None

    def redo(self) -> Optional[Dict]:
        """Redo to next state"""
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            return self.history[self.current_index]
        return None

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
        # Show status information
        clips_in = p / "clips_in"
        project_file = p / "project.json"
        has_clips = clips_in.exists() and any(clips_in.iterdir())
        has_project = project_file.exists()

        status = ""
        if not has_clips:
            status = " (no clips)"
        elif not has_project:
            status = " (ready to mark)"
        else:
            status = " (in progress)"

        print(f"  {i}. {p.name}{status}")

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

def build_proxy(src: pathlib.Path, dst: pathlib.Path, progress_callback=None):
    """Enhanced proxy building with progress callback"""
    vf = f"scale={TARGET_W}:-2:flags=bicubic,fps={FPS},setsar=1"
    cmd = [FFMPEG_CMD,"-y","-noautorotate","-i",str(src),
           "-vf",vf,
           "-c:v","libx264","-preset","veryfast","-crf",str(CRF),
           "-pix_fmt","yuv420p",
           "-an",
           str(dst)]

    if progress_callback:
        progress_callback(f"Building proxy for {src.name}...")

    run(cmd)

def get_meta(cap):
    fps = cap.get(cv2.CAP_PROP_FPS) or FPS
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or TARGET_W)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)
    dur = total_frames / fps if total_frames > 0 else 0.0
    return fps, total_frames, w, h, dur

def clamp(v, a, b):
    return max(a, min(b, v))

def show_help():
    """Display help information"""
    help_text = """
SoccerHype Enhanced Controls:

PLAYBACK:
  Space         Play/Pause
  , / .         Step -1 / +1 frame (when paused)
  ← / →         Seek ±0.5s
  ↑ / ↓         Seek ±5s
  [ / ]         Decrease/Increase playback speed
  g             Go to specific time (seconds)

MARKING:
  Left Click    Set ring center at cursor position
  Right Click   Context menu with options
  + / -         Increase/Decrease ring radius
  Mouse Wheel   Adjust ring radius (Shift = larger steps)
  1-5           Ring radius presets (40, 60, 72, 90, 120 px)

TIMING:
  s             Set freeze frame timing (spot_time)
  a             Set start trim
  b             Set end trim

ADVANCED:
  u             Undo last marker placement
  y             Redo marker placement
  z             Toggle zoom mode
  p             Auto-detect player (experimental)
  r             Reset marker, trims, and spot timing

COMPLETION:
  Enter         Accept current clip and continue
  q / Esc       Skip this clip
  F1            Show this help

Tips:
- Use zoom mode (z) for precise marking in crowded scenes
- Right-click for quick access to common functions
- The system learns from your preferences for smarter defaults
"""
    print(help_text)

def draw_enhanced_hud(frame, t, fps, frame_idx, total_frames, rate, paused,
                     radius_disp, start_trim, end_trim, spot_time, spot_frame,
                     marker_disp, zoom_mode=False, help_visible=False):
    """Enhanced HUD with more information and better layout"""
    overlay = frame.copy()

    # Main status line
    status = "PAUSED" if paused else "PLAYING"
    line1 = f"Time: {t:.2f}s | Frame: {frame_idx}/{max(0,total_frames-1)} | Speed: {rate:.2f}x | {status}"

    # Marking info line
    line2 = f"Radius: {radius_disp}px | Start: {start_trim:.2f}s | End: {end_trim:.2f}s | Spot: {spot_time:.2f}s"

    # Mode indicators
    mode_indicators = []
    if zoom_mode:
        mode_indicators.append("ZOOM")
    if help_visible:
        mode_indicators.append("HELP")

    mode_text = " | ".join(mode_indicators)
    if mode_text:
        line3 = f"Mode: {mode_text}"
    else:
        line3 = "Press F1 for help | Right-click for options"

    # Draw text with better visibility
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Black background for better readability
    text_bg_color = (0, 0, 0, 180)
    text_color = (255, 255, 255)

    # Position text at top
    y_offset = 30
    cv2.rectangle(overlay, (10, 5), (frame.shape[1] - 10, y_offset * 3 + 15), text_bg_color[:3], -1)

    cv2.putText(overlay, line1, (20, y_offset), font, 0.7, text_color, 2, cv2.LINE_AA)
    cv2.putText(overlay, line2, (20, y_offset * 2), font, 0.7, text_color, 2, cv2.LINE_AA)
    cv2.putText(overlay, line3, (20, y_offset * 3), font, 0.6, (200, 200, 200), 1, cv2.LINE_AA)

    # Draw marker with enhanced visibility
    if marker_disp:
        # Main ring
        cv2.circle(overlay, marker_disp, radius_disp, (0, 0, 255), 3)
        # Outer glow
        cv2.circle(overlay, marker_disp, radius_disp + 3, (0, 0, 255), 1)
        # Center dot
        cv2.circle(overlay, marker_disp, 3, (0, 0, 255), -1)
        # Crosshairs
        cv2.line(overlay, (marker_disp[0] - 15, marker_disp[1]),
                (marker_disp[0] + 15, marker_disp[1]), (0, 0, 255), 2)
        cv2.line(overlay, (marker_disp[0], marker_disp[1] - 15),
                (marker_disp[0], marker_disp[1] + 15), (0, 0, 255), 2)

    cv2.addWeighted(overlay, 0.9, frame, 0.1, 0, frame)
    return frame

def create_player_profile_interactive(template_manager: PlayerTemplate) -> Dict[str, Any]:
    """Interactive player profile creation with template support"""
    print("\n=== Player Profile Setup ===")

    # Check for existing templates
    templates = template_manager.list_templates()
    if templates:
        print(f"\nAvailable templates: {', '.join(templates)}")
        use_template = input("Use existing template? (template name or 'n' for new): ").strip()

        if use_template != 'n' and use_template in templates:
            profile = template_manager.load_template(use_template)
            print(f"Loaded template: {use_template}")
            return profile

    # Create new profile
    print("Enter player information (press Enter to skip optional fields):")

    profile = {}
    profile["name"] = input("Name *: ").strip()

    # Optional title field
    title = input("Title (e.g., 'Fall 2025 Highlight Video'): ").strip()
    if title:
        profile["title"] = title

    profile["position"] = input("Position: ").strip()
    profile["grad_year"] = input("Graduation Year: ").strip()
    profile["club_team"] = input("Club Team: ").strip()
    profile["high_school"] = input("High School: ").strip()
    profile["height_weight"] = input("Height/Weight: ").strip()
    profile["gpa"] = input("GPA: ").strip()
    profile["email"] = input("Email: ").strip()
    profile["phone"] = input("Phone: ").strip()

    # Save as template option
    if profile["name"]:
        save_template = input(f"\nSave as template for future use? (y/N): ").strip().lower()
        if save_template == 'y':
            template_name = input(f"Template name (default: {profile['name']}): ").strip()
            if not template_name:
                template_name = profile["name"]
            template_manager.save_template(template_name, profile)

    return profile

def mark_on_proxy_enhanced(orig_path: pathlib.Path, proxy_path: pathlib.Path,
                          clip_index: int, smart_defaults: SmartDefaults):
    """Enhanced marking with better UX and smart features"""
    cap = cv2.VideoCapture(str(proxy_path))
    if not cap.isOpened():
        print(f"Could not open proxy: {proxy_path}")
        return None

    fps, total_frames, w, h, dur = get_meta(cap)

    disp_max_w, disp_max_h = 1280, 720
    scale = min(disp_max_w / w, disp_max_h / h, 1.0)
    disp_w, disp_h = int(round(w * scale)), int(round(h * scale))

    win = f"[{clip_index}] {orig_path.name} - Enhanced Marking"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, disp_w, disp_h)

    # Initialize state with smart defaults
    current_frame = 0
    playing = True
    rate_idx = SPEED_OPTIONS.index(1.0)  # Start at normal speed

    # Use smart defaults
    radius = smart_defaults.get_suggested_radius()
    marker = smart_defaults.get_suggested_position()

    spot_time = 0.0
    spot_frame_std = None
    start_trim = 0.0
    end_trim = 0.0
    zoom_mode = False
    help_visible = False

    # Initialize history for undo/redo
    history = MarkerHistory()
    history.add_state(marker, radius)

    def on_mouse(event, x, y, flags, param):
        nonlocal marker, radius, history

        if event == cv2.EVENT_LBUTTONDOWN:
            # Convert display coordinates to video coordinates
            fx = int(round(x / max(scale, 1e-6)))
            fy = int(round(y / max(scale, 1e-6)))
            fx = clamp(fx, 0, w - 1)
            fy = clamp(fy, 0, h - 1)

            old_marker = marker
            marker = (fx, fy)

            # Add to history
            history.add_state(marker, radius)
            print(f"Marker set to ({fx}, {fy})")

        elif event == cv2.EVENT_RBUTTONDOWN:
            # Right-click context menu (simple version)
            print("\nContext Menu:")
            print("  r - Reset marker")
            print("  p - Auto-detect player")
            print("  z - Toggle zoom mode")
            print("  u - Undo")

        elif event == cv2.EVENT_MOUSEWHEEL:
            step = 12 if (flags & cv2.EVENT_FLAG_SHIFTKEY) else 6
            if flags > 0:
                radius = clamp(radius + step, RADIUS_MIN, RADIUS_MAX)
            else:
                radius = clamp(radius - step, RADIUS_MIN, RADIUS_MAX)

            # Update history
            history.add_state(marker, radius)

    cv2.setMouseCallback(win, on_mouse)

    print(f"\n=== Enhanced Marking: {orig_path.name} ===")
    print("Enhanced controls available! Press F1 for help.")
    print("Suggestion: Use zoom mode (z) for precise marking.")

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

        # Apply zoom if enabled
        display_frame = frame.copy()
        if zoom_mode and marker:
            # Zoom to 2x around marker
            zoom_factor = 2.0
            crop_w, crop_h = int(w / zoom_factor), int(h / zoom_factor)
            x1 = clamp(marker[0] - crop_w // 2, 0, w - crop_w)
            y1 = clamp(marker[1] - crop_h // 2, 0, h - crop_h)
            x2, y2 = x1 + crop_w, y1 + crop_h

            cropped = frame[y1:y2, x1:x2]
            display_frame = cv2.resize(cropped, (w, h))

            # Adjust marker position for zoom display
            marker_disp_adj = (
                int((marker[0] - x1) * zoom_factor * scale),
                int((marker[1] - y1) * zoom_factor * scale)
            )
        else:
            display_frame = cv2.resize(frame, (disp_w, disp_h), interpolation=cv2.INTER_LINEAR)
            marker_disp_adj = (int(round(marker[0] * scale)), int(round(marker[1] * scale)))

        radius_disp = int(round(radius * scale))
        if zoom_mode:
            radius_disp = int(round(radius * scale * 2))  # Adjust for zoom

        display_frame = draw_enhanced_hud(
            display_frame, t, fps, current_frame, total_frames,
            SPEED_OPTIONS[rate_idx], not playing,
            radius_disp, start_trim, end_trim,
            spot_time, spot_frame_std, marker_disp_adj,
            zoom_mode, help_visible
        )

        cv2.imshow(win, display_frame)

        if playing:
            step = max(1, int(round(SPEED_OPTIONS[rate_idx] * 1)))
            current_frame = clamp(current_frame + step, 0, max(0, total_frames-1))

        key = cv2.waitKey(1 if playing else 20) & 0xFF
        if key == 255:
            continue

        # Handle enhanced key commands
        if key in (ord('q'), 27):  # q or Esc
            cap.release()
            cv2.destroyWindow(win)
            return None

        elif key == ord(' '):  # Space
            playing = not playing

        elif key == ord(',') and not playing:  # Previous frame
            current_frame = clamp(current_frame - 1, 0, max(0, total_frames-1))

        elif key == ord('.') and not playing:  # Next frame
            current_frame = clamp(current_frame + 1, 0, max(0, total_frames-1))

        elif key == 81:   # Left arrow
            current_frame = clamp(current_frame - int(0.5 * fps), 0, max(0, total_frames-1))

        elif key == 83:   # Right arrow
            current_frame = clamp(current_frame + int(0.5 * fps), 0, max(0, total_frames-1))

        elif key == 82:   # Up arrow
            current_frame = clamp(current_frame - int(5 * fps), 0, max(0, total_frames-1))

        elif key == 84:   # Down arrow
            current_frame = clamp(current_frame + int(5 * fps), 0, max(0, total_frames-1))

        elif key == ord('['):  # Decrease speed
            rate_idx = max(0, rate_idx - 1)

        elif key == ord(']'):  # Increase speed
            rate_idx = min(len(SPEED_OPTIONS)-1, rate_idx + 1)

        elif key == ord('g'):  # Go to time
            try:
                secs = float(input("Go to time (seconds): ").strip())
                current_frame = clamp(int(round(secs * fps)), 0, max(0, total_frames-1))
            except (ValueError, EOFError):
                pass

        elif key == ord('s'):  # Set spot time
            spot_time = current_frame / fps if fps > 0 else 0.0
            spot_frame_std = current_frame
            print(f"Spot time set: {spot_time:.3f}s (frame {spot_frame_std})")

        elif key == ord('a'):  # Set start trim
            start_trim = current_frame / fps if fps > 0 else 0.0
            print(f"Start trim set: {start_trim:.3f}s")

        elif key == ord('b'):  # Set end trim
            now = current_frame / fps if fps > 0 else 0.0
            end_trim = max(0.0, dur - now)
            print(f"End trim set: {end_trim:.3f}s")

        elif key == ord('+') or key == ord('='):  # Increase radius
            radius = clamp(radius + 6, RADIUS_MIN, RADIUS_MAX)
            history.add_state(marker, radius)

        elif key == ord('-'):  # Decrease radius
            radius = clamp(radius - 6, RADIUS_MIN, RADIUS_MAX)
            history.add_state(marker, radius)

        elif key in (ord('1'), ord('2'), ord('3'), ord('4'), ord('5')):  # Presets
            presets = {ord('1'):40, ord('2'):60, ord('3'):72, ord('4'):90, ord('5'):120}
            radius = presets[key]
            history.add_state(marker, radius)
            print(f"Radius preset: {radius}px")

        elif key == ord('r'):  # Reset
            marker = (w//2, h//2)
            radius = 72
            start_trim = 0.0
            end_trim = 0.0
            spot_time = 0.0
            spot_frame_std = None
            history.add_state(marker, radius)
            print("Reset marker, trims, and spot timing")

        elif key == ord('u'):  # Undo
            prev_state = history.undo()
            if prev_state:
                marker = prev_state["marker"]
                radius = prev_state["radius"]
                print("Undid last marker change")
            else:
                print("Nothing to undo")

        elif key == ord('y'):  # Redo
            next_state = history.redo()
            if next_state:
                marker = next_state["marker"]
                radius = next_state["radius"]
                print("Redid marker change")
            else:
                print("Nothing to redo")

        elif key == ord('z'):  # Toggle zoom
            zoom_mode = not zoom_mode
            print(f"Zoom mode: {'ON' if zoom_mode else 'OFF'}")

        elif key == ord('p'):  # Auto-detect player (placeholder)
            print("Auto-detect feature coming soon!")

        elif key == 255 or key == ord('h') or key == 63232:  # F1 or h for help
            help_visible = not help_visible
            if help_visible:
                show_help()

        elif key == 13:  # Enter - Accept clip
            if spot_frame_std is None:
                spot_frame_std = current_frame
                spot_time = current_frame / fps if fps > 0 else 0.0
                print(f"Auto-set spot time: {spot_time:.3f}s (frame {spot_frame_std})")

            cap.release()
            cv2.destroyWindow(win)

            result = {
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

            # Update smart defaults
            smart_defaults.update_from_clip(result)

            return result

def main():
    ap = argparse.ArgumentParser(description="Enhanced play marking with smart features")
    ap.add_argument("--athlete", type=str, help="Athlete folder name under ./athletes")
    ap.add_argument("--dir", type=str, help="Full path to athlete folder")
    ap.add_argument("--template", type=str, help="Player template to use")
    args = ap.parse_args()

    # Initialize enhancement systems
    template_manager = PlayerTemplate()
    smart_defaults = SmartDefaults()
    clip_detector = ClipDetector()

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
    intro_dir = base / "intro"
    intro_dir.mkdir(exist_ok=True)

    # Check existing project
    project_path = base / "project.json"
    existing_project = None

    if project_path.exists():
        existing_project = json.loads(project_path.read_text())
        print(f"Found existing project for {base.name}")

        # Load smart defaults from existing clips
        for clip in existing_project.get("clips", []):
            smart_defaults.update_from_clip(clip)

    # Discover clips
    all_clips = list_clips(paths["clips_in"])
    if not all_clips:
        print(f"No clips found in {paths['clips_in']}")
        sys.exit(0)

    # Find new clips if project exists
    if existing_project:
        new_clips = clip_detector.find_new_clips(paths["clips_in"], existing_project.get("clips", []))
        if new_clips:
            new_clips = clip_detector.suggest_processing_order(new_clips)
            print(f"\nFound {len(new_clips)} new clips to process:")
            for clip in new_clips:
                print(f"  - {clip.name}")

            process_new = input("\nProcess new clips? (Y/n): ").strip().lower()
            if process_new == 'n':
                print("Skipping new clips.")
                sys.exit(0)

            clips_to_process = new_clips
            project = existing_project
        else:
            print("No new clips found.")
            sys.exit(0)
    else:
        # New project
        clips_to_process = clip_detector.suggest_processing_order(all_clips)

        # Ask before overwriting if project exists
        if project_path.exists():
            ans = input(f"{project_path} exists. Overwrite? [y/N]: ").strip().lower()
            if ans != "y":
                print("Aborted.")
                sys.exit(0)

        include_intro = input("Include intro screen? [Y/n]: ").strip().lower() != "n"

        if include_intro:
            if args.template:
                player = template_manager.load_template(args.template)
                if not player:
                    print(f"Template '{args.template}' not found.")
                    player = create_player_profile_interactive(template_manager)
            else:
                player = create_player_profile_interactive(template_manager)
        else:
            player = {}

        project = {
            "player": player,
            "include_intro": include_intro,
            "intro_media": None,
            "clips": existing_project.get("clips", []) if existing_project else []
        }

    # Process clips with enhanced marking
    for idx, src in enumerate(clips_to_process, len(project["clips"]) + 1):
        proxy = paths["prox"] / f"clip{idx:02d}_std.mp4"

        print(f"\n=== Processing clip {idx}/{len(clips_to_process)} ===")

        try:
            build_proxy(src, proxy, lambda msg: print(f"  {msg}"))
        except Exception as e:
            print(f"Proxy build failed for {src.name}: {e}")
            continue

        data = mark_on_proxy_enhanced(src, proxy, idx, smart_defaults)
        if data is not None:
            project["clips"].append(data)
            # Auto-save progress
            project_path.write_text(json.dumps(project, indent=2))
            print(f"  ✓ Saved progress to {project_path}")
        else:
            print(f"Skipped: {src.name}")

    # Final save
    project_path.write_text(json.dumps(project, indent=2))
    print(f"\n✅ Enhanced marking completed!")
    print(f"📁 Project saved: {project_path}")
    print(f"🎬 Next step: python render_highlight.py --dir \"{base}\"")
    print(f"🔧 Or use the GUI: python soccerhype_gui.py")

if __name__ == "__main__":
    main()