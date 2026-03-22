# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Slate generation for intro screens."""

from __future__ import annotations

import pathlib

from PIL import ImageFont

from render.utils import FFMPEG_CMD, FPS, CRF, find_dejavu_font, run


def _load_font(size: int):
    """Load a font for Pillow rendering."""
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
    """Interactively choose an intro media file."""
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
                return options[idx - 1]
        print("Invalid choice. Try again.")


def make_slate(player: dict, out_path: pathlib.Path, work: pathlib.Path,
               intro_media: pathlib.Path | None = None, template_name: str | None = None):
    """Create intro slate with optional picture or video integration."""
    if intro_media and intro_media.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}:
        make_slate_with_video(player, out_path, work, intro_media, template_name=template_name)
        return

    make_slate_with_image(player, out_path, work, intro_media, template_name=template_name)


def make_slate_with_image(player: dict, out_path: pathlib.Path, work: pathlib.Path,
                          intro_image: pathlib.Path | None = None, template_name: str | None = None):
    """Create slate with player profile card using the selected template."""
    from slate_templates import get_template

    template = get_template(template_name)
    print(f"  Using slate template: {template.display_name}")

    img = template.render_image_slate(player, intro_image)

    slate_png = work / "slate.png"
    img.save(slate_png)

    run([
        FFMPEG_CMD, "-y",
        "-loop", "1", "-i", str(slate_png),
        "-t", "5",
        "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(CRF),
        "-pix_fmt", "yuv420p",
        "-an",
        str(out_path)
    ])


def make_slate_with_video(player: dict, out_path: pathlib.Path, work: pathlib.Path,
                          intro_video: pathlib.Path, template_name: str | None = None):
    """Create slate using intro video as background with text overlay."""
    from slate_templates import get_template

    template = get_template(template_name)
    print(f"  Using slate template: {template.display_name}")

    temp_resized = work / "intro_resized.mp4"

    run([
        FFMPEG_CMD, "-y",
        "-i", str(intro_video),
        "-vf", f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps={FPS}",
        "-t", "5",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(CRF),
        "-pix_fmt", "yuv420p",
        "-an",
        str(temp_resized)
    ])

    font_bold = find_dejavu_font()
    font_regular = font_bold.replace("-Bold", "") if font_bold and "-Bold" in font_bold else font_bold
    filter_str = template.get_video_drawtext_filters(player, font_bold, font_regular)

    run([
        FFMPEG_CMD, "-y",
        "-i", str(temp_resized),
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(CRF),
        "-pix_fmt", "yuv420p",
        "-an",
        str(out_path)
    ])

    temp_resized.unlink(missing_ok=True)
