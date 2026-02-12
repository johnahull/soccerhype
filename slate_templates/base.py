# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Base class and shared utilities for slate templates."""

from __future__ import annotations

import os
import pathlib
import platform
from abc import ABC, abstractmethod

from PIL import Image, ImageDraw, ImageFont


# ── shared font utilities ──────────────────────────────────────────

# Font cache to improve performance on repeated loads
_FONT_CACHE: dict[tuple[int, bool], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}

def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a TrueType font at the given size, falling back to default.

    Args:
        size: Font point size.
        bold: If True, prefer a bold variant.

    Returns:
        Cached font instance for improved performance.
    """
    cache_key = (size, bold)
    if cache_key in _FONT_CACHE:
        return _FONT_CACHE[cache_key]

    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]

    # Add cross-platform paths
    system = platform.system()
    if system == "Darwin":
        candidates += [
            "/System/Library/Fonts/Supplemental/DejaVuSans-Bold.ttf" if bold
            else "/System/Library/Fonts/Supplemental/DejaVuSans.ttf",
            "/Library/Fonts/DejaVuSans-Bold.ttf" if bold
            else "/Library/Fonts/DejaVuSans.ttf",
        ]
    elif system == "Windows":
        candidates += [
            "C:/Windows/Fonts/DejaVuSans-Bold.ttf" if bold
            else "C:/Windows/Fonts/DejaVuSans.ttf",
        ]

    font = None
    for path in candidates:
        try:
            font = ImageFont.truetype(path, size)
            break
        except (OSError, IOError):
            # Font file doesn't exist or can't be opened
            pass

    if font is None:
        font = ImageFont.load_default()

    _FONT_CACHE[cache_key] = font
    return font


def escape_drawtext(text: str) -> str:
    """Escape special characters for FFmpeg drawtext filter.

    FFmpeg drawtext has many special chars that need escaping:
    backslash, colon, percent, curly braces, square brackets, single quotes.
    """
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("%", "\\%")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    text = text.replace("'", "'\\''")
    return text


def find_dejavu_font() -> str:
    """Find DejaVu Sans Bold font across platforms.

    Returns path to font file, or empty string to use FFmpeg default.
    """
    system = platform.system()
    candidates: list[str] = []
    allowed_dirs: list[str] = []

    if system == "Linux":
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        ]
        allowed_dirs = ["/usr/share/fonts", "/usr/local/share/fonts"]
    elif system == "Darwin":
        candidates = [
            "/System/Library/Fonts/Supplemental/DejaVuSans-Bold.ttf",
            "/Library/Fonts/DejaVuSans-Bold.ttf",
            str(pathlib.Path.home() / "Library/Fonts/DejaVuSans-Bold.ttf"),
        ]
        allowed_dirs = ["/System/Library/Fonts", "/Library/Fonts",
                        str(pathlib.Path.home() / "Library/Fonts")]
    elif system == "Windows":
        candidates = [
            "C:/Windows/Fonts/DejaVuSans-Bold.ttf",
            str(pathlib.Path.home() / "AppData/Local/Microsoft/Windows/Fonts/DejaVuSans-Bold.ttf"),
        ]
        allowed_dirs = ["C:/Windows/Fonts", "C:\\Windows\\Fonts",
                        str(pathlib.Path.home() / "AppData/Local/Microsoft/Windows/Fonts")]

    for font_path in candidates:
        font_file = pathlib.Path(font_path).resolve()
        if font_file.exists():
            if font_file.suffix.lower() not in ['.ttf', '.otf', '.ttc']:
                continue
            if not os.access(font_file, os.R_OK):
                continue
            font_str = str(font_file)
            if not any(font_str.startswith(d) for d in allowed_dirs):
                continue
            return str(font_file)

    print("Warning: DejaVu Sans Bold font not found, using FFmpeg default font")
    return ""


def find_dejavu_regular() -> str:
    """Find DejaVu Sans (regular) font. Falls back to bold if not found."""
    bold = find_dejavu_font()
    if bold:
        regular = bold.replace("-Bold", "")
        if pathlib.Path(regular).exists():
            return regular
    return bold


# ── helper to extract player fields ────────────────────────────────

def extract_player_fields(player: dict) -> dict:
    """Pull common player fields from the data dict, with safe defaults."""
    return {
        "name": player.get("name") or "Player Name",
        "title": player.get("title") or "",
        "position": player.get("position") or "",
        "grad_year": str(player.get("grad_year") or ""),
        "club_team": player.get("club_team") or "",
        "high_school": player.get("high_school") or "",
        "height_weight": player.get("height_weight") or "",
        "gpa": player.get("gpa") or "",
        "email": player.get("email") or "",
        "phone": player.get("phone") or "",
    }


# ── abstract base ──────────────────────────────────────────────────

class SlateTemplate(ABC):
    """Abstract base for slate template designs."""

    name: str           # e.g. "classic"
    display_name: str   # e.g. "Classic"
    description: str    # One-line summary for the GUI

    # ── abstract methods that each template MUST implement ──

    @abstractmethod
    def render_image_slate(self, player: dict, intro_image: pathlib.Path | None) -> Image.Image:
        """Return a 1920x1080 PIL Image for image-based (or text-only) slates."""

    @abstractmethod
    def get_video_drawtext_filters(self, player: dict, font_bold: str, font_regular: str) -> str:
        """Return an FFmpeg drawtext filter string for video-background slates."""

    # ── optional override ──

    def render_preview(self, player: dict, intro_image: pathlib.Path | None) -> Image.Image:
        """Return a 384x216 thumbnail preview (default: render full then downscale)."""
        full = self.render_image_slate(player, intro_image)
        return full.resize((384, 216), Image.LANCZOS)
