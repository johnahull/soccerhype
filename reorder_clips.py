#!/usr/bin/env python3
# reorder_clips.py — GUI to reorder clips in project.json with system player preview
#
# Usage:
#   python reorder_clips.py
#   python reorder_clips.py --athlete "Jane Smith"
#   python reorder_clips.py --dir "athletes/Jane Smith"
#
# Note: Preview functionality uses system default video player for reliability.
# Trade-offs vs embedded player: No scrubbing/looping, but better codec support.
#
# Requirements: tkinter (python3-tk)

import argparse
import json
import os
import pathlib
import platform
import shutil
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

        # Message and status area
        self.label = tk.Label(self,
                             text="Select a clip and click 'Preview' to open in system player",
                             bg=bg,
                             fg="#666666",
                             font=("Arial", 12),
                             justify="center",
                             wraplength=400)
        self.label.pack(expand=True, fill="both", padx=20, pady=20)

        # Make the area expandable
        self.pack_propagate(False)

    def show_clip_info(self, clip_name: str, file_path: pathlib.Path):
        """Display information about the selected clip"""
        try:
            info_text = f"Selected: {clip_name}\n\n"
            info_text += f"File: {file_path.name}\n"

            # Only get file size if it's a local file (not network drive)
            # and use non-blocking approach
            try:
                if file_path.exists() and file_path.is_file():
                    # Quick check - only for reasonably accessible files
                    file_size = file_path.stat().st_size
                    size_mb = file_size / (1024 * 1024)
                    info_text += f"Size: {size_mb:.1f} MB\n\n"
                else:
                    info_text += "Size: Unknown\n\n"
            except (OSError, PermissionError):
                # Network drives or permission issues - skip size
                info_text += "Size: Unknown\n\n"

            info_text += "Click 'Preview' to open in system player"
            self.label.configure(text=info_text)
        except Exception:
            self.label.configure(text=f"Selected: {clip_name}\n\nClick 'Preview' to open in system player")

    def show_status(self, message: str):
        """Show a status message"""
        self.label.configure(text=message)

    def reset(self):
        """Reset to default message"""
        self.label.configure(text="Select a clip and click 'Preview' to open in system player")

# ---------- drag-and-drop listbox ----------
class DragListbox(tk.Listbox):
    def __init__(self, master, on_reorder=None, **kw):
        super().__init__(master, selectmode=tk.SINGLE, activestyle="dotbox", **kw)
        self.bind("<Button-1>", self.set_current)
        self.bind("<B1-Motion>", self.shift_selection)
        self.curIndex = None
        self.on_reorder = on_reorder  # Callback when items are reordered

    def set_current(self, event):
        self.curIndex = self.nearest(event.y)

    def shift_selection(self, event):
        i = self.nearest(event.y)
        if self.curIndex is None or i == self.curIndex:
            return
        old_index = self.curIndex
        item = self.get(self.curIndex)
        self.delete(self.curIndex)
        self.insert(i, item)
        self.selection_clear(0, tk.END)
        self.selection_set(i)
        self.curIndex = i
        # Notify parent about reordering
        if self.on_reorder:
            self.on_reorder(old_index, i)
        # Trigger selection change event to update internal state
        self.event_generate("<<ListboxSelect>>")

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
        self.is_modified = False  # Track unsaved changes

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
        self.listbox = DragListbox(left, on_reorder=self.handle_drag_reorder, width=40, height=24)
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
        remove_btn = tk.Button(btns, text="Remove", command=self.remove_selected, fg="red")
        remove_btn.grid(row=0, column=4, padx=2)
        tk.Button(btns, text="Save Order", command=self.save_order).grid(row=0, column=5, padx=12)
        tk.Button(btns, text="Close", command=self.on_closing).grid(row=0, column=6, padx=2)

        # Preview pane
        tk.Label(right, text="Preview:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.preview_area = PreviewArea(right)
        self.preview_area.grid(row=1, column=0, sticky="nsew", pady=(4,0))

        # Double-click list item to preview
        self.listbox.bind("<Double-Button-1>", lambda e: self.preview_selected())
        # Show clip info when selection changes
        self.listbox.bind("<<ListboxSelect>>", self.on_selection_change)

        # Shortcuts
        self.bind("<Control-Up>", lambda e: self.move_up())
        self.bind("<Control-Down>", lambda e: self.move_down())
        self.bind("<Delete>", lambda e: self.remove_selected())
        self.bind("<BackSpace>", lambda e: self.remove_selected())  # macOS compatibility

        # Handle window close to warn about unsaved changes
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def current_selection(self) -> Optional[int]:
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def handle_drag_reorder(self, old_index: int, new_index: int):
        """Handle reordering of clips data when listbox items are dragged"""
        if old_index == new_index:
            return

        # Validate indices are within range to prevent IndexError
        if not (0 <= old_index < len(self.clips) and 0 <= new_index < len(self.clips)):
            return

        try:
            # Move the clip in the data list to match the listbox
            clip = self.clips.pop(old_index)
            self.clips.insert(new_index, clip)
            self.is_modified = True
            self.update_title()
        except (IndexError, ValueError):
            # Handle edge cases during rapid drag operations
            pass

    def on_selection_change(self, event=None):
        """Handle listbox selection change to show clip info"""
        i = self.current_selection()
        if i is None:
            self.preview_area.reset()
            return

        try:
            # Validate bounds to prevent IndexError
            if i >= len(self.clips):
                self.preview_area.reset()
                return

            clip_name = self.listbox.get(i)
            path = resolve_video_path(self.base, self.clips[i])
            if path and path.exists():
                self.preview_area.show_clip_info(clip_name, path)
            else:
                self.preview_area.show_status(f"Selected: {clip_name}\n\n⚠️ File not found")
        except Exception:
            self.preview_area.reset()

    def move_up(self):
        i = self.current_selection()
        if i is None or i == 0: return
        self.clips[i-1], self.clips[i] = self.clips[i], self.clips[i-1]
        txt = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(i-1, txt)
        self.listbox.selection_set(i-1)
        self.is_modified = True
        self.update_title()

    def move_down(self):
        i = self.current_selection()
        if i is None or i >= len(self.clips)-1: return
        self.clips[i+1], self.clips[i] = self.clips[i], self.clips[i+1]
        txt = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(i+1, txt)
        self.listbox.selection_set(i+1)
        self.is_modified = True
        self.update_title()

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
        self.is_modified = True
        self.update_title()

    def remove_selected(self):
        """Remove selected clip from the list with confirmation"""
        i = self.current_selection()
        if i is None:
            messagebox.showwarning("No Selection", "Please select a clip to remove.")
            return

        # Validate bounds to prevent IndexError
        if i >= len(self.clips):
            messagebox.showerror("Selection Error", "Selected item is out of range.")
            return

        clip_name = self.listbox.get(i)

        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Removal",
            f"Remove clip from list?\n\n{clip_name}\n\n"
            "This will remove it from the project (when you click 'Save Order').\n"
            "The original video file will not be deleted.",
            icon='warning'
        )

        if not result:
            return

        # Remove from data and UI
        del self.clips[i]
        self.listbox.delete(i)
        self.is_modified = True
        self.update_title()

        # Update selection to next item (or previous if last item was removed)
        if len(self.clips) > 0:
            new_index = min(i, len(self.clips) - 1)
            self.listbox.selection_set(new_index)
            self.listbox.activate(new_index)
            self.on_selection_change()
        else:
            # No clips left
            self.preview_area.show_status("No clips remaining\n\nClick 'Close' or add more clips to mark_play.py")

    def preview_selected(self):
        """Open selected clip in system default video player with comprehensive error handling"""
        i = self.current_selection()
        if i is None:
            messagebox.showwarning("No Selection", "Please select a clip to preview.")
            return

        # Validate bounds to prevent IndexError
        if i >= len(self.clips):
            messagebox.showerror("Selection Error", "Selected item is out of range. Please refresh and try again.")
            return

        # Get and validate the file path
        path = resolve_video_path(self.base, self.clips[i])
        if not path:
            messagebox.showwarning("File Not Found",
                                 "Could not locate file or proxy for this clip.\n\n"
                                 "Possible solutions:\n"
                                 "• Check if the source file exists in clips_in/\n"
                                 "• Run render_highlight.py to generate proxies")
            return

        if not path.exists():
            messagebox.showerror("File Missing",
                               f"File does not exist:\n{path}\n\n"
                               "The file may have been moved or deleted.")
            return

        # Show status while launching
        clip_name = self.listbox.get(i)
        self.preview_area.show_status(f"Opening {clip_name}...")
        self.update_idletasks()  # Refresh UI without blocking

        # Additional security: validate path is safe
        try:
            # Resolve path to prevent directory traversal attacks
            resolved_path = path.resolve()
            # Ensure path is within expected directories (athletes folder or work folder)
            if not (str(resolved_path).startswith(str(self.base.resolve())) or
                   str(resolved_path).startswith(str((self.base / "work").resolve()))):
                messagebox.showerror("Security Error", "File path is outside allowed directories.")
                return
        except (OSError, ValueError) as e:
            messagebox.showerror("Path Error", f"Invalid file path: {e}")
            return

        # Launch system player with proper error handling and security
        try:
            system = platform.system()
            success = False
            safe_path = str(resolved_path)  # Use resolved path

            if system == "Darwin":  # macOS
                if shutil.which("open"):
                    subprocess.run(["open", safe_path], check=True, shell=False, timeout=10)
                    success = True
                else:
                    raise FileNotFoundError("'open' command not available")

            elif system == "Windows":
                # os.startfile is Windows-specific and secure
                os.startfile(safe_path)
                success = True

            else:  # Linux and others
                if shutil.which("xdg-open"):
                    subprocess.run(["xdg-open", safe_path], check=True, shell=False, timeout=10)
                    success = True
                else:
                    raise FileNotFoundError("'xdg-open' command not available")

            if success:
                # Show success status briefly, then restore clip info
                self.preview_area.show_status(f"✓ Opened {clip_name} in system player")

                # Safe callback that checks if window still exists
                def restore_clip_info():
                    try:
                        if self.winfo_exists():
                            self.preview_area.show_clip_info(clip_name, path)
                    except tk.TclError:
                        pass  # Window was destroyed

                def restore_focus():
                    try:
                        if self.winfo_exists():
                            self.lift()
                            self.focus_set()  # Less aggressive than focus_force()
                    except tk.TclError:
                        pass  # Window was destroyed

                self.after(2000, restore_clip_info)
                self.after(1000, restore_focus)

        except subprocess.TimeoutExpired:
            messagebox.showerror("Preview Timeout",
                               "System player took too long to start.\n\n"
                               "The file may be corrupted or the system is busy.")
            self.preview_area.show_clip_info(clip_name, path)

        except subprocess.CalledProcessError as e:
            messagebox.showerror("System Player Error",
                               f"System player failed to open the file.\n\n"
                               f"Exit code: {e.returncode}\n\n"
                               "Possible solutions:\n"
                               "• Install a compatible video player\n"
                               "• Check file format compatibility\n"
                               "• Try opening the file manually")
            self.preview_area.show_clip_info(clip_name, path)

        except FileNotFoundError as e:
            messagebox.showerror("System Command Missing",
                               f"Required system command not found: {e}\n\n"
                               "Please install appropriate system tools or try opening the file manually:\n"
                               f"{path}")
            self.preview_area.show_clip_info(clip_name, path)

        except Exception as e:
            messagebox.showerror("Unexpected Error",
                               f"An unexpected error occurred:\n{e}\n\n"
                               "Try opening the file manually:\n"
                               f"{path}")
            self.preview_area.show_clip_info(clip_name, path)

    def save_order(self):
        self.project["clips"] = self.clips
        pj = save_project(self.base, self.project)
        self.is_modified = False
        self.update_title()
        messagebox.showinfo("Saved", f"Order saved to:\n{pj}\n\nNow run render_highlight.py.")

    def update_title(self):
        """Update window title to reflect unsaved changes"""
        title = f"Reorder Clips – {self.base.name}"
        if self.is_modified:
            title += " *"
        self.title(title)

    def on_closing(self):
        """Handle window close event with unsaved changes warning"""
        if self.is_modified:
            result = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes.\n\n"
                "Do you want to save before closing?",
                icon='warning'
            )
            if result is None:  # Cancel
                return
            elif result:  # Yes, save
                self.save_order()
        self.destroy()

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


