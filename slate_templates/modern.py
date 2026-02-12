# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Modern slate template.

Dark gradient (#1a1a2e → #16213e), 8px gold accent stripe on left,
circular photo crop, clean two-column stats, accent-colored pill badge
for position.
"""

from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw

from .base import SlateTemplate, load_font, escape_drawtext, extract_player_fields


class ModernTemplate(SlateTemplate):
    name = "modern"
    display_name = "Modern"
    description = "Dark gradient, gold accent stripe, circular photo crop"

    _BG_TOP = (26, 26, 46)       # #1a1a2e
    _BG_BOTTOM = (22, 33, 62)    # #16213e
    _ACCENT = (218, 165, 32)     # gold
    _TEXT_PRIMARY = (255, 255, 255)
    _TEXT_SECONDARY = (180, 180, 200)

    # ── helpers ────────────────────────────────────────────────────

    @staticmethod
    def _gradient(w: int, h: int, top: tuple, bottom: tuple) -> Image.Image:
        img = Image.new("RGB", (w, h))
        draw = ImageDraw.Draw(img)
        for y in range(h):
            t = y / max(h - 1, 1)
            r = int(top[0] + (bottom[0] - top[0]) * t)
            g = int(top[1] + (bottom[1] - top[1]) * t)
            b = int(top[2] + (bottom[2] - top[2]) * t)
            draw.line([(0, y), (w, y)], fill=(r, g, b))
        return img

    @staticmethod
    def _circular_crop(photo: Image.Image, diameter: int) -> Image.Image:
        # Crop to square first (center-x, top-biased-y) to avoid stretching
        w, h = photo.size
        side = min(w, h)
        left = (w - side) // 2
        top = min(h - side, h // 4)  # bias toward top to keep head
        photo = photo.crop((left, top, left + side, top + side))
        photo = photo.resize((diameter, diameter), Image.LANCZOS)
        mask = Image.new("L", (diameter, diameter), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, diameter, diameter), fill=255)
        out = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
        out.paste(photo.convert("RGBA"), (0, 0))
        out.putalpha(mask)
        return out

    # ── image slate ────────────────────────────────────────────────

    def render_image_slate(self, player: dict, intro_image: pathlib.Path | None) -> Image.Image:
        W, H = 1920, 1080
        img = self._gradient(W, H, self._BG_TOP, self._BG_BOTTOM)
        draw = ImageDraw.Draw(img)

        p = extract_player_fields(player)

        # Gold accent stripe (left edge)
        draw.rectangle([(0, 0), (8, H)], fill=self._ACCENT)

        name_font = load_font(56, bold=True)
        label_font = load_font(22)
        data_font = load_font(32)
        pos_font = load_font(26, bold=True)

        photo_diameter = 300
        photo_loaded = False

        if intro_image:
            try:
                raw = Image.open(intro_image).convert("RGBA")
                circle = self._circular_crop(raw, photo_diameter)

                # Gold ring around photo
                ring = Image.new("RGBA", (photo_diameter + 8, photo_diameter + 8), (0, 0, 0, 0))
                ring_draw = ImageDraw.Draw(ring)
                ring_draw.ellipse((0, 0, photo_diameter + 7, photo_diameter + 7), fill=self._ACCENT)
                ring_draw.ellipse((4, 4, photo_diameter + 3, photo_diameter + 3), fill=(0, 0, 0, 0))
                ring.paste(circle, (4, 4), circle)

                px = 120
                py = (H - photo_diameter - 8) // 2

                img_rgba = img.convert("RGBA")
                img_rgba.paste(ring, (px, py), ring)
                img = img_rgba.convert("RGB")
                draw = ImageDraw.Draw(img)
                photo_loaded = True
            except Exception as e:
                print(f"Warning: Could not load picture {intro_image}: {e}")

        # Text layout
        if photo_loaded:
            text_x = 120 + photo_diameter + 80
            text_w = W - text_x - 120
        else:
            text_x = 120
            text_w = W - 240

        # Title (if set)
        name_y = 180
        if p["title"]:
            title_font = load_font(36, bold=True)
            draw.text((text_x, 140), p["title"], fill=self._ACCENT, font=title_font)
            name_y = 190

        # Name
        draw.text((text_x, name_y), p["name"], fill=self._TEXT_PRIMARY, font=name_font)

        # Position pill badge
        if p["position"]:
            badge_text = p["position"].upper()
            badge_font = pos_font
            bb = draw.textbbox((0, 0), badge_text, font=badge_font)
            bw, bh = bb[2] - bb[0], bb[3] - bb[1]
            badge_x = text_x
            badge_y = 260
            draw.rounded_rectangle(
                [(badge_x, badge_y), (badge_x + bw + 30, badge_y + bh + 14)],
                radius=12, fill=self._ACCENT,
            )
            draw.text((badge_x + 15, badge_y + 7), badge_text, fill=(0, 0, 0), font=badge_font)

        # Stats in two-column grid
        stats = []
        if p["grad_year"]:
            stats.append(("GRAD YEAR", p["grad_year"]))
        if p["club_team"]:
            stats.append(("CLUB", p["club_team"]))
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

        col_w = text_w // 2
        start_y = 340
        row_h = 90

        for i, (label, value) in enumerate(stats):
            col = i % 2
            row = i // 2
            x = text_x + col * col_w
            y = start_y + row * row_h
            draw.text((x, y), label, fill=self._TEXT_SECONDARY, font=label_font)
            draw.text((x, y + 30), value, fill=self._TEXT_PRIMARY, font=data_font)

        return img

    # ── video drawtext ─────────────────────────────────────────────

    def get_video_drawtext_filters(self, player: dict, font_bold: str, font_regular: str) -> str:
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
                f"fontsize=36",
                f"fontcolor=#daa520",
                f"x=80",
                f"y=h*0.64",
                f"box=1",
                f"boxcolor=black@0.6",
                f"boxborderw=8",
            ]
            if sfb:
                parts.insert(1, f"fontfile={sfb}")
            filters.append(":".join(parts))

        # Name – bottom left with accent-colored underline effect via box
        parts = [
            f"drawtext=text='{safe_name}'",
            f"fontsize=64",
            f"fontcolor=white",
            f"x=80",
            f"y=h*0.72",
            f"box=1",
            f"boxcolor=black@0.6",
            f"boxborderw=12",
        ]
        if sfb:
            parts.insert(1, f"fontfile={sfb}")
        filters.append(":".join(parts))

        # Position badge
        if p["position"]:
            safe_pos = escape_drawtext(p["position"].upper())
            parts = [
                f"drawtext=text='{safe_pos}'",
                f"fontsize=32",
                f"fontcolor=#1a1a2e",
                f"x=80",
                f"y=h*0.82",
                f"box=1",
                f"boxcolor=#daa520",
                f"boxborderw=10",
            ]
            if sfb:
                parts.insert(1, f"fontfile={sfb}")
            filters.append(":".join(parts))

        # Grad year
        if p["grad_year"]:
            safe_grad = escape_drawtext(f"Class of {p['grad_year']}")
            parts = [
                f"drawtext=text='{safe_grad}'",
                f"fontsize=36",
                f"fontcolor=white",
                f"x=80+text_w+40" if p["position"] else f"x=80",
                f"y=h*0.82",
                f"box=1",
                f"boxcolor=black@0.5",
                f"boxborderw=8",
            ]
            if sfr:
                parts.insert(1, f"fontfile={sfr}")
            filters.append(":".join(parts))

        return ",".join(filters)
