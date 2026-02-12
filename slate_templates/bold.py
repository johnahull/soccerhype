# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Bold slate template.

Huge centered name, photo as darkened full-bleed background,
minimal info footer.  No photo → charcoal background.
"""

from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from .base import SlateTemplate, load_font, escape_drawtext, extract_player_fields


class BoldTemplate(SlateTemplate):
    name = "bold"
    display_name = "Bold"
    description = "Huge centered name, full-bleed photo bg, minimal info"

    _CHARCOAL = (45, 45, 48)
    _GOLD = (218, 165, 32)

    # ── image slate ────────────────────────────────────────────────

    def render_image_slate(self, player: dict, intro_image: pathlib.Path | None) -> Image.Image:
        W, H = 1920, 1080
        p = extract_player_fields(player)

        if intro_image:
            try:
                bg = Image.open(intro_image).convert("RGB")
                # Scale to cover 1920x1080
                bg_w, bg_h = bg.size
                scale = max(W / bg_w, H / bg_h)
                bg = bg.resize((int(bg_w * scale), int(bg_h * scale)), Image.LANCZOS)
                # Top-anchored crop — keep head visible
                cx = bg.size[0] // 2
                bg = bg.crop((cx - W // 2, 0, cx + W // 2, H))
                # Darken: 50% black overlay
                bg = ImageEnhance.Brightness(bg).enhance(0.5)
                # Slight blur for depth
                bg = bg.filter(ImageFilter.GaussianBlur(radius=3))
                img = bg
            except Exception as e:
                print(f"Warning: Could not load picture {intro_image}: {e}")
                img = Image.new("RGB", (W, H), self._CHARCOAL)
        else:
            img = Image.new("RGB", (W, H), self._CHARCOAL)

        draw = ImageDraw.Draw(img)

        # Title above name (if set)
        center_y = H // 2 - 100
        if p["title"]:
            title_font = load_font(44, bold=True)
            tb = draw.textbbox((0, 0), p["title"].upper(), font=title_font)
            tw = tb[2] - tb[0]
            draw.text(((W - tw) // 2, center_y - 70), p["title"].upper(),
                      fill=self._GOLD, font=title_font)

        # Massive centred name
        name_font = load_font(96, bold=True)
        name_text = p["name"].upper()
        bb = draw.textbbox((0, 0), name_text, font=name_font)
        nw = bb[2] - bb[0]
        draw.text(((W - nw) // 2, center_y), name_text, fill=(255, 255, 255), font=name_font)

        # Position in gold below name
        pos_bottom_y = center_y + 130
        if p["position"]:
            pos_font = load_font(48, bold=True)
            pos_text = p["position"].upper()
            bb = draw.textbbox((0, 0), pos_text, font=pos_font)
            pw = bb[2] - bb[0]
            draw.text(((W - pw) // 2, pos_bottom_y), pos_text, fill=self._GOLD, font=pos_font)
            pos_bottom_y += 60

        # Footer line 1: grad year · club · high school
        footer_font = load_font(28)
        line1_parts = []
        if p["grad_year"]:
            line1_parts.append(f"Class of {p['grad_year']}")
        if p["club_team"]:
            line1_parts.append(p["club_team"])
        if p["high_school"]:
            line1_parts.append(p["high_school"])

        # Footer line 2: height/weight · gpa · email · phone
        line2_parts = []
        if p["height_weight"]:
            line2_parts.append(p["height_weight"])
        if p["gpa"]:
            line2_parts.append(f"GPA {p['gpa']}")
        if p["email"]:
            line2_parts.append(p["email"].lower())
        if p["phone"]:
            line2_parts.append(p["phone"])

        footer_y = H - 80
        if line1_parts and line2_parts:
            footer_y = H - 120
        elif line1_parts or line2_parts:
            footer_y = H - 80

        if line1_parts:
            text = "  ·  ".join(line1_parts)
            bb = draw.textbbox((0, 0), text, font=footer_font)
            fw = bb[2] - bb[0]
            draw.text(((W - fw) // 2, footer_y), text, fill=(200, 200, 200), font=footer_font)
            footer_y += 40

        if line2_parts:
            text = "  ·  ".join(line2_parts)
            bb = draw.textbbox((0, 0), text, font=footer_font)
            fw = bb[2] - bb[0]
            draw.text(((W - fw) // 2, footer_y), text, fill=(170, 170, 170), font=footer_font)

        return img

    # ── video drawtext ─────────────────────────────────────────────

    def get_video_drawtext_filters(self, player: dict, font_bold: str, font_regular: str) -> str:
        p = extract_player_fields(player)
        safe_name = escape_drawtext(p["name"].upper())
        sfb = escape_drawtext(font_bold) if font_bold else ""
        sfr = escape_drawtext(font_regular) if font_regular else ""

        filters: list[str] = []

        # Title above name
        if p["title"]:
            safe_title = escape_drawtext(p["title"].upper())
            parts = [
                f"drawtext=text='{safe_title}'",
                f"fontsize=44",
                f"fontcolor=#daa520",
                f"x=(w-text_w)/2",
                f"y=(h-text_h)/2-120",
                f"box=1",
                f"boxcolor=black@0.5",
                f"boxborderw=10",
            ]
            if sfb:
                parts.insert(1, f"fontfile={sfb}")
            filters.append(":".join(parts))

        # Big centred name
        parts = [
            f"drawtext=text='{safe_name}'",
            f"fontsize=96",
            f"fontcolor=white",
            f"x=(w-text_w)/2",
            f"y=(h-text_h)/2-40",
            f"box=1",
            f"boxcolor=black@0.5",
            f"boxborderw=15",
        ]
        if sfb:
            parts.insert(1, f"fontfile={sfb}")
        filters.append(":".join(parts))

        # Position in gold
        if p["position"]:
            safe_pos = escape_drawtext(p["position"].upper())
            parts = [
                f"drawtext=text='{safe_pos}'",
                f"fontsize=48",
                f"fontcolor=#daa520",
                f"x=(w-text_w)/2",
                f"y=(h)/2+40",
                f"box=1",
                f"boxcolor=black@0.5",
                f"boxborderw=10",
            ]
            if sfb:
                parts.insert(1, f"fontfile={sfb}")
            filters.append(":".join(parts))

        # Footer line 1: grad year · club · high school
        line1_parts = []
        if p["grad_year"]:
            line1_parts.append(f"Class of {p['grad_year']}")
        if p["club_team"]:
            line1_parts.append(p["club_team"])
        if p["high_school"]:
            line1_parts.append(p["high_school"])
        if line1_parts:
            safe_line1 = escape_drawtext("  ·  ".join(line1_parts))
            parts = [
                f"drawtext=text='{safe_line1}'",
                f"fontsize=28",
                f"fontcolor=#cccccc",
                f"x=(w-text_w)/2",
                f"y=h-130",
                f"box=1",
                f"boxcolor=black@0.5",
                f"boxborderw=8",
            ]
            if sfr:
                parts.insert(1, f"fontfile={sfr}")
            filters.append(":".join(parts))

        # Footer line 2: height/weight · gpa · email · phone
        line2_parts = []
        if p["height_weight"]:
            line2_parts.append(p["height_weight"])
        if p["gpa"]:
            line2_parts.append(f"GPA {p['gpa']}")
        if p["email"]:
            line2_parts.append(p["email"].lower())
        if p["phone"]:
            line2_parts.append(p["phone"])
        if line2_parts:
            safe_line2 = escape_drawtext("  ·  ".join(line2_parts))
            parts = [
                f"drawtext=text='{safe_line2}'",
                f"fontsize=24",
                f"fontcolor=#aaaaaa",
                f"x=(w-text_w)/2",
                f"y=h-85",
                f"box=1",
                f"boxcolor=black@0.5",
                f"boxborderw=6",
            ]
            if sfr:
                parts.insert(1, f"fontfile={sfr}")
            filters.append(":".join(parts))

        return ",".join(filters)
