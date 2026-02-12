# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Classic slate template – the original soccerhype design.

Black background, gray corner brackets, "PLAYER PROFILE" header,
gold labels, white data.  Photo left 33% / stats right 66%.
"""

from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw

from .base import SlateTemplate, load_font, escape_drawtext, extract_player_fields


class ClassicTemplate(SlateTemplate):
    name = "classic"
    display_name = "Classic"
    description = "Black bg, gold labels, corner brackets – the original design"

    # ── image-based slate ──────────────────────────────────────────

    def render_image_slate(self, player: dict, intro_image: pathlib.Path | None) -> Image.Image:
        W, H = 1920, 1080
        img = Image.new("RGB", (W, H), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        p = extract_player_fields(player)

        # Corner brackets
        bracket_color = (128, 128, 128)
        bracket_size = 60
        bracket_thickness = 4
        margin = 80

        # Top-left
        draw.line([(margin, margin), (margin + bracket_size, margin)], fill=bracket_color, width=bracket_thickness)
        draw.line([(margin, margin), (margin, margin + bracket_size)], fill=bracket_color, width=bracket_thickness)
        # Top-right
        draw.line([(W - margin - bracket_size, margin), (W - margin, margin)], fill=bracket_color, width=bracket_thickness)
        draw.line([(W - margin, margin), (W - margin, margin + bracket_size)], fill=bracket_color, width=bracket_thickness)
        # Bottom-left
        draw.line([(margin, H - margin - bracket_size), (margin, H - margin)], fill=bracket_color, width=bracket_thickness)
        draw.line([(margin, H - margin), (margin + bracket_size, H - margin)], fill=bracket_color, width=bracket_thickness)
        # Bottom-right
        draw.line([(W - margin, H - margin - bracket_size), (W - margin, H - margin)], fill=bracket_color, width=bracket_thickness)
        draw.line([(W - margin - bracket_size, H - margin), (W - margin, H - margin)], fill=bracket_color, width=bracket_thickness)

        # "PLAYER PROFILE" header
        header_font = load_font(48)
        header_text = "PLAYER PROFILE"
        header_bbox = draw.textbbox((0, 0), header_text, font=header_font)
        header_w = header_bbox[2] - header_bbox[0]
        header_x = int(W * 0.66 - header_w // 2)
        header_y = 120
        draw.text((header_x, header_y), header_text, fill=(255, 255, 255), font=header_font)

        # Colors and fonts
        label_color = (255, 215, 0)   # Gold
        data_color = (255, 255, 255)  # White
        label_font = load_font(24)
        data_font = load_font(36)
        name_font = load_font(52)
        title_font = load_font(72, bold=True)

        # Build stat rows
        stats_elements = []
        if p["position"]:
            stats_elements.append(("POSITION", p["position"].upper()))
        if p["height_weight"]:
            stats_elements.append(("HEIGHT | WEIGHT", p["height_weight"]))
        if p["grad_year"]:
            stats_elements.append(("GRADUATION YEAR", f"CLASS OF {p['grad_year']}"))
        if p["club_team"]:
            stats_elements.append(("CLUB", p["club_team"].upper()))
        if p["high_school"]:
            stats_elements.append(("HIGH SCHOOL", p["high_school"].upper()))
        if p["gpa"]:
            stats_elements.append(("GPA", str(p["gpa"])))
        if p["email"]:
            stats_elements.append(("EMAIL", p["email"].lower()))
        if p["phone"]:
            stats_elements.append(("PHONE", p["phone"]))

        # Load intro image if provided
        if intro_image:
            pic_area_w, pic_area_h = 450, 600
            pic_area_x = int(W * 0.33 - pic_area_w // 2)
            pic_area_y = 220

            try:
                player_pic = Image.open(intro_image).convert("RGBA")
                pic_w, pic_h = player_pic.size
                scale = min(pic_area_w / pic_w, pic_area_h / pic_h, 1.0)
                new_w, new_h = int(pic_w * scale), int(pic_h * scale)
                player_pic = player_pic.resize((new_w, new_h), Image.LANCZOS)

                # Rounded rectangle mask
                mask = Image.new("L", (new_w, new_h), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle([(0, 0), (new_w, new_h)], radius=20, fill=255)

                rounded_pic = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
                rounded_pic.paste(player_pic, (0, 0))
                rounded_pic.putalpha(mask)

                pic_x = pic_area_x + (pic_area_w - new_w) // 2
                pic_y = pic_area_y + (pic_area_h - new_h) // 2

                img_rgba = img.convert("RGBA")
                img_rgba.paste(rounded_pic, (pic_x, pic_y), rounded_pic)
                img = img_rgba.convert("RGB")
                draw = ImageDraw.Draw(img)
            except Exception as e:
                print(f"Warning: Could not load picture {intro_image}: {e}")
                intro_image = None

        if intro_image:
            # Title above name (if set), below picture, centered at 33%
            below_pic_y = pic_area_y + pic_area_h + 20
            if p["title"]:
                tb = draw.textbbox((0, 0), p["title"], font=title_font)
                tw = tb[2] - tb[0]
                draw.text((int(W * 0.33 - tw // 2), below_pic_y), p["title"],
                          fill=label_color, font=title_font)
                below_pic_y += 75

            name_bbox = draw.textbbox((0, 0), p["name"], font=name_font)
            name_w = name_bbox[2] - name_bbox[0]
            name_x = int(W * 0.33 - name_w // 2)
            name_y = below_pic_y
            draw.text((name_x, name_y), p["name"], fill=data_color, font=name_font)

            # Stats centered at 66%
            text_center_x = int(W * 0.66)
            line_spacing = 85
            total_height = len(stats_elements) * line_spacing - (line_spacing - 50) if stats_elements else 0
            current_y = (H - total_height) // 2

            for label, text in stats_elements:
                bbox = draw.textbbox((0, 0), label, font=label_font)
                lw = bbox[2] - bbox[0]
                draw.text((text_center_x - lw // 2, current_y), label, fill=label_color, font=label_font)
                bbox = draw.textbbox((0, 0), text, font=data_font)
                dw = bbox[2] - bbox[0]
                draw.text((text_center_x - dw // 2, current_y + 35), text, fill=data_color, font=data_font)
                current_y += line_spacing
        else:
            # No picture – everything centred
            below_header_y = header_y + 70
            if p["title"]:
                tb = draw.textbbox((0, 0), p["title"], font=title_font)
                tw = tb[2] - tb[0]
                draw.text(((W - tw) // 2, below_header_y), p["title"],
                          fill=label_color, font=title_font)
                below_header_y += 80

            name_bbox = draw.textbbox((0, 0), p["name"], font=name_font)
            name_w = name_bbox[2] - name_bbox[0]
            name_x = (W - name_w) // 2
            name_y = below_header_y
            draw.text((name_x, name_y), p["name"], fill=data_color, font=name_font)

            text_center_x = W // 2
            line_spacing = 95
            current_y = name_y + 100

            for label, text in stats_elements:
                bbox = draw.textbbox((0, 0), label, font=label_font)
                lw = bbox[2] - bbox[0]
                draw.text((text_center_x - lw // 2, current_y), label, fill=label_color, font=label_font)
                bbox = draw.textbbox((0, 0), text, font=data_font)
                dw = bbox[2] - bbox[0]
                draw.text((text_center_x - dw // 2, current_y + 35), text, fill=data_color, font=data_font)
                current_y += line_spacing

        return img

    # ── video-background slate (drawtext filters) ──────────────────

    def get_video_drawtext_filters(self, player: dict, font_bold: str, font_regular: str) -> str:
        p = extract_player_fields(player)
        safe_name = escape_drawtext(p["name"])
        safe_font_bold = escape_drawtext(font_bold) if font_bold else ""
        safe_font_regular = escape_drawtext(font_regular) if font_regular else ""

        filters: list[str] = []

        # Title (above name)
        if p["title"]:
            safe_title = escape_drawtext(p["title"])
            parts = [
                f"drawtext=text='{safe_title}'",
                f"fontsize=72",
                f"fontcolor=#ffd700",
                f"x=(w-text_w)/2",
                f"y=h*0.65",
                f"box=1",
                f"boxcolor=black@0.7",
                f"boxborderw=10",
            ]
            if safe_font_bold:
                parts.insert(1, f"fontfile={safe_font_bold}")
            filters.append(":".join(parts))

        # Main name
        parts = [
            f"drawtext=text='{safe_name}'",
            f"fontsize=64",
            f"fontcolor=white",
            f"x=(w-text_w)/2",
            f"y=h*0.75",
            f"box=1",
            f"boxcolor=black@0.7",
            f"boxborderw=10",
        ]
        if safe_font_bold:
            parts.insert(1, f"fontfile={safe_font_bold}")
        filters.append(":".join(parts))

        # Position + grad year
        if p["position"] or p["grad_year"]:
            pos_line = p["position"] + (f"  •  Class of {p['grad_year']}" if p["grad_year"] else "")
            safe_pos = escape_drawtext(pos_line)
            parts = [
                f"drawtext=text='{safe_pos}'",
                f"fontsize=40",
                f"fontcolor=white",
                f"x=(w-text_w)/2",
                f"y=h*0.82",
                f"box=1",
                f"boxcolor=black@0.7",
                f"boxborderw=8",
            ]
            if safe_font_regular:
                parts.insert(1, f"fontfile={safe_font_regular}")
            filters.append(":".join(parts))

        return ",".join(filters)
