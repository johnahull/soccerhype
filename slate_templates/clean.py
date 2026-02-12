# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Clean slate template.

Off-white (#f5f5f5) bg, dark text (#2c3e50), thin horizontal divider
at 35% height, name above divider, stats below in clean grid,
photo with thin border.  Video overlay uses white text for contrast.
"""

from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw

from .base import SlateTemplate, load_font, escape_drawtext, extract_player_fields


class CleanTemplate(SlateTemplate):
    name = "clean"
    display_name = "Clean"
    description = "Light bg, dark text, horizontal divider – professional look"

    _BG = (245, 245, 245)         # off-white
    _TEXT_DARK = (44, 62, 80)     # #2c3e50
    _TEXT_MID = (100, 100, 110)
    _DIVIDER = (180, 180, 185)
    _ACCENT = (41, 128, 185)      # steel blue
    _BORDER = (200, 200, 205)

    # ── image slate ────────────────────────────────────────────────

    def render_image_slate(self, player: dict, intro_image: pathlib.Path | None) -> Image.Image:
        W, H = 1920, 1080
        img = Image.new("RGB", (W, H), self._BG)
        draw = ImageDraw.Draw(img)

        p = extract_player_fields(player)

        divider_y = int(H * 0.35)

        name_font = load_font(60, bold=True)
        label_font = load_font(20)
        data_font = load_font(30)
        pos_font = load_font(32, bold=True)

        photo_loaded = False
        photo_right_edge = 0

        if intro_image:
            try:
                pic = Image.open(intro_image).convert("RGB")
                # Fit in box: max 320×320, positioned left of centre above divider
                max_dim = 280
                pw, ph = pic.size
                scale = min(max_dim / pw, max_dim / ph, 1.0)
                nw, nh = int(pw * scale), int(ph * scale)
                pic = pic.resize((nw, nh), Image.LANCZOS)

                # Thin border
                border = 3
                bx = 140
                by = (divider_y - nh - border * 2) // 2 + 20
                draw.rectangle(
                    [(bx, by), (bx + nw + border * 2, by + nh + border * 2)],
                    outline=self._BORDER, width=border,
                )
                img.paste(pic, (bx + border, by + border))
                photo_loaded = True
                photo_right_edge = bx + nw + border * 2 + 60
            except Exception as e:
                print(f"Warning: Could not load picture {intro_image}: {e}")

        # Text area (above divider)
        if photo_loaded:
            name_x = photo_right_edge
        else:
            name_x = 140

        # Title above name
        name_y = divider_y - 110
        if p["title"]:
            title_font = load_font(28)
            draw.text((name_x, name_y - 40), p["title"],
                       fill=self._TEXT_MID, font=title_font)

        draw.text((name_x, name_y), p["name"], fill=self._TEXT_DARK, font=name_font)

        # Position below name
        if p["position"]:
            draw.text((name_x, name_y + 70), p["position"].upper(), fill=self._ACCENT, font=pos_font)

        # Horizontal divider
        draw.line([(100, divider_y), (W - 100, divider_y)], fill=self._DIVIDER, width=2)

        # Stats grid below divider
        stats = []
        if p["grad_year"]:
            stats.append(("GRADUATION YEAR", f"Class of {p['grad_year']}"))
        if p["club_team"]:
            stats.append(("CLUB TEAM", p["club_team"]))
        if p["high_school"]:
            stats.append(("HIGH SCHOOL", p["high_school"]))
        if p["height_weight"]:
            stats.append(("HEIGHT / WEIGHT", p["height_weight"]))
        if p["gpa"]:
            stats.append(("GPA", str(p["gpa"])))
        if p["email"]:
            stats.append(("EMAIL", p["email"].lower()))
        if p["phone"]:
            stats.append(("PHONE", p["phone"]))

        grid_x = 140
        grid_y = divider_y + 50
        col_w = (W - 280) // 3
        row_h = 85

        for i, (label, value) in enumerate(stats):
            col = i % 3
            row = i // 3
            x = grid_x + col * col_w
            y = grid_y + row * row_h
            draw.text((x, y), label, fill=self._TEXT_MID, font=label_font)
            draw.text((x, y + 28), value, fill=self._TEXT_DARK, font=data_font)

        return img

    # ── video drawtext ─────────────────────────────────────────────

    def get_video_drawtext_filters(self, player: dict, font_bold: str, font_regular: str) -> str:
        """White text for contrast over video backgrounds."""
        p = extract_player_fields(player)
        safe_name = escape_drawtext(p["name"])
        sfb = escape_drawtext(font_bold) if font_bold else ""
        sfr = escape_drawtext(font_regular) if font_regular else ""

        filters: list[str] = []

        # Title (above name)
        if p["title"]:
            safe_title = escape_drawtext(p["title"])
            parts = [
                f"drawtext=text='{safe_title}'",
                f"fontsize=28",
                f"fontcolor=#cccccc",
                f"x=(w-text_w)/2",
                f"y=h*0.20",
                f"box=1",
                f"boxcolor=black@0.55",
                f"boxborderw=6",
            ]
            if sfr:
                parts.insert(1, f"fontfile={sfr}")
            filters.append(":".join(parts))

        # Name – centred upper third
        parts = [
            f"drawtext=text='{safe_name}'",
            f"fontsize=60",
            f"fontcolor=white",
            f"x=(w-text_w)/2",
            f"y=h*0.28",
            f"box=1",
            f"boxcolor=black@0.55",
            f"boxborderw=12",
        ]
        if sfb:
            parts.insert(1, f"fontfile={sfb}")
        filters.append(":".join(parts))

        # Position
        if p["position"]:
            safe_pos = escape_drawtext(p["position"].upper())
            parts = [
                f"drawtext=text='{safe_pos}'",
                f"fontsize=36",
                f"fontcolor=#2980b9",
                f"x=(w-text_w)/2",
                f"y=h*0.38",
                f"box=1",
                f"boxcolor=black@0.55",
                f"boxborderw=8",
            ]
            if sfb:
                parts.insert(1, f"fontfile={sfb}")
            filters.append(":".join(parts))

        # Stats line: grad year · club
        info_parts = []
        if p["grad_year"]:
            info_parts.append(f"Class of {p['grad_year']}")
        if p["club_team"]:
            info_parts.append(p["club_team"])
        if p["high_school"]:
            info_parts.append(p["high_school"])
        if info_parts:
            safe_info = escape_drawtext("  ·  ".join(info_parts))
            parts = [
                f"drawtext=text='{safe_info}'",
                f"fontsize=28",
                f"fontcolor=#eeeeee",
                f"x=(w-text_w)/2",
                f"y=h*0.80",
                f"box=1",
                f"boxcolor=black@0.55",
                f"boxborderw=8",
            ]
            if sfr:
                parts.insert(1, f"fontfile={sfr}")
            filters.append(":".join(parts))

        return ",".join(filters)
