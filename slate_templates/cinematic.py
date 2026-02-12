# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Cinematic slate template.

Dark gray with 100px letterbox bars top/bottom, subtle noise texture,
bottom-left aligned text, photo as darkened background if available.
Only shows name + position + grad_year.
"""

from __future__ import annotations

import pathlib
import random

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from .base import SlateTemplate, load_font, escape_drawtext, extract_player_fields


class CinematicTemplate(SlateTemplate):
    name = "cinematic"
    display_name = "Cinematic"
    description = "Letterbox bars, film-grain noise, bottom-left text"

    _BG = (30, 30, 32)
    _BAR = (0, 0, 0)
    _TEXT_WARM = (240, 230, 215)
    _TEXT_MUTED = (160, 155, 145)
    _BAR_H = 100

    @staticmethod
    def _add_noise(img: Image.Image, strength: int = 12) -> Image.Image:
        """Add subtle film-grain noise texture."""
        rng = random.Random(42)  # deterministic for consistency
        noise = Image.new("RGB", img.size)
        pixels = noise.load()
        w, h = img.size
        for y in range(h):
            for x in range(w):
                n = rng.randint(-strength, strength)
                pixels[x, y] = (128 + n, 128 + n, 128 + n)
        from PIL import ImageChops
        # Blend: soft light approximation via overlay at low opacity
        blended = Image.blend(img, noise, 0.06)
        return blended

    # ── image slate ────────────────────────────────────────────────

    def render_image_slate(self, player: dict, intro_image: pathlib.Path | None) -> Image.Image:
        W, H = 1920, 1080
        p = extract_player_fields(player)

        if intro_image:
            try:
                bg = Image.open(intro_image).convert("RGB")
                bg_w, bg_h = bg.size
                scale = max(W / bg_w, H / bg_h)
                bg = bg.resize((int(bg_w * scale), int(bg_h * scale)), Image.LANCZOS)
                # Top-anchored crop — keep head visible
                cx = bg.size[0] // 2
                bg = bg.crop((cx - W // 2, 0, cx + W // 2, H))
                bg = ImageEnhance.Brightness(bg).enhance(0.35)
                bg = bg.filter(ImageFilter.GaussianBlur(radius=2))
                img = bg
            except Exception as e:
                print(f"Warning: Could not load picture {intro_image}: {e}")
                img = Image.new("RGB", (W, H), self._BG)
        else:
            img = Image.new("RGB", (W, H), self._BG)

        # Add noise
        img = self._add_noise(img)

        draw = ImageDraw.Draw(img)

        # Letterbox bars
        draw.rectangle([(0, 0), (W, self._BAR_H)], fill=self._BAR)
        draw.rectangle([(0, H - self._BAR_H), (W, H)], fill=self._BAR)

        # Bottom-left text block (above bottom letterbox bar)
        name_font = load_font(64, bold=True)
        title_font = load_font(32, bold=True)
        detail_font = load_font(28)
        small_font = load_font(22)

        text_x = 120

        # Count how many lines we need so we can position upward from the bar
        lines = 0
        if p["title"]:
            lines += 1
        lines += 1  # name (always)
        if p["position"] or p["grad_year"]:
            lines += 1
        # Detail lines
        detail_line1_parts = []
        if p["club_team"]:
            detail_line1_parts.append(p["club_team"])
        if p["high_school"]:
            detail_line1_parts.append(p["high_school"])
        if detail_line1_parts:
            lines += 1
        detail_line2_parts = []
        if p["height_weight"]:
            detail_line2_parts.append(p["height_weight"])
        if p["gpa"]:
            detail_line2_parts.append(f"GPA {p['gpa']}")
        if detail_line2_parts:
            lines += 1
        detail_line3_parts = []
        if p["email"]:
            detail_line3_parts.append(p["email"].lower())
        if p["phone"]:
            detail_line3_parts.append(p["phone"])
        if detail_line3_parts:
            lines += 1

        # Start drawing from bottom, working upward
        cursor_y = H - self._BAR_H - 40 - lines * 50

        # Title
        if p["title"]:
            draw.text((text_x, cursor_y), p["title"], fill=self._TEXT_MUTED, font=title_font)
            cursor_y += 45

        # Name
        draw.text((text_x, cursor_y), p["name"], fill=self._TEXT_WARM, font=name_font)
        cursor_y += 80

        # Position + grad year
        sub_parts = []
        if p["position"]:
            sub_parts.append(p["position"].upper())
        if p["grad_year"]:
            sub_parts.append(f"Class of {p['grad_year']}")
        if sub_parts:
            draw.text((text_x, cursor_y), "  |  ".join(sub_parts),
                       fill=self._TEXT_MUTED, font=detail_font)
            cursor_y += 40

        # Club / High School
        if detail_line1_parts:
            draw.text((text_x, cursor_y), "  ·  ".join(detail_line1_parts),
                       fill=self._TEXT_MUTED, font=small_font)
            cursor_y += 32

        # Height/Weight / GPA
        if detail_line2_parts:
            draw.text((text_x, cursor_y), "  ·  ".join(detail_line2_parts),
                       fill=self._TEXT_MUTED, font=small_font)
            cursor_y += 32

        # Email / Phone
        if detail_line3_parts:
            draw.text((text_x, cursor_y), "  ·  ".join(detail_line3_parts),
                       fill=self._TEXT_MUTED, font=small_font)

        return img

    # ── video drawtext ─────────────────────────────────────────────

    def get_video_drawtext_filters(self, player: dict, font_bold: str, font_regular: str) -> str:
        p = extract_player_fields(player)
        safe_name = escape_drawtext(p["name"])
        sfb = escape_drawtext(font_bold) if font_bold else ""
        sfr = escape_drawtext(font_regular) if font_regular else ""

        filters: list[str] = []

        # Title – matches image ~y=640 (h-440)
        if p["title"]:
            safe_title = escape_drawtext(p["title"])
            parts = [
                f"drawtext=text='{safe_title}'",
                f"fontsize=32",
                f"fontcolor=#a09b91",
                f"x=120",
                f"y=h-440",
                f"box=1",
                f"boxcolor=black@0.4",
                f"boxborderw=6",
            ]
            if sfb:
                parts.insert(1, f"fontfile={sfb}")
            filters.append(":".join(parts))

        # Bottom-left name – matches image ~y=685 (h-395)
        parts = [
            f"drawtext=text='{safe_name}'",
            f"fontsize=64",
            f"fontcolor=#f0e6d7",
            f"x=120",
            f"y=h-395",
            f"box=1",
            f"boxcolor=black@0.5",
            f"boxborderw=10",
        ]
        if sfb:
            parts.insert(1, f"fontfile={sfb}")
        filters.append(":".join(parts))

        # Position + grad year – matches image ~y=765 (h-315)
        sub_parts = []
        if p["position"]:
            sub_parts.append(p["position"].upper())
        if p["grad_year"]:
            sub_parts.append(f"Class of {p['grad_year']}")
        if sub_parts:
            safe_sub = escape_drawtext("  |  ".join(sub_parts))
            parts = [
                f"drawtext=text='{safe_sub}'",
                f"fontsize=28",
                f"fontcolor=#a09b91",
                f"x=120",
                f"y=h-315",
                f"box=1",
                f"boxcolor=black@0.4",
                f"boxborderw=8",
            ]
            if sfr:
                parts.insert(1, f"fontfile={sfr}")
            filters.append(":".join(parts))

        # Detail line 1: club · school – matches image ~y=805 (h-275)
        detail1_parts = []
        if p["club_team"]:
            detail1_parts.append(p["club_team"])
        if p["high_school"]:
            detail1_parts.append(p["high_school"])
        if detail1_parts:
            safe_d1 = escape_drawtext("  ·  ".join(detail1_parts))
            parts = [
                f"drawtext=text='{safe_d1}'",
                f"fontsize=22",
                f"fontcolor=#a09b91",
                f"x=120",
                f"y=h-275",
                f"box=1",
                f"boxcolor=black@0.4",
                f"boxborderw=6",
            ]
            if sfr:
                parts.insert(1, f"fontfile={sfr}")
            filters.append(":".join(parts))

        # Detail line 2: height/weight · gpa – matches image ~y=837 (h-243)
        detail2_parts = []
        if p["height_weight"]:
            detail2_parts.append(p["height_weight"])
        if p["gpa"]:
            detail2_parts.append(f"GPA {p['gpa']}")
        if detail2_parts:
            safe_d2 = escape_drawtext("  ·  ".join(detail2_parts))
            parts = [
                f"drawtext=text='{safe_d2}'",
                f"fontsize=22",
                f"fontcolor=#a09b91",
                f"x=120",
                f"y=h-243",
                f"box=1",
                f"boxcolor=black@0.4",
                f"boxborderw=6",
            ]
            if sfr:
                parts.insert(1, f"fontfile={sfr}")
            filters.append(":".join(parts))

        # Detail line 3: email · phone – matches image ~y=869 (h-211)
        detail3_parts = []
        if p["email"]:
            detail3_parts.append(p["email"].lower())
        if p["phone"]:
            detail3_parts.append(p["phone"])
        if detail3_parts:
            safe_d3 = escape_drawtext("  ·  ".join(detail3_parts))
            parts = [
                f"drawtext=text='{safe_d3}'",
                f"fontsize=22",
                f"fontcolor=#a09b91",
                f"x=120",
                f"y=h-211",
                f"box=1",
                f"boxcolor=black@0.4",
                f"boxborderw=6",
            ]
            if sfr:
                parts.insert(1, f"fontfile={sfr}")
            filters.append(":".join(parts))

        return ",".join(filters)
