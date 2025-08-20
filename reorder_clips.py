#!/usr/bin/env python3
# reorder_clips.py — GUI to reorder clips in project.json with playback preview
#
# Usage:
#   python reorder_clips.py
#   python reorder_clips.py --athlete "Jane Smith"
#   python reorder_clips.py --dir "athletes/Jane Smith"
#
# Requirements: tkinter (python3-tk), Pillow, OpenCV, ffmpeg (only for still-thumb fallback)

import argparse
import json
import pathlib
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
from typing import List, Tuple, Optional
from PIL import Image, ImageTk
import cv2
import math
import time

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

# ---------- still-frame fallback for files OpenCV can't decode ----------
def ffmpeg_first_frame(path: pathlib.Path, out_png: pathlib.Path) -> Optional[Image.Image]:
    try:
        cmd = [
            "ffmpeg","-y","-i",str(path),
            "-vf","select='gte(n,0)',setpts=N/FRAME_RATE/TB",
            "-vframes","1", str(out_png)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if out_png.exists():
            return Image.open(out_png)
    except Exception:
        return None
    return None

# ---------- player widget ----------
class VideoPlayer(tk.Frame):
    def __init__(self, master, bg="#111"):
        super().__init__(master)
        self.configure(bg=bg)

        # UI
        self.display = tk.Label(self, bd=1, relief="sunken", bg=bg)
        self.display.grid(row=0, column=0, columnspan=6, sticky="nsew", padx=0, pady=(0,8))

        self.btn_play = tk.Button(self, text="Play", width=6, command=self.toggle_play)
        self.btn_stop = tk.Button(self, text="Stop", width=6, command=self.stop)
        self.btn_b5  = tk.Button(self, text="⏪ 5s", width=6, command=lambda: self.nudge(-5.0))
        self.btn_b05 = tk.Button(self, text="◀ 0.5s", width=6, command=lambda: self.nudge(-0.5))
        self.btn_f05 = tk.Button(self, text="0.5s ▶", width=6, command=lambda: self.nudge(+0.5))
        self.btn_f5  = tk.Button(self, text="5s ⏩", width=6, command=lambda: self.nudge(+5.0))

        self.btn_b5.grid(row=1, column=0, padx=2)
        self.btn_b05.grid(row=1, column=1, padx=2)
        self.btn_play.grid(row=1, column=2, padx=2)
        self.btn_stop.grid(row=1, column=3, padx=2)
        self.btn_f05.grid(row=1, column=4, padx=2)
        self.btn_f5.grid(row=1, column=5, padx=2)

        self.loop_var = tk.BooleanVar(value=True)
        self.chk_loop = tk.Checkbutton(self, text="Loop", variable=self.loop_var)
        self.chk_loop.grid(row=2, column=0, sticky="w", padx=2, pady=(6,0))

        self.lbl_time = tk.Label(self, text="00:00 / 00:00")
        self.lbl_time.grid(row=2, column=5, sticky="e", padx=2, pady=(6,0))

        self.scale = tk.Scale(self, from_=0, to=100, orient="horizontal", showvalue=False,
                              command=self.on_slider)
        self.scale.grid(row=3, column=0, columnspan=6, sticky="ew")

        # grid weights
        for c in range(6):
            self.columnconfigure(c, weight=1)
        self.rowconfigure(0, weight=1)

        # State
        self.cap = None
        self.path = None
        self.fps = 30.0
        self.total_frames = 0
        self.cur_frame = 0
        self.playing = False
        self._after_id = None
        self._tk_img = None
        self._last_tick = None

        # keyboard
        self.bind_all("<space>", lambda e: self.toggle_play())

    def open(self, path: pathlib.Path):
        self.stop()
        self.path = path
        self.cap = cv2.VideoCapture(str(path))
        ok = self.cap.isOpened()
        if not ok:
            # graceful message; caller may choose to show still frame instead
            raise RuntimeError(f"Could not open video: {path}")

        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        if self.fps <= 1e-3:
            self.fps = 30.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if self.total_frames <= 0:
            # Try estimating with duration if reported
            dur = self.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            self.total_frames = int(round((dur or 1) * self.fps))

        self.cur_frame = 0
        self.scale.configure(from_=0, to=max(0, self.total_frames-1))
        self.update_time_label()
        self._show_current_frame()

    def destroy(self):
        self.stop()
        if self.cap is not None:
            self.cap.release()
        super().destroy()

    # ----- playback control -----
    def toggle_play(self):
        if self.playing:
            self.pause()
        else:
            self.play()

    def play(self):
        if self.cap is None:
            return
        self.playing = True
        self.btn_play.configure(text="Pause")
        self._last_tick = time.time()
        self._schedule_next_frame()

    def pause(self):
        self.playing = False
        self.btn_play.configure(text="Play")
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

    def stop(self):
        self.pause()
        if self.cap is not None:
            self.cur_frame = 0
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self._show_current_frame()
            self.scale.set(0)

    def nudge(self, seconds: float):
        if self.cap is None:
            return
        delta = int(round(seconds * self.fps))
        self.cur_frame = max(0, min(self.total_frames-1, self.cur_frame + delta))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.cur_frame)
        self._show_current_frame()
        self.scale.set(self.cur_frame)

    def on_slider(self, value):
        if self.cap is None:
            return
        self.pause()  # pause while scrubbing
        f = int(value)
        self.cur_frame = max(0, min(self.total_frames-1, f))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.cur_frame)
        self._show_current_frame()

    # ----- frame/timer -----
    def _schedule_next_frame(self):
        if not self.playing or self.cap is None:
            return
        # compute delay based on fps
        delay_ms = max(1, int(round(1000.0 / self.fps)))
        self._after_id = self.after(delay_ms, self._tick)

    def _tick(self):
        if not self.playing or self.cap is None:
            return
        ok, frame = self.cap.read()
        if not ok:
            # reached end
            if self.loop_var.get():
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.cur_frame = 0
                self.scale.set(0)
                self._show_current_frame()
                self._schedule_next_frame()
            else:
                self.pause()
            return

        self.cur_frame = min(self.cur_frame + 1, self.total_frames-1)
        self._render(frame)
        self.scale.set(self.cur_frame)
        self.update_time_label()
        self._schedule_next_frame()

    def _show_current_frame(self):
        if self.cap is None:
            return
        ok, frame = self.cap.read()
        if not ok:
            return
        # when we read, the internal cursor advanced; step back one so current_frame stays consistent
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, self.cur_frame))
        self._render(frame)
        self.update_time_label()

    def _render(self, frame):
        # convert BGR->RGB and fit to display width while preserving aspect
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        im = Image.fromarray(frame)
        panel_w = max(400, self.display.winfo_width() or 640)
        panel_h = max(300, self.display.winfo_height() or 360)
        r = min(panel_w / im.width, panel_h / im.height)
        im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
        self._tk_img = ImageTk.PhotoImage(im)
        self.display.configure(image=self._tk_img)

    def update_time_label(self):
        cur_s = self.cur_frame / self.fps if self.fps > 0 else 0.0
        total_s = self.total_frames / self.fps if self.fps > 0 else 0.0
        def fmt(t):
            m, s = divmod(int(round(t)), 60)
            return f"{m:02d}:{s:02d}"
        self.lbl_time.configure(text=f"{fmt(cur_s)} / {fmt(total_s)}")

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

        # Player pane
        tk.Label(right, text="Preview:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.player = VideoPlayer(right)
        self.player.grid(row=1, column=0, sticky="nsew", pady=(4,0))

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
        # Try to open for playback
        try:
            self.player.open(path)
            self.player.play()
        except Exception:
            # If playback fails (codec), show a single still as fallback
            thumbs = self.base / "work" / "thumbs"
            thumbs.mkdir(parents=True, exist_ok=True)
            thumb_png = thumbs / (path.stem + ".png")
            im = ffmpeg_first_frame(path, thumb_png)
            if im is None:
                messagebox.showwarning("Preview", "Could not read a frame from this clip.")
                return
            self.player.pause()
            # Render still onto player display
            panel_w = max(400, self.player.display.winfo_width() or 640)
            panel_h = max(300, self.player.display.winfo_height() or 360)
            r = min(panel_w / im.width, panel_h / im.height)
            im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
            self.player._tk_img = ImageTk.PhotoImage(im)
            self.player.display.configure(image=self.player._tk_img)

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


