# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Tkinter dialog for choosing a slate template with visual previews."""

from __future__ import annotations

import pathlib
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from slate_templates import get_template, list_templates


class SlateTemplateChooser:
    """Modal dialog with thumbnail grid and large preview for selecting a slate template.

    Usage::

        result = SlateTemplateChooser.choose(parent, player_data, intro_image, current="classic")
        # result is a template name string, or None if cancelled
    """

    THUMB_W, THUMB_H = 150, 84
    PREVIEW_W, PREVIEW_H = 640, 360

    def __init__(self, parent: tk.Tk | tk.Toplevel, player: dict,
                 intro_image: pathlib.Path | None = None,
                 current: str | None = None):
        self.result: str | None = None
        self.player = player
        self.intro_image = intro_image
        self.selected: str = current or "classic"

        self.templates = list_templates()
        self._thumb_images: dict[str, ImageTk.PhotoImage] = {}
        self._full_images: dict[str, Image.Image] = {}

        # ── window ─────────────────────────────────────────────
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Choose Slate Template")
        self.dialog.geometry("820x560")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Centre on parent
        px = parent.winfo_rootx() + (parent.winfo_width() - 820) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - 560) // 2
        self.dialog.geometry(f"+{max(px, 0)}+{max(py, 0)}")

        self._build_ui()
        self._render_previews()
        self._select(self.selected)

        self.dialog.protocol("WM_DELETE_WINDOW", self._cancel)
        self.dialog.wait_window()

    # ── UI construction ────────────────────────────────────────

    def _build_ui(self):
        main = tk.Frame(self.dialog, padx=15, pady=10)
        main.pack(fill="both", expand=True)

        # Title
        tk.Label(main, text="Choose Slate Template",
                 font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))

        # ── thumbnail row ──────────────────────────────────────
        thumb_frame = tk.Frame(main)
        thumb_frame.pack(fill="x", pady=(0, 12))

        self._thumb_buttons: dict[str, tk.Label] = {}
        for tpl in self.templates:
            col = tk.Frame(thumb_frame)
            col.pack(side="left", expand=True, padx=4)

            lbl = tk.Label(col, relief="flat", bd=3, cursor="hand2")
            lbl.pack()
            lbl.bind("<Button-1>", lambda e, n=tpl.name: self._select(n))
            self._thumb_buttons[tpl.name] = lbl

            tk.Label(col, text=tpl.display_name,
                     font=("Segoe UI", 9)).pack(pady=(2, 0))

        # ── preview + info area ────────────────────────────────
        preview_row = tk.Frame(main)
        preview_row.pack(fill="both", expand=True)

        self._preview_label = tk.Label(preview_row, bg="#222222")
        self._preview_label.pack(side="left", padx=(0, 15))

        info_frame = tk.Frame(preview_row)
        info_frame.pack(side="left", fill="both", expand=True, anchor="n", pady=10)

        self._info_name = tk.Label(info_frame, text="",
                                   font=("Segoe UI", 13, "bold"), anchor="w")
        self._info_name.pack(fill="x", pady=(0, 6))

        self._info_desc = tk.Label(info_frame, text="", wraplength=200,
                                   font=("Segoe UI", 10), fg="#555",
                                   anchor="nw", justify="left")
        self._info_desc.pack(fill="x")

        # ── buttons ────────────────────────────────────────────
        btn_frame = tk.Frame(main)
        btn_frame.pack(fill="x", pady=(12, 0))

        tk.Button(btn_frame, text="Select", command=self._confirm,
                  bg="#007ACC", fg="white", font=("Segoe UI", 10, "bold"),
                  width=12).pack(side="right", padx=(8, 0))
        tk.Button(btn_frame, text="Cancel", command=self._cancel,
                  font=("Segoe UI", 10), width=10).pack(side="right")

    # ── preview rendering ──────────────────────────────────────

    def _render_previews(self):
        """Render full-size images and create thumbnail PhotoImages."""
        for tpl in self.templates:
            full = tpl.render_image_slate(self.player, self.intro_image)
            self._full_images[tpl.name] = full

            thumb = full.resize((self.THUMB_W, self.THUMB_H), Image.LANCZOS)
            photo = ImageTk.PhotoImage(thumb)
            self._thumb_images[tpl.name] = photo
            self._thumb_buttons[tpl.name].config(image=photo)

    # ── selection logic ────────────────────────────────────────

    def _select(self, name: str):
        self.selected = name

        # Highlight selected thumbnail border
        for tname, btn in self._thumb_buttons.items():
            if tname == name:
                btn.config(relief="solid", bd=3, highlightbackground="#007ACC",
                           highlightcolor="#007ACC", highlightthickness=3)
            else:
                btn.config(relief="flat", bd=3, highlightthickness=0)

        # Update large preview
        full = self._full_images.get(name)
        if full:
            preview = full.resize((self.PREVIEW_W, self.PREVIEW_H), Image.LANCZOS)
            self._preview_photo = ImageTk.PhotoImage(preview)
            self._preview_label.config(image=self._preview_photo)

        # Update info text
        tpl = get_template(name)
        self._info_name.config(text=tpl.display_name)
        self._info_desc.config(text=tpl.description)

    # ── dialog actions ─────────────────────────────────────────

    def _confirm(self):
        self.result = self.selected
        self.dialog.destroy()

    def _cancel(self):
        self.result = None
        self.dialog.destroy()

    # ── convenience class method ───────────────────────────────

    @classmethod
    def choose(cls, parent: tk.Tk | tk.Toplevel, player: dict,
               intro_image: pathlib.Path | None = None,
               current: str | None = None) -> str | None:
        """Show the chooser dialog and return selected template name, or None."""
        dlg = cls(parent, player, intro_image, current)
        return dlg.result
