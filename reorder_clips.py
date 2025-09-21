#!/usr/bin/env python3
# reorder_clips.py — GUI to reorder clips in project.json with playback preview
#
# Usage:
#   python reorder_clips.py
#   python reorder_clips.py --athlete "Jane Smith"
#   python reorder_clips.py --dir "athletes/Jane Smith"
#
# Requirements: tkinter (python3-tk)

import argparse
import json
import os
import pathlib
import platform
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
from typing import List, Tuple, Optional

ROOT = pathlib.Path.cwd()
ATHLETES = ROOT / "athletes"

# ---------- athlete / project helpers ----------
def find_athletes() -> list[pathlib.Path]:
    if not ATHLETES.exists():
        return []
    return sorted([p for p in ATHLETES.iterdir() if p.is_dir()])

def choose_athlete_interactive() -> pathlib.Path | None:
    options = find_athletes()
    if not options:
        print("No athlete folders found under ./athletes/")
        return None
    print("\nSelect an athlete:")
    for i, p in enumerate(options, 1):
        print(f"  {i}. {p.name}")
    print("  q. Quit")
    while True:
        choice = input("Enter number: ").strip().lower()
        if choice in ("q","quit","exit"):
            return None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(options):
                return options[idx-1]
        print("Invalid choice. Try again.")

def load_project(base: pathlib.Path) -> dict:
    pj = base / "project.json"
    if not pj.exists():
        raise FileNotFoundError(f"{pj} not found. Run mark_play.py first.")
    return json.loads(pj.read_text())

def save_project(base: pathlib.Path, data: dict):
    pj = base / "project.json"
    pj.write_text(json.dumps(data, indent=2))
    return pj

# ---------- robust path resolution ----------
def resolve_video_path(base: pathlib.Path, clip_entry: dict) -> pathlib.Path | None:
    candidates = []
    for key in ("std_file", "file"):
        p = clip_entry.get(key)
        if p:
            candidates.append(pathlib.Path(p))

    more = []
    for key in ("file", "std_file"):
        p = clip_entry.get(key)
        if p:
            name = pathlib.Path(p).name
            more.extend([
                base / name,
                base / "work" / "proxies" / name,
                base / "clips_in" / name,
            ])
    candidates.extend(more)

    for cand in candidates:
        c = cand if cand.is_absolute() else (base / cand)
        if c.exists():
            return c
    return None


# ---------- preview area widget ----------
class PreviewArea(tk.Frame):
    def __init__(self, master, bg="#f0f0f0"):
        super().__init__(master)
        self.configure(bg=bg, bd=1, relief="sunken")

        # Simple message area
        self.label = tk.Label(self,
                             text="Click 'Preview' button to open selected clip\nin your system's default video player",
                             bg=bg,
                             fg="#666666",
                             font=("Arial", 12),
                             justify="center")
        self.label.pack(expand=True, fill="both", padx=20, pady=20)

        # Make the area expandable
        self.pack_propagate(False)

# ---------- drag-and-drop listbox ----------
class DragListbox(tk.Listbox):
    def __init__(self, master, **kw):
        super().__init__(master, selectmode=tk.SINGLE, activestyle="dotbox", **kw)
        self.bind("<Button-1>", self.set_current)
        self.bind("<B1-Motion>", self.shift_selection)
        self.curIndex = None

    def set_current(self, event):
        self.curIndex = self.nearest(event.y)

    def shift_selection(self, event):
        i = self.nearest(event.y)
        if self.curIndex is None or i == self.curIndex:
            return
        item = self.get(self.curIndex)
        self.delete(self.curIndex)
        self.insert(i, item)
        self.selection_clear(0, tk.END)
        self.selection_set(i)
        self.curIndex = i

# ---------- main GUI ----------
class ReorderGUI(tk.Tk):
    def __init__(self, base_dir: pathlib.Path):
        super().__init__()
        self.title(f"Reorder Clips – {base_dir.name}")
        self.geometry("1000x650")
        self.minsize(860, 560)

        self.base = base_dir
        self.project = load_project(self.base)
        self.clips: List[dict] = list(self.project.get("clips", []))

        # layout
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = tk.Frame(self)
        left.grid(row=0, column=0, sticky="nsw", padx=10, pady=10)
        right = tk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        tk.Label(left, text="Clips (drag to reorder):", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.listbox = DragListbox(left, width=40, height=24)
        self.listbox.pack(fill="y", expand=False)

        for c in self.clips:
            name = pathlib.Path(c.get("file","") or c.get("std_file","")).name or "(unnamed)"
            self.listbox.insert(tk.END, name)

        btns = tk.Frame(left)
        btns.pack(fill="x", pady=(8,0))
        tk.Button(btns, text="▲ Up", command=self.move_up).grid(row=0, column=0, padx=2)
        tk.Button(btns, text="▼ Down", command=self.move_down).grid(row=0, column=1, padx=2)
        tk.Button(btns, text="Sort by Filename", command=self.sort_by_name).grid(row=0, column=2, padx=8)
        tk.Button(btns, text="Preview", command=self.preview_selected).grid(row=0, column=3, padx=2)
        tk.Button(btns, text="Save Order", command=self.save_order).grid(row=0, column=4, padx=12)
        tk.Button(btns, text="Close", command=self.destroy).grid(row=0, column=5, padx=2)

        # Preview pane
        tk.Label(right, text="Preview:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.preview_area = PreviewArea(right)
        self.preview_area.grid(row=1, column=0, sticky="nsew", pady=(4,0))

        # Double-click list item to preview
        self.listbox.bind("<Double-Button-1>", lambda e: self.preview_selected())

        # Shortcuts
        self.bind("<Control-Up>", lambda e: self.move_up())
        self.bind("<Control-Down>", lambda e: self.move_down())

    def current_selection(self) -> Optional[int]:
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def move_up(self):
        i = self.current_selection()
        if i is None or i == 0: return
        self.clips[i-1], self.clips[i] = self.clips[i], self.clips[i-1]
        txt = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(i-1, txt)
        self.listbox.selection_set(i-1)

    def move_down(self):
        i = self.current_selection()
        if i is None or i >= len(self.clips)-1: return
        self.clips[i+1], self.clips[i] = self.clips[i], self.clips[i+1]
        txt = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(i+1, txt)
        self.listbox.selection_set(i+1)

    def sort_by_name(self):
        pairs: List[Tuple[str, dict]] = []
        for c in self.clips:
            name = pathlib.Path(c.get("file","") or c.get("std_file","")).name
            pairs.append((name, c))
        pairs.sort(key=lambda x: x[0].lower())
        self.clips = [c for _, c in pairs]
        self.listbox.delete(0, tk.END)
        for name, _ in pairs:
            self.listbox.insert(tk.END, name)

    def preview_selected(self):
        i = self.current_selection()
        if i is None: return
        path = resolve_video_path(self.base, self.clips[i])
        if not path:
            messagebox.showwarning("Preview", "Could not locate file or proxy for this clip.")
            return

        # Open video in system default player
        try:
            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", str(path)], check=True)
            elif system == "Windows":
                os.startfile(str(path))
            else:  # Linux and others
                subprocess.run(["xdg-open", str(path)], check=True)
        except Exception as e:
            messagebox.showerror("Preview Error", f"Could not open video in system player:\n{e}")

    def save_order(self):
        self.project["clips"] = self.clips
        pj = save_project(self.base, self.project)
        messagebox.showinfo("Saved", f"Order saved to:\n{pj}\n\nNow run render_highlight.py.")

def main():
    ap = argparse.ArgumentParser(description="GUI to reorder clips with playback preview")
    ap.add_argument("--athlete", type=str, help="Athlete folder name under ./athletes")
    ap.add_argument("--dir", type=str, help="Full path to athlete folder")
    args = ap.parse_args()

    if args.dir:
        base = pathlib.Path(args.dir).resolve()
    elif args.athlete:
        base = (ATHLETES / args.athlete).resolve()
    else:
        base = choose_athlete_interactive()
        if base is None:
            sys.exit(0)

    if not base.exists() or not base.is_dir():
        print(f"Invalid athlete directory: {base}")
        sys.exit(1)

    try:
        app = ReorderGUI(base)
        app.mainloop()
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    main()


