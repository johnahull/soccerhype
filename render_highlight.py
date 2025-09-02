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
        ["ffprobe","-v","error","-show_entries","format=duration",
         "-of","default=nk=1:nw=1", str(path)],
        capture_output=True, text=True
    )
    try:
        return float(p.stdout.strip())
    except:
        return 0.0

def proxy_fps(path: pathlib.Path) -> float:
    p = subprocess.run(
        ["ffprobe","-v","error","-select_streams","v:0",
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
        ["ffprobe","-v","error","-select_streams","v:0","-count_frames",
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
        "ffmpeg","-y",
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
    """Create slate with optional player picture embedded."""
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    name  = (player.get("name") or "Player Name")
    pos   = (player.get("position") or "")
    grad  = str(player.get("grad_year") or "")
    club  = (player.get("club_team") or "")
    hs    = (player.get("high_school") or "")
    hw    = (player.get("height_weight") or "")
    gpa   = (player.get("gpa") or "")
    email = (player.get("email") or "")
    phone = (player.get("phone") or "")

    lines = []
    lines.append((name, 72))
    pos_line = pos + (f"  •  Class of {grad}" if grad else "")
    if pos_line.strip():
        lines.append((pos_line.strip(), 44))
    if club:  lines.append((club,          40))
    if hs:    lines.append((hs,            40))
    if hw:    lines.append((hw,            40))
    if gpa:   lines.append((f"GPA: {gpa}", 40))
    if email: lines.append((email,         36))
    if phone: lines.append((phone,         36))

    # Layout calculation considering picture placement
    if intro_image:
        # Picture on left, text on right layout
        picture_area_w = W // 2  # Left half for picture
        text_start_x = picture_area_w + 50  # Add some padding
        text_area_w = W - text_start_x - 50  # Right half minus padding
        
        # Load and resize picture
        try:
            player_pic = Image.open(intro_image).convert("RGBA")
            # Calculate picture size (maintain aspect ratio, fit in left half)
            pic_max_w = picture_area_w - 100  # Leave padding
            pic_max_h = H - 200  # Leave top/bottom padding
            
            pic_w, pic_h = player_pic.size
            scale = min(pic_max_w / pic_w, pic_max_h / pic_h, 1.0)
            new_w, new_h = int(pic_w * scale), int(pic_h * scale)
            player_pic = player_pic.resize((new_w, new_h), Image.LANCZOS)
            
            # Center picture in left area
            pic_x = (picture_area_w - new_w) // 2
            pic_y = (H - new_h) // 2
            
            # Create a background layer for the image
            pic_layer = Image.new("RGBA", img.size, (0,0,0,0))
            pic_layer.paste(player_pic, (pic_x, pic_y), player_pic)
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, pic_layer).convert("RGB")
            # Recreate draw object after compositing
            draw = ImageDraw.Draw(img)
            
        except Exception as e:
            print(f"Warning: Could not load picture {intro_image}: {e}")
            text_start_x = 0
            text_area_w = W
    else:
        # No picture - center text normally
        text_start_x = 0
        text_area_w = W

    # Calculate text layout
    spacing = 18
    fonts, widths, heights = [], [], []
    for text, sz in lines:
        f = _load_font(sz); fonts.append(f)
        l,t,r,b = draw.textbbox((0,0), text, font=f)
        widths.append(r-l); heights.append(b-t)
    
    total_h = sum(heights) + spacing * (len(lines)-1) if lines else 0
    y = (H - total_h) // 2

    # Draw text
    for (text, _), f, w, h in zip(lines, fonts, widths, heights):
        if intro_image:
            # Center text in right half
            x = text_start_x + (text_area_w - w) // 2
        else:
            # Center text across full width
            x = (W - w) // 2
        draw.text((x, y), text, fill=(255,255,255), font=f)
        y += h + spacing

    slate_png = work / "slate.png"
    img.save(slate_png)

    # Convert to video
    run([
        "ffmpeg","-y",
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
    text_filters.append(f"drawtext=text='{name}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=64:fontcolor=white:x=(w-text_w)/2:y=h*0.75:box=1:boxcolor=black@0.7:boxborderw=10")
    
    # Position and grad year
    if pos or grad:
        pos_line = pos + (f"  •  Class of {grad}" if grad else "")
        text_filters.append(f"drawtext=text='{pos_line}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:fontsize=40:fontcolor=white:x=(w-text_w)/2:y=h*0.82:box=1:boxcolor=black@0.7:boxborderw=8")
    
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
    run(["ffmpeg","-y","-i",str(std_mp4),"-vf",sel,"-vsync","vfr","-frames:v","1",str(frm)])
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
        run(["ffmpeg","-y","-f","lavfi","-i","color=c=black:s=1920x1080","-t","0.0334",
             "-r",str(FPS),"-c:v","libx264","-preset","veryfast","-crf",str(CRF),"-pix_fmt","yuv420p","-an",str(out_v)])
        return
    sel = f"select='between(n\\,{start_f}\\,{end_f})',setpts=N/FRAME_RATE/TB,fps={FPS}"
    run(["ffmpeg","-y","-i",str(std_mp4),"-vf",sel,
         "-c:v","libx264","-preset","veryfast","-crf",str(CRF),"-pix_fmt","yuv420p","-an",str(out_v)])

def concat_videos(files: list[pathlib.Path], out_path: pathlib.Path):
    inputs = []
    for f in files: inputs += ["-i", str(f)]
    streams = "".join([f"[{i}:v]" for i in range(len(files))])
    run(["ffmpeg","-y",*inputs,
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
    run(["ffmpeg","-y","-i",str(std_mp4),"-vf",sel,"-vsync","vfr","-frames:v","1",str(frame_png)])

    # Composite ring
    ring_png = work / f"{out_mp4.stem}_ring.png"
    make_ring_png(ring_png, max(6, int(radius)))
    frame_annot = work / (out_mp4.stem + "_frame_annot.png")
    pil_composite_ring_on_png(frame_png, ring_png, px, py, frame_annot)

    # 1.25s still
    still = work / (out_mp4.stem + "_still.mp4")
    run(["ffmpeg","-y","-loop","1","-i",str(frame_annot),"-t",str(still_dur),
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
            print(f"\n🎬 Setting up intro slate for {base.name}")
            
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
                print(f"Using previously selected intro media: {pathlib.Path(intro_media_path).name}")
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

