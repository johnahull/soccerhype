##!/usr/bin/env python3
# render_highlight.py
# Multi-athlete renderer: choose athlete folder and render audio-free highlights.
#
# Usage:
#   python render_highlight.py
#   python render_highlight.py --athlete "jane_smith"
#   python render_highlight.py --dir athletes/jane_smith
#   python render_highlight.py --keep-work
#
# Output:
#   athletes/<athlete>/output/final.mp4
#
# Requires: Pillow, FFmpeg

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont

# Import FFmpeg utilities for bundled binary detection
try:
    from ffmpeg_utils import get_ffmpeg_path
    FFMPEG_CMD = get_ffmpeg_path() or "ffmpeg"
    FFPROBE_CMD = get_ffmpeg_path().replace('ffmpeg', 'ffprobe') if get_ffmpeg_path() else "ffprobe"
except ImportError:
    # Fallback to system binaries if ffmpeg_utils not available
    FFMPEG_CMD = "ffmpeg"
    FFPROBE_CMD = "ffprobe"

ROOT = pathlib.Path.cwd()
ATHLETES = ROOT / "athletes"

# Render / proxy params
FPS = 30
CRF = 18
PROXY_W = 1920
VIDEO_ONLY = True

# -------------------- utils --------------------

def run(cmd_list):
    print("•", " ".join(map(str, cmd_list)))
    if subprocess.call(cmd_list) != 0:
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
        if choice in ("q","quit","exit"):
            return None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(options):
                return options[idx-1]
        print("Invalid choice. Try again.")

def ensure_dirs(base: pathlib.Path):
    (base / "work" / "proxies").mkdir(parents=True, exist_ok=True)
    (base / "output").mkdir(exist_ok=True)

def clear_work_dir(work: pathlib.Path):
    for p in work.glob("*"):
        try:
            p.unlink()
        except IsADirectoryError:
            shutil.rmtree(p)

def resolve_path(base: pathlib.Path, p: str | None) -> pathlib.Path | None:
    if not p:
        return None
    path = pathlib.Path(p)
    return path if path.is_absolute() else (base / path)

def duration_of(path: pathlib.Path) -> float:
    p = subprocess.run(
        [FFPROBE_CMD,"-v","error","-show_entries","format=duration",
         "-of","default=nk=1:nw=1", str(path)],
        capture_output=True, text=True
    )
    try:
        return float(p.stdout.strip())
    except:
        return 0.0

def proxy_fps(path: pathlib.Path) -> float:
    p = subprocess.run(
        [FFPROBE_CMD,"-v","error","-select_streams","v:0",
         "-show_entries","stream=avg_frame_rate",
         "-of","default=nk=1:nw=1", str(path)],
        capture_output=True, text=True
    )
    s = p.stdout.strip()
    if "/" in s:
        a, b = s.split("/")
        try:
            return float(a) / float(b)
        except: pass
    try:
        return float(s)
    except:
        return 30.0

def proxy_frame_count(path: pathlib.Path) -> int:
    p = subprocess.run(
        [FFPROBE_CMD,"-v","error","-select_streams","v:0","-count_frames",
         "-show_entries","stream=nb_read_frames",
         "-of","default=nk=1:nw=1", str(path)],
        capture_output=True, text=True
    )
    txt = p.stdout.strip()
    if txt.isdigit():
        return int(txt)
    fps = proxy_fps(path)
    dur = duration_of(path)
    return max(1, int(round(fps * dur)))

def to_frame(t: float, fps: float) -> int:
    return max(0, int(round(t * fps)))

# -------------------- proxy builder --------------------

def ensure_proxy(src_path: pathlib.Path, std_path: pathlib.Path):
    """
    Create the standardized proxy if it doesn't exist.
      - Scale to width=1920 (keep AR), CFR=30
      - H.264 CRF 18
      - Strip audio
    """
    std_path.parent.mkdir(parents=True, exist_ok=True)
    if std_path.exists():
        return
    if not src_path.exists():
        raise RuntimeError(f"Source clip not found: {src_path}")

    cmd = [
        FFMPEG_CMD,"-y",
        "-i", str(src_path),
        "-vf", f"scale={PROXY_W}:-2,fps={FPS}",
        "-an",
        "-c:v","libx264","-preset","veryfast","-crf", str(CRF),
        "-pix_fmt","yuv420p",
        str(std_path)
    ]
    print("•", " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        print(proc.stdout)
        raise RuntimeError(f"Failed to build proxy for {src_path}")

# -------------------- ring + slate --------------------

def make_ring_png(out_path: pathlib.Path, radius: int, thickness: int = 8):
    size = max(2, radius * 2 + thickness * 6)
    main_color  = (200, 0, 0, 235)  # dark red
    glow_color  = (200, 0, 0, 110)  # outer glow
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bbox1 = [(size/2 - radius, size/2 - radius), (size/2 + radius, size/2 + radius)]
    d.ellipse(bbox1, outline=main_color, width=thickness)
    bbox2 = [(size/2 - radius - 5, size/2 - radius - 5), (size/2 + radius + 5, size/2 + radius + 5)]
    d.ellipse(bbox2, outline=glow_color, width=max(3, thickness//2))
    img.save(out_path)

def pil_composite_ring_on_png(frame_png: pathlib.Path, ring_png: pathlib.Path, px: int, py: int, out_png: pathlib.Path):
    base = Image.open(frame_png).convert("RGBA")
    ring = Image.open(ring_png).convert("RGBA")
    x = int(round(px - ring.width / 2))
    y = int(round(py - ring.height / 2))
    layer = Image.new("RGBA", base.size, (0,0,0,0))
    layer.paste(ring, (x, y), ring)
    Image.alpha_composite(base, layer).save(out_png)

def _load_font(size: int):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/freefont/FreeSans.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

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

def make_slate(player: dict, out_path: pathlib.Path, work: pathlib.Path, intro_media: pathlib.Path | None = None):
    """Create intro slate with optional picture or video integration."""
    
    # If intro_media is a video file, handle it directly
    if intro_media and intro_media.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}:
        make_slate_with_video(player, out_path, work, intro_media)
        return
    
    # Create image-based slate (with or without picture)
    make_slate_with_image(player, out_path, work, intro_media)

def make_slate_with_image(player: dict, out_path: pathlib.Path, work: pathlib.Path, intro_image: pathlib.Path | None = None):
    """Create slate with player profile card design matching phia-profile.jpg style."""
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Player data
    name = (player.get("name") or "Player Name")
    pos = (player.get("position") or "")
    grad = str(player.get("grad_year") or "")
    club = (player.get("club_team") or "")
    hs = (player.get("high_school") or "")
    hw = (player.get("height_weight") or "")
    gpa = (player.get("gpa") or "")
    email = (player.get("email") or "")
    phone = (player.get("phone") or "")

    # Draw corner brackets
    bracket_color = (128, 128, 128)  # Gray color for brackets
    bracket_size = 60
    bracket_thickness = 4
    margin = 80
    
    # Top-left bracket
    draw.line([(margin, margin), (margin + bracket_size, margin)], fill=bracket_color, width=bracket_thickness)
    draw.line([(margin, margin), (margin, margin + bracket_size)], fill=bracket_color, width=bracket_thickness)
    
    # Top-right bracket
    draw.line([(W - margin - bracket_size, margin), (W - margin, margin)], fill=bracket_color, width=bracket_thickness)
    draw.line([(W - margin, margin), (W - margin, margin + bracket_size)], fill=bracket_color, width=bracket_thickness)
    
    # Bottom-left bracket
    draw.line([(margin, H - margin - bracket_size), (margin, H - margin)], fill=bracket_color, width=bracket_thickness)
    draw.line([(margin, H - margin), (margin + bracket_size, H - margin)], fill=bracket_color, width=bracket_thickness)
    
    # Bottom-right bracket
    draw.line([(W - margin, H - margin - bracket_size), (W - margin, H - margin)], fill=bracket_color, width=bracket_thickness)
    draw.line([(W - margin - bracket_size, H - margin), (W - margin, H - margin)], fill=bracket_color, width=bracket_thickness)

    # Draw "PLAYER PROFILE" header - positioned over the profile text area (75%)
    header_font = _load_font(48)
    header_text = "PLAYER PROFILE"
    header_bbox = draw.textbbox((0, 0), header_text, font=header_font)
    header_w = header_bbox[2] - header_bbox[0]
    header_x = int(W * 0.66 - header_w // 2)  # Center at 66% of slate width
    header_y = 120
    draw.text((header_x, header_y), header_text, fill=(255, 255, 255), font=header_font)

    # Colors and fonts
    label_color = (255, 215, 0)  # Gold/yellow color
    data_color = (255, 255, 255)  # White for data
    label_font = _load_font(24)
    data_font = _load_font(36)
    name_font = _load_font(52)
    
    # Build text elements for stats (excluding name which gets special positioning)
    stats_elements = []
    
    # Other elements
    if pos:
        stats_elements.append(("POSITION", pos.upper(), label_font, label_color, False))
    if hw:
        stats_elements.append(("HEIGHT | WEIGHT", hw, label_font, label_color, False))
    if grad:
        stats_elements.append(("GRADUATION YEAR", f"CLASS OF {grad}", label_font, label_color, False))
    if club:
        stats_elements.append(("CLUB", club.upper(), label_font, label_color, False))
    if hs:
        stats_elements.append(("HIGH SCHOOL", hs.upper(), label_font, label_color, False))
    if gpa:
        stats_elements.append(("GPA", str(gpa), label_font, label_color, False))
    if email:
        stats_elements.append(("EMAIL", email.lower(), label_font, label_color, False))
    if phone:
        stats_elements.append(("PHONE", phone, label_font, label_color, False))
    
    if intro_image:
        # Layout with picture: centered at 25% of slate width
        pic_area_w = 450
        pic_area_h = 600
        pic_area_x = int(W * 0.33 - pic_area_w // 2)  # Center at 33% of slate width
        pic_area_y = 220
        
        # Load and display picture
        try:
            player_pic = Image.open(intro_image).convert("RGBA")
            
            # Resize picture to fit in the designated area with rounded corners
            pic_w, pic_h = player_pic.size
            scale = min(pic_area_w / pic_w, pic_area_h / pic_h, 1.0)
            new_w, new_h = int(pic_w * scale), int(pic_h * scale)
            player_pic = player_pic.resize((new_w, new_h), Image.LANCZOS)
            
            # Create rounded rectangle mask
            mask = Image.new("L", (new_w, new_h), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([(0, 0), (new_w, new_h)], radius=20, fill=255)
            
            # Apply mask to create rounded corners
            rounded_pic = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
            rounded_pic.paste(player_pic, (0, 0))
            rounded_pic.putalpha(mask)
            
            # Center picture in left half
            pic_x = pic_area_x + (pic_area_w - new_w) // 2
            pic_y = pic_area_y + (pic_area_h - new_h) // 2
            
            # Paste picture onto main image
            img_rgba = img.convert("RGBA")
            img_rgba.paste(rounded_pic, (pic_x, pic_y), rounded_pic)
            img = img_rgba.convert("RGB")
            draw = ImageDraw.Draw(img)
            
        except Exception as e:
            print(f"Warning: Could not load picture {intro_image}: {e}")
            intro_image = None  # Fall back to no-picture layout
    
    if intro_image:
        # Player name centered at 25% of slate width (below picture)
        name_bbox = draw.textbbox((0, 0), name, font=name_font)
        name_w = name_bbox[2] - name_bbox[0]
        name_x = int(W * 0.33 - name_w // 2)  # Center at 33% of slate width
        name_y = pic_area_y + pic_area_h + 30
        draw.text((name_x, name_y), name, fill=data_color, font=name_font)
        
        # Stats centered at 75% of slate width
        text_center_x = int(W * 0.66)  # Center at 66% of slate width
        
        # Calculate total height needed for stats
        line_spacing = 85
        total_height = len(stats_elements) * line_spacing - (line_spacing - 50) if stats_elements else 0
        start_y = (H - total_height) // 2
        
        current_y = start_y
        for label, text, font, color, is_name in stats_elements:
            # Label and data on separate lines, centered
            bbox = draw.textbbox((0, 0), label, font=label_font)
            label_w = bbox[2] - bbox[0]
            label_x = text_center_x - label_w // 2
            draw.text((label_x, current_y), label, fill=label_color, font=label_font)
            
            bbox = draw.textbbox((0, 0), text, font=data_font)
            data_w = bbox[2] - bbox[0]
            data_x = text_center_x - data_w // 2
            draw.text((data_x, current_y + 35), text, fill=data_color, font=data_font)
            current_y += line_spacing
    else:
        # No picture: name centered below "PLAYER PROFILE" header, then stats below
        
        # Player name centered below header
        name_bbox = draw.textbbox((0, 0), name, font=name_font)
        name_w = name_bbox[2] - name_bbox[0]
        name_x = (W - name_w) // 2
        name_y = header_y + 80  # Below the header
        draw.text((name_x, name_y), name, fill=data_color, font=name_font)
        
        # Stats centered below name
        text_center_x = W // 2
        
        # Calculate total height needed for stats
        line_spacing = 95
        total_height = len(stats_elements) * line_spacing - (line_spacing - 60) if stats_elements else 0
        start_y = name_y + 100  # Below name with some spacing
        
        current_y = start_y
        for label, text, font, color, is_name in stats_elements:
            # Label and data on separate lines, centered
            bbox = draw.textbbox((0, 0), label, font=label_font)
            label_w = bbox[2] - bbox[0]
            label_x = text_center_x - label_w // 2
            draw.text((label_x, current_y), label, fill=label_color, font=label_font)
            
            bbox = draw.textbbox((0, 0), text, font=data_font)
            data_w = bbox[2] - bbox[0]
            data_x = text_center_x - data_w // 2
            draw.text((data_x, current_y + 35), text, fill=data_color, font=data_font)
            current_y += line_spacing

    slate_png = work / "slate.png"
    img.save(slate_png)

    # Convert to video
    run([
        FFMPEG_CMD,"-y",
        "-loop","1","-i",str(slate_png),
        "-t","5",
        "-r",str(FPS),
        "-c:v","libx264","-preset","veryfast","-crf",str(CRF),
        "-pix_fmt","yuv420p",
        "-an",
        str(out_path)
    ])

def make_slate_with_video(player: dict, out_path: pathlib.Path, work: pathlib.Path, intro_video: pathlib.Path):
    """Create slate using intro video as background with text overlay."""
    temp_resized = work / "intro_resized.mp4"
    temp_with_text = work / "intro_with_text.mp4"
    
    # First, resize intro video to 1920x1080 and ensure it's exactly 5 seconds
    run([
        "ffmpeg", "-y",
        "-i", str(intro_video),
        "-vf", f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps={FPS}",
        "-t", "5",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(CRF),
        "-pix_fmt", "yuv420p",
        "-an",
        str(temp_resized)
    ])
    
    # Create text overlay
    name = (player.get("name") or "Player Name")
    pos = (player.get("position") or "")
    grad = str(player.get("grad_year") or "")
    
    # Build filter for text overlay
    text_filters = []
    
    # Main name with background
    name_y = "h*0.75"
    pos_y = "h*0.82"
    text_filters.append(f"drawtext=text='{name}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=64:fontcolor=white:x=(w-text_w)/2:y={name_y}:box=1:boxcolor=black@0.7:boxborderw=10")
    
    # Position and grad year
    if pos or grad:
        pos_line = pos + (f"  •  Class of {grad}" if grad else "")
        text_filters.append(f"drawtext=text='{pos_line}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:fontsize=40:fontcolor=white:x=(w-text_w)/2:y={pos_y}:box=1:boxcolor=black@0.7:boxborderw=8")
    
    filter_str = ",".join(text_filters)
    
    # Apply text overlay
    run([
        "ffmpeg", "-y",
        "-i", str(temp_resized),
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(CRF),
        "-pix_fmt", "yuv420p",
        "-an",
        str(out_path)
    ])
    
    # Clean up temp file
    temp_resized.unlink(missing_ok=True)

# -------------------- debug --------------------

def debug_mark(std_mp4: pathlib.Path, frame_idx: int, px: int, py: int, work: pathlib.Path, tag: str):
    frm = work / f"debug_{tag}_frame.png"
    sel = f"select='eq(n\\,{frame_idx})',setpts=N/FRAME_RATE/TB,fps={FPS}"
    run([FFMPEG_CMD,"-y","-i",str(std_mp4),"-vf",sel,"-vsync","vfr","-frames:v","1",str(frm)])
    im = Image.open(frm).convert("RGBA")
    d = ImageDraw.Draw(im)
    L = 22
    d.line((px-L, py, px+L, py), fill=(255,0,0,255), width=3)
    d.line((px, py-L, px, py+L), fill=(255,0,0,255), width=3)
    d.ellipse((px-4, py-4, px+4, py+4), outline=(255,0,0,255), width=3)
    out = work / f"debug_{tag}_marked.png"
    im.save(out)
    print(f"🔍 Debug saved: {out}")

# -------------------- segments (video-only CFR 30) --------------------

def build_video_frames(std_mp4: pathlib.Path, start_f: int, end_f: int, out_v: pathlib.Path):
    if end_f < start_f:
        run([FFMPEG_CMD,"-y","-f","lavfi","-i","color=c=black:s=1920x1080","-t","0.0334",
             "-r",str(FPS),"-c:v","libx264","-preset","veryfast","-crf",str(CRF),"-pix_fmt","yuv420p","-an",str(out_v)])
        return
    sel = f"select='between(n\\,{start_f}\\,{end_f})',setpts=N/FRAME_RATE/TB,fps={FPS}"
    run([FFMPEG_CMD,"-y","-i",str(std_mp4),"-vf",sel,
         "-c:v","libx264","-preset","veryfast","-crf",str(CRF),"-pix_fmt","yuv420p","-an",str(out_v)])

def concat_videos(files: list[pathlib.Path], out_path: pathlib.Path):
    inputs = []
    for f in files: inputs += ["-i", str(f)]
    streams = "".join([f"[{i}:v]" for i in range(len(files))])
    run([FFMPEG_CMD,"-y",*inputs,
         "-filter_complex",f"{streams}concat=n={len(files)}:v=1:a=0[v]",
         "-map","[v]",
         "-c:v","libx264","-preset","veryfast","-crf",str(CRF),
         "-pix_fmt","yuv420p",
         str(out_path)])

# -------------------- freeze + compose --------------------

def make_freeze_with_spot(std_mp4: pathlib.Path, px: int, py: int, radius: int,
                          out_mp4: pathlib.Path, start_trim: float, end_trim: float,
                          spot_frame: int, work: pathlib.Path, still_dur: float = 1.25):
    fps = proxy_fps(std_mp4)
    total_f = proxy_frame_count(std_mp4)
    start_f = to_frame(start_trim, fps)
    end_f_cut = total_f - 1 - to_frame(end_trim, fps)
    spot_f = max(start_f, min(int(spot_frame), end_f_cut))
    print(f"[clip] fps={fps:.3f} total_f={total_f} start_f={start_f} spot_f={spot_f} end_f={end_f_cut}")

    debug_mark(std_mp4, spot_f, px, py, work, out_mp4.stem)

    # Freeze frame -> PNG
    frame_png  = work / (out_mp4.stem + "_frame.png")
    sel = f"select='eq(n\\,{spot_f})',setpts=N/FRAME_RATE/TB,fps={FPS}"
    run([FFMPEG_CMD,"-y","-i",str(std_mp4),"-vf",sel,"-vsync","vfr","-frames:v","1",str(frame_png)])

    # Composite ring
    ring_png = work / f"{out_mp4.stem}_ring.png"
    make_ring_png(ring_png, max(6, int(radius)))
    frame_annot = work / (out_mp4.stem + "_frame_annot.png")
    pil_composite_ring_on_png(frame_png, ring_png, px, py, frame_annot)

    # 1.25s still
    still = work / (out_mp4.stem + "_still.mp4")
    run([FFMPEG_CMD,"-y","-loop","1","-i",str(frame_annot),"-t",str(still_dur),
         "-r",str(FPS),"-c:v","libx264","-preset","veryfast","-crf",str(CRF),"-pix_fmt","yuv420p","-an",str(still)])

    parts = []
    if spot_f > start_f:
        pre_v = work / (out_mp4.stem + "_pre.mp4")
        build_video_frames(std_mp4, start_f, spot_f - 1, pre_v)
        parts.append(pre_v)

    parts.append(still)

    post_v = work / (out_mp4.stem + "_post.mp4")
    build_video_frames(std_mp4, spot_f, end_f_cut, post_v)
    parts.append(post_v)

    concat_videos(parts, out_mp4)

# -------------------- main --------------------

def main():
    ap = argparse.ArgumentParser(description="Render highlights for an athlete (audio-free)")
    ap.add_argument("--athlete", type=str, help="Athlete folder name under ./athletes")
    ap.add_argument("--dir", type=str, help="Full path to athlete folder")
    ap.add_argument("--keep-work", action="store_true")
    ap.add_argument("--reset-intro", action="store_true", help="Reset intro media selection and choose again")
    args = ap.parse_args()

    if args.dir:
        base = pathlib.Path(args.dir).resolve()
    elif args.athlete:
        base = (ATHLETES / args.athlete).resolve()
    else:
        base = choose_athlete_interactive()
        if base is None: sys.exit(0)

    if not base.exists() or not base.is_dir():
        print(f"Invalid athlete directory: {base}")
        sys.exit(1)

    ensure_dirs(base)
    project_path = base / "project.json"
    work = base / "work"
    output = base / "output"

    if not project_path.exists():
        print(f"{project_path} not found. Run mark_play.py first.")
        sys.exit(1)

    data = json.loads(project_path.read_text())
    include_intro = bool(data.get("include_intro", True))
    
    # Handle intro media selection if intro is enabled
    if include_intro:
        # Check if intro media has already been selected (and not reset)
        if "intro_media" not in data or args.reset_intro:
            print(f"\n🎬 Resetting intro media selection for {base.name}")
            
            # Check for intro media files
            intro_dir = base / "intro"
            intro_files = find_intro_files(intro_dir)
            intro_media_path = None
            
            if intro_files["images"] or intro_files["videos"]:
                intro_media = choose_intro_media(intro_files)
                if intro_media:
                    # Store relative path in project.json
                    intro_media_path = str(intro_media.relative_to(base))
                    print(f"Selected intro media: {intro_media.name}")
                else:
                    print("Using text-only slate")
            else:
                print("No intro media files found - using text-only slate")
            
            # Save the selection to project.json
            data["intro_media"] = intro_media_path
            project_path.write_text(json.dumps(data, indent=2))
        else:
            intro_media_path = data.get("intro_media")
            if intro_media_path:
                print(f"Using intro media: {pathlib.Path(intro_media_path).name}")
            else:
                print("Using text-only slate")

    processed = []
    for i, c in enumerate(data.get("clips", []), 1):
        # Resolve std_file if present, otherwise use default path
        std_path = resolve_path(base, c.get("std_file"))
        if std_path is None:
            std_path = base / "work" / "proxies" / f"clip{i:02d}_std.mp4"

        # Ensure proxy exists (build it if missing) using original file path
        src_path = resolve_path(base, c.get("file"))
        if src_path is None:
            raise RuntimeError(f"Clip {i}: source 'file' missing in project.json")
        ensure_proxy(src_path, std_path)

        # Marker/spot values (prefer *_std if present)
        mx = int(c.get("marker_x_std", c.get("marker_x", 960)))
        my = int(c.get("marker_y_std", c.get("marker_y", 540)))
        radius_std = int(c.get("radius_std", c.get("radius", 72)))
        spot_frame_std = int(c.get("spot_frame_std", -1))
        if spot_frame_std < 0:
            fps = proxy_fps(std_path)
            spot_frame_std = to_frame(float(c.get("spot_time", 0.0)), fps)

        out = work / f"clip{i:02d}_done.mp4"
        make_freeze_with_spot(std_path, mx, my, radius_std, out,
                              float(c.get("start_trim", 0.0)),
                              float(c.get("end_trim", 0.0)),
                              spot_frame_std, work,
                              still_dur=1.25)
        processed.append(out)

    if not processed:
        print("No processed clips.")
        sys.exit(0)

    body = work / "body.mp4"
    concat_videos(processed, body)

    outputs = [body]
    if include_intro:
        slate = work / "slate.mp4"
        
        # Get intro media from project.json
        intro_media = None
        intro_media_path = data.get("intro_media")
        if intro_media_path:
            intro_media = base / intro_media_path
            if not intro_media.exists():
                print(f"Warning: Intro media file not found: {intro_media}")
                intro_media = None
        
        make_slate(data.get("player", {}), slate, work, intro_media)
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

