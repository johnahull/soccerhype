# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Video operations: zoom, concat, overlays, and frame extraction."""

from __future__ import annotations

import pathlib
import subprocess

from constants import (
    SECTIONS,
    OVERLAY_DURATION_DEFAULT,
    OVERLAY_FADE_IN,
    OVERLAY_FADE_OUT,
    OVERLAY_DURATION_MIN,
    OVERLAY_MARGIN,
    OVERLAY_FONT_SIZE,
    OVERLAY_X_MARGIN,
    OVERLAY_Y_OFFSET,
    OVERLAY_BOX_BORDER,
)

from render.utils import FFMPEG_CMD, FPS, CRF, PROXY_W, escape_drawtext, find_dejavu_font, run
from render.proxy import proxy_fps, proxy_frame_count, to_frame, duration_of
from render.ring import make_ring_png, pil_composite_ring_on_png, debug_mark


def transform_for_zoom(mx: int, my: int, radius: int, video_w: int, video_h: int,
                       zoom: float) -> tuple[int, int, int]:
    """Transform marker coordinates and radius for center-zoomed output."""
    if zoom <= 1.0:
        return mx, my, radius

    cx, cy = video_w / 2, video_h / 2
    new_mx = int(round(cx + (mx - cx) * zoom))
    new_my = int(round(cy + (my - cy) * zoom))
    new_radius = int(round(radius * zoom))

    return new_mx, new_my, new_radius


def build_zoom_filter(video_w: int, video_h: int, zoom: float) -> str:
    """Build FFmpeg filter string for center-crop zoom."""
    if zoom <= 1.0:
        return ""

    crop_w = int(video_w / zoom) & ~1
    crop_h = int(video_h / zoom) & ~1
    crop_x = (video_w - crop_w) // 2
    crop_y = (video_h - crop_h) // 2

    return f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={video_w}:{video_h},setsar=1"


def build_video_frames(std_mp4: pathlib.Path, start_f: int, end_f: int,
                       out_v: pathlib.Path, zoom: float = 1.0):
    """Extract video frames with optional zoom applied."""
    if end_f < start_f:
        run([FFMPEG_CMD, "-y", "-f", "lavfi", "-i", "color=c=black:s=1920x1080", "-t", "0.0334",
             "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", str(CRF),
             "-pix_fmt", "yuv420p", "-an", str(out_v)])
        return

    sel = f"select='between(n\\,{start_f}\\,{end_f})',setpts=N/FRAME_RATE/TB"

    if zoom > 1.0:
        zoom_filter = build_zoom_filter(PROXY_W, 1080, zoom)
        vf = f"{sel},{zoom_filter},fps={FPS}"
    else:
        vf = f"{sel},fps={FPS}"

    run([FFMPEG_CMD, "-y", "-i", str(std_mp4), "-vf", vf,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", str(CRF),
         "-pix_fmt", "yuv420p", "-an", str(out_v)])


def concat_videos(files: list[pathlib.Path], out_path: pathlib.Path):
    """Concatenate multiple video files."""
    inputs = []
    for f in files:
        inputs += ["-i", str(f)]
    streams = "".join([f"[{i}:v]" for i in range(len(files))])
    run([FFMPEG_CMD, "-y", *inputs,
         "-filter_complex", f"{streams}concat=n={len(files)}:v=1:a=0[v]",
         "-map", "[v]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", str(CRF),
         "-pix_fmt", "yuv420p",
         str(out_path)])


def add_lower_third_overlay(input_mp4: pathlib.Path, output_mp4: pathlib.Path,
                            section_text: str, duration: float = OVERLAY_DURATION_DEFAULT):
    """Add lower-third text overlay to the first few seconds of a video."""
    if not section_text or not section_text.strip():
        raise ValueError("Section text cannot be empty")
    if len(section_text) > 50:
        raise ValueError(f"Section text too long: {len(section_text)} chars (max 50)")
    if section_text not in SECTIONS:
        print(f"Warning: '{section_text}' is not a predefined section")

    if duration <= 0 or duration > 10:
        raise ValueError(f"Duration must be greater than 0 and at most 10 seconds, got {duration}")

    safe_text = escape_drawtext(section_text.upper())
    font_path = find_dejavu_font()

    alpha_expr = (
        f"if(lt(t,{OVERLAY_FADE_IN}),t/{OVERLAY_FADE_IN},"
        f"if(lt(t,{duration - OVERLAY_FADE_OUT}),1,"
        f"({duration}-t)/{OVERLAY_FADE_OUT}))"
    )

    filter_parts = [
        f"drawtext=text='{safe_text}'",
        f"fontsize={OVERLAY_FONT_SIZE}",
        f"fontcolor=white",
        f"x={OVERLAY_X_MARGIN}",
        f"y=h-{OVERLAY_Y_OFFSET}",
        f"box=1",
        f"boxcolor=black@0.7",
        f"boxborderw={OVERLAY_BOX_BORDER}",
        f"enable='lt(t,{duration})'",
        f"alpha='{alpha_expr}'"
    ]

    if font_path:
        filter_parts.insert(1, f"fontfile={font_path}")

    filter_str = ":".join(filter_parts)

    run([
        FFMPEG_CMD, "-y",
        "-i", str(input_mp4),
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(CRF),
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_mp4)
    ])


def make_freeze_with_spot(std_mp4: pathlib.Path, px: int, py: int, radius: int,
                          out_mp4: pathlib.Path, start_trim: float, end_trim: float,
                          spot_frame: int, work: pathlib.Path, zoom: float = 1.0,
                          still_dur: float = 1.25):
    """Create clip with freeze frame and ring overlay, with optional zoom."""
    fps = proxy_fps(std_mp4)
    total_f = proxy_frame_count(std_mp4)
    start_f = to_frame(start_trim, fps)
    end_f_cut = total_f - 1 - to_frame(end_trim, fps)
    spot_f = max(start_f, min(int(spot_frame), end_f_cut))
    print(f"[clip] fps={fps:.3f} total_f={total_f} start_f={start_f} spot_f={spot_f} end_f={end_f_cut} zoom={zoom:.2f}x")

    debug_mark(std_mp4, spot_f, px, py, work, out_mp4.stem)

    video_h = 1080
    zoomed_px, zoomed_py, zoomed_radius = transform_for_zoom(px, py, radius, PROXY_W, video_h, zoom)

    # Freeze frame -> PNG (with zoom applied)
    frame_png = work / (out_mp4.stem + "_frame.png")
    sel = f"select='eq(n\\,{spot_f})',setpts=N/FRAME_RATE/TB"
    if zoom > 1.0:
        zoom_filter = build_zoom_filter(PROXY_W, video_h, zoom)
        vf = f"{sel},{zoom_filter}"
    else:
        vf = sel
    run([FFMPEG_CMD, "-y", "-i", str(std_mp4), "-vf", vf, "-vsync", "vfr",
         "-frames:v", "1", str(frame_png)])

    # Composite ring
    ring_png = work / f"{out_mp4.stem}_ring.png"
    make_ring_png(ring_png, max(6, zoomed_radius))
    frame_annot = work / (out_mp4.stem + "_frame_annot.png")
    pil_composite_ring_on_png(frame_png, ring_png, zoomed_px, zoomed_py, frame_annot)

    # Still frame video
    still = work / (out_mp4.stem + "_still.mp4")
    run([FFMPEG_CMD, "-y", "-loop", "1", "-i", str(frame_annot), "-t", str(still_dur),
         "-vf", "setsar=1", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
         "-crf", str(CRF), "-pix_fmt", "yuv420p", "-an", str(still)])

    parts = []
    if spot_f > start_f:
        pre_v = work / (out_mp4.stem + "_pre.mp4")
        build_video_frames(std_mp4, start_f, spot_f - 1, pre_v, zoom=zoom)
        parts.append(pre_v)

    parts.append(still)

    post_v = work / (out_mp4.stem + "_post.mp4")
    build_video_frames(std_mp4, spot_f, end_f_cut, post_v, zoom=zoom)
    parts.append(post_v)

    concat_videos(parts, out_mp4)
