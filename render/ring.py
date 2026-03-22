# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Ring/spotlight rendering and freeze frame composition."""

from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw, ImageFont

from render.utils import FFMPEG_CMD, FPS, CRF, PROXY_W, run


def make_ring_png(out_path: pathlib.Path, radius: int, thickness: int = 8):
    """Create a ring overlay PNG."""
    size = max(2, radius * 2 + thickness * 6)
    main_color = (200, 0, 0, 235)
    glow_color = (200, 0, 0, 110)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bbox1 = [(size / 2 - radius, size / 2 - radius), (size / 2 + radius, size / 2 + radius)]
    d.ellipse(bbox1, outline=main_color, width=thickness)
    bbox2 = [(size / 2 - radius - 5, size / 2 - radius - 5), (size / 2 + radius + 5, size / 2 + radius + 5)]
    d.ellipse(bbox2, outline=glow_color, width=max(3, thickness // 2))
    img.save(out_path)


def pil_composite_ring_on_png(frame_png: pathlib.Path, ring_png: pathlib.Path,
                               px: int, py: int, out_png: pathlib.Path):
    """Composite ring overlay onto a frame image."""
    base = Image.open(frame_png).convert("RGBA")
    ring = Image.open(ring_png).convert("RGBA")
    x = int(round(px - ring.width / 2))
    y = int(round(py - ring.height / 2))
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.paste(ring, (x, y), ring)
    Image.alpha_composite(base, layer).save(out_png)


def debug_mark(std_mp4: pathlib.Path, frame_idx: int, px: int, py: int,
               work: pathlib.Path, tag: str):
    """Save a debug image showing marker position."""
    frm = work / f"debug_{tag}_frame.png"
    sel = f"select='eq(n\\,{frame_idx})',setpts=N/FRAME_RATE/TB,fps={FPS}"
    run([FFMPEG_CMD, "-y", "-i", str(std_mp4), "-vf", sel, "-vsync", "vfr",
         "-frames:v", "1", str(frm)])
    im = Image.open(frm).convert("RGBA")
    d = ImageDraw.Draw(im)
    L = 22
    d.line((px - L, py, px + L, py), fill=(255, 0, 0, 255), width=3)
    d.line((px, py - L, px, py + L), fill=(255, 0, 0, 255), width=3)
    d.ellipse((px - 4, py - 4, px + 4, py + 4), outline=(255, 0, 0, 255), width=3)
    out = work / f"debug_{tag}_marked.png"
    im.save(out)
    print(f"🔍 Debug saved: {out}")
