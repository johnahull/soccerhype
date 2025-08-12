#!/usr/bin/env python3
# render_highlight.py
# Frame-accurate highlight builder (audio-free).
# - Uses standardized proxies + standardized coordinates from project.json (created by mark_play.py).
# - 1.25s freeze with a dark red ring (baked with Pillow), then straight cut to live.
# - Optional intro slate (Pillow).
# - CFR 30 output, yuv420p, libx264, CRF=18.
# - Video-only pipeline (no audio anywhere) for robust concat.
#
# Usage:
#   python render_highlight.py [--keep-work]
#
# Inputs:
#   project.json
#
# Outputs:
#   out/final.mp4
#   (debug PNGs in work/ if --keep-work is used)

import json
import pathlib
import subprocess
import shutil
import argparse
from PIL import Image, ImageDraw, ImageFont

WORK = pathlib.Path("work")
OUT = pathlib.Path("out")
PROJECT_JSON = pathlib.Path("project.json")

FPS = 30
CRF = 18

# ---------- helpers ----------

def run(cmd_list):
    print("•", " ".join(cmd_list))
    if subprocess.call(cmd_list) != 0:
        raise RuntimeError("Command failed")

def ensure_dirs():
    WORK.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)

def clear_work_dir():
    # remove all files/dirs inside work/
    for p in WORK.glob("*"):
        try:
            p.unlink()
        except IsADirectoryError:
            shutil.rmtree(p)

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
        except Exception:
            pass
    try:
        return float(s)
    except Exception:
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
    # fallback if nb_read_frames isn't available
    fps = proxy_fps(path)
    dur = duration_of(path)
    return max(1, int(round(fps * dur)))

def to_frame(t: float, fps: float) -> int:
    return max(0, int(round(t * fps)))

# ---------- ring assets ----------

def make_ring_png(out_path: pathlib.Path, radius: int, thickness: int = 8):
    """Dark red ring with soft outer glow."""
    size = max(2, radius * 2 + thickness * 6)
    main_color  = (200, 0, 0, 235)   # dark red (opaque)
    glow_color  = (200, 0, 0, 110)   # softer red glow
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
    out = Image.alpha_composite(base, layer)
    out.save(out_png)

# ---------- concat (video-only) ----------

def concat_ffmpeg(files, out_path: pathlib.Path):
    """Safe video-only concat with re-encode."""
    inputs = []
    for f in files:
        inputs += ["-i", str(f)]
    # build [0:v][1:v]...[n:v]concat
    streams = "".join([f"[{i}:v]" for i in range(len(files))])
    run(["ffmpeg","-y",*inputs,
         "-filter_complex",f"{streams}concat=n={len(files)}:v=1:a=0[v]",
         "-map","[v]",
         "-c:v","libx264","-preset","veryfast","-crf",str(CRF),
         "-pix_fmt","yuv420p",
         str(out_path)])

# ---------- slate (Pillow -> looped video, no audio) ----------

def _load_font(size: int):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

def make_slate(player: dict, out_path: pathlib.Path):
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

    spacing = 18
    fonts, widths, heights = [], [], []
    for text, sz in lines:
        f = _load_font(sz); fonts.append(f)
        l,t,r,b = draw.textbbox((0,0), text, font=f)
        widths.append(r-l); heights.append(b-t)

    total_h = sum(heights) + spacing * (len(lines)-1) if lines else 0
    y = (H - total_h) // 2

    for (text, _), f, w, h in zip(lines, fonts, widths, heights):
        x = (W - w) // 2
        draw.text((x, y), text, fill=(255,255,255), font=f)
        y += h + spacing

    slate_png = WORK / "slate.png"
    img.save(slate_png)

    # 3s looped slate, video-only
    run([
        "ffmpeg","-y",
        "-loop","1","-i",str(slate_png),
        "-t","3",
        "-r",str(FPS),
        "-c:v","libx264","-preset","veryfast","-crf",str(CRF),
        "-pix_fmt","yuv420p",
        "-an",
        str(out_path)
    ])

# ---------- debug ----------

def debug_mark(std_mp4: pathlib.Path, frame_idx: int, px: int, py: int, tag: str):
    """Extract exact frame by index and draw a crosshair (sanity check)."""
    frm = WORK / f"debug_{tag}_frame.png"
    sel = f"select='eq(n\\,{frame_idx})',setpts=N/FRAME_RATE/TB,fps={FPS}"
    run(["ffmpeg","-y","-i",str(std_mp4),"-vf",sel,"-vsync","vfr","-frames:v","1",str(frm)])
    im = Image.open(frm).convert("RGBA")
    d = ImageDraw.Draw(im)
    L = 22
    d.line((px-L, py, px+L, py), fill=(255,0,0,255), width=3)
    d.line((px, py-L, px, py+L), fill=(255,0,0,255), width=3)
    d.ellipse((px-4, py-4, px+4, py+4), outline=(255,0,0,255), width=3)
    out = WORK / f"debug_{tag}_marked.png"
    im.save(out)
    print(f"🔍 Debug saved: {out}")

# ---------- segment builders (frame-accurate, CFR 30, video-only) ----------

def build_video_frames(std_mp4: pathlib.Path, start_f: int, end_f: int, out_v: pathlib.Path):
    """Inclusive end_f; force CFR FPS; strip audio."""
    # If the range is invalid, synthesize a 1-frame black (shouldn't happen but safe)
    if end_f < start_f:
        run([
            "ffmpeg","-y",
            "-f","lavfi","-i","color=c=black:s=1920x1080",
            "-t","0.0334",
            "-r",str(FPS),
            "-c:v","libx264","-preset","veryfast","-crf",str(CRF),
            "-pix_fmt","yuv420p",
            "-an",
            str(out_v)
        ])
        return

    sel = f"select='between(n\\,{start_f}\\,{end_f})',setpts=N/FRAME_RATE/TB,fps={FPS}"
    run(["ffmpeg","-y","-i",str(std_mp4),"-vf",sel,
         "-c:v","libx264","-preset","veryfast","-crf",str(CRF),
         "-pix_fmt","yuv420p",
         "-an",
         str(out_v)])

# ---------- freeze + compose + straight cut (video-only) ----------

def make_freeze_with_spot(std_mp4: pathlib.Path,
                          px: int, py: int,
                          radius: int,
                          out_mp4: pathlib.Path,
                          start_trim: float,
                          end_trim: float,
                          spot_frame: int,
                          still_dur: float = 1.25,
                          do_debug: bool = True):
    fps = proxy_fps(std_mp4)
    total_f = proxy_frame_count(std_mp4)

    start_f   = to_frame(start_trim, fps)
    end_f_cut = total_f - 1 - to_frame(end_trim, fps)
    spot_f    = max(start_f, min(int(spot_frame), end_f_cut))

    print(f"[clip] fps={fps:.3f} total_f={total_f} start_f={start_f} spot_f={spot_f} end_f={end_f_cut}")

    if do_debug:
        debug_mark(std_mp4, spot_f, px, py, out_mp4.stem)

    # 1) Extract exact freeze frame PNG
    frame_png  = WORK / (out_mp4.stem + "_frame.png")
    sel = f"select='eq(n\\,{spot_f})',setpts=N/FRAME_RATE/TB,fps={FPS}"
    run(["ffmpeg","-y","-i",str(std_mp4),"-vf",sel,"-vsync","vfr","-frames:v","1",str(frame_png)])

    # 2) Create ring and composite with Pillow (guaranteed visible)
    ring_png = WORK / f"{out_mp4.stem}_ring.png"
    make_ring_png(ring_png, max(6, int(radius)))
    frame_annot = WORK / (out_mp4.stem + "_frame_annot.png")
    pil_composite_ring_on_png(frame_png, ring_png, px, py, frame_annot)

    # 3) Build 1.25s still @ CFR 30, video-only
    still = WORK / (out_mp4.stem + "_still.mp4")
    run(["ffmpeg","-y","-loop","1","-i",str(frame_annot),
         "-t",str(still_dur),
         "-r",str(FPS),
         "-c:v","libx264","-preset","veryfast","-crf",str(CRF),
         "-pix_fmt","yuv420p",
         "-an",
         str(still)])

    # 4) PRE segment (if any) & POST segment (video-only)
    parts = []

    if spot_f > start_f:
        pre_v = WORK / (out_mp4.stem + "_pre.mp4")
        build_video_frames(std_mp4, start_f, spot_f - 1, pre_v)
        parts.append(pre_v)

    parts.append(still)

    post_v = WORK / (out_mp4.stem + "_post.mp4")
    build_video_frames(std_mp4, spot_f, end_f_cut, post_v)
    parts.append(post_v)

    # 5) Straight cut concat: PRE (opt) + STILL + POST
    concat_ffmpeg(parts, out_mp4)

# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Render soccer highlights (audio-free) from project.json")
    ap.add_argument("--keep-work", action="store_true", help="Keep work/ directory (debug files)")
    args = ap.parse_args()

    ensure_dirs()
    if not PROJECT_JSON.exists():
        print("project.json not found. Run mark_play.py first.")
        return

    data = json.loads(PROJECT_JSON.read_text())
    include_intro = bool(data.get("include_intro", True))

    processed = []
    for i, c in enumerate(data.get("clips", []), 1):
        std_path = pathlib.Path(c.get("std_file",""))
        if not std_path.exists():
            raise RuntimeError(f"Standardized proxy missing for clip {i}: {std_path}")

        mx = int(c.get("marker_x_std", c.get("marker_x", 960)))
        my = int(c.get("marker_y_std", c.get("marker_y", 540)))
        radius_std = int(c.get("radius_std", c.get("radius", 72)))
        spot_frame_std = int(c.get("spot_frame_std", -1))
        if spot_frame_std < 0:
            fps = proxy_fps(std_path)
            spot_frame_std = to_frame(float(c.get("spot_time", 0.0)), fps)

        out = WORK / f"clip{i:02d}_done.mp4"
        make_freeze_with_spot(
            std_path,
            mx, my,
            radius_std,
            out,
            float(c.get("start_trim", 0.0)),
            float(c.get("end_trim", 0.0)),
            spot_frame_std,
            still_dur=1.25,
            do_debug=True
        )
        processed.append(out)

    if not processed:
        print("No processed clips to concatenate.")
        return

    body = WORK / "body.mp4"
    concat_ffmpeg(processed, body)

    outputs = [body]
    if include_intro:
        slate = WORK / "slate.mp4"
        make_slate(data.get("player", {}), slate)
        outputs = [slate, body]

    final = OUT / "final.mp4"
    concat_ffmpeg(outputs, final)

    if not args.keep_work:
        clear_work_dir()

    print(f"\n✅ Final video saved to {final.resolve()}")
    if args.keep_work:
        print("ℹ️ Kept debug files in work/ (frame_annot, debug_*_marked.png, etc.)")

if __name__ == "__main__":
    main()

