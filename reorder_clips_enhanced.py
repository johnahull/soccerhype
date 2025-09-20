#!/usr/bin/env python3
"""
Enhanced Clip Reordering GUI
Advanced interface for reordering clips with improved video player,
thumbnail generation, and better user experience.
"""

import argparse
import json
import pathlib
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Tuple, Optional, Dict
from PIL import Image, ImageTk
import cv2
import threading
from enhanced_video_player import EnhancedVideoPlayer

ROOT = pathlib.Path.cwd()
ATHLETES = ROOT / "athletes"

class ThumbnailGenerator:
    """Generates and caches video thumbnails"""

    def __init__(self, cache_dir: pathlib.Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._thumbnail_cache = {}

    def get_thumbnail(self, video_path: pathlib.Path, size: Tuple[int, int] = (160, 90)) -> Optional[Image.Image]:
        """Get or generate thumbnail for video"""
        cache_key = f"{video_path.name}_{size[0]}x{size[1]}"

        if cache_key in self._thumbnail_cache:
            return self._thumbnail_cache[cache_key]

        # Check disk cache
        cache_file = self.cache_dir / f"{cache_key}.png"
        if cache_file.exists():
            try:
                thumbnail = Image.open(cache_file)
                self._thumbnail_cache[cache_key] = thumbnail
                return thumbnail
            except Exception:
                pass

        # Generate new thumbnail
        thumbnail = self._generate_thumbnail(video_path, size)
        if thumbnail:
            # Save to cache
            try:
                thumbnail.save(cache_file)
                self._thumbnail_cache[cache_key] = thumbnail
            except Exception:
                pass

        return thumbnail

    def _generate_thumbnail(self, video_path: pathlib.Path, size: Tuple[int, int]) -> Optional[Image.Image]:
        """Generate thumbnail from video"""
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return None

            # Seek to middle of video for better thumbnail
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if total_frames > 10:
                cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)

            ret, frame = cap.read()
            cap.release()

            if not ret:
                return None

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(frame_rgb)

            # Resize maintaining aspect ratio
            image.thumbnail(size, Image.Resampling.LANCZOS)

            return image

        except Exception:
            return None

class ClipListWidget(tk.Frame):
    """Enhanced clip list with thumbnails and drag-and-drop"""

    def __init__(self, master, clips: List[Dict], base_dir: pathlib.Path,
                 on_selection_change: Optional[callable] = None,
                 on_order_change: Optional[callable] = None):
        super().__init__(master)

        self.clips = clips.copy()
        self.base_dir = base_dir
        self.on_selection_change = on_selection_change
        self.on_order_change = on_order_change

        # Initialize thumbnail generator
        self.thumbnail_gen = ThumbnailGenerator(base_dir / "work" / "thumbnails")

        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        """Setup the clip list UI"""
        # Header
        header_frame = tk.Frame(self)
        header_frame.pack(fill='x', pady=(0, 5))

        tk.Label(header_frame, text="Clips (drag to reorder):",
                font=("Segoe UI", 10, "bold")).pack(side='left')

        # Action buttons
        btn_frame = tk.Frame(header_frame)
        btn_frame.pack(side='right')

        tk.Button(btn_frame, text="▲", width=3, command=self.move_up,
                 font=("Segoe UI", 8)).pack(side='left', padx=1)
        tk.Button(btn_frame, text="▼", width=3, command=self.move_down,
                 font=("Segoe UI", 8)).pack(side='left', padx=1)
        tk.Button(btn_frame, text="Sort A-Z", command=self.sort_alphabetically,
                 font=("Segoe UI", 8)).pack(side='left', padx=5)

        # Listbox with scrollbar
        list_frame = tk.Frame(self)
        list_frame.pack(fill='both', expand=True)

        # Create treeview for better display
        self.tree = ttk.Treeview(list_frame, columns=("duration", "size"), show='tree headings', height=20)
        self.tree.heading("#0", text="Clip", anchor='w')
        self.tree.heading("duration", text="Duration", anchor='center')
        self.tree.heading("size", text="Size", anchor='center')

        self.tree.column("#0", width=250, minwidth=200)
        self.tree.column("duration", width=80, minwidth=60)
        self.tree.column("size", width=80, minwidth=60)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Bind events
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<B1-Motion>", self.on_tree_drag)

        # Drag and drop state
        self.drag_item = None
        self.drag_start_y = 0

    def refresh_list(self):
        """Refresh the clip list display"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add clips
        for i, clip in enumerate(self.clips):
            clip_name = self.get_clip_name(clip)
            duration = self.get_clip_duration(clip)
            file_size = self.get_clip_size(clip)

            item_id = self.tree.insert("", 'end', text=f"{i+1:02d}. {clip_name}",
                                      values=(duration, file_size))

            # Load thumbnail asynchronously
            self.load_thumbnail_async(item_id, clip)

    def get_clip_name(self, clip: Dict) -> str:
        """Get display name for clip"""
        file_path = clip.get("file", "") or clip.get("std_file", "")
        return pathlib.Path(file_path).name if file_path else "Unknown"

    def get_clip_duration(self, clip: Dict) -> str:
        """Get clip duration string"""
        try:
            video_path = self.resolve_video_path(clip)
            if video_path and video_path.exists():
                cap = cv2.VideoCapture(str(video_path))
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS) or 30
                    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
                    duration = frame_count / fps if fps > 0 else 0
                    cap.release()

                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    return f"{minutes:02d}:{seconds:02d}"
        except Exception:
            pass
        return "??:??"

    def get_clip_size(self, clip: Dict) -> str:
        """Get clip file size string"""
        try:
            video_path = self.resolve_video_path(clip)
            if video_path and video_path.exists():
                size_bytes = video_path.stat().st_size
                if size_bytes < 1024 * 1024:
                    return f"{size_bytes // 1024}KB"
                else:
                    return f"{size_bytes // (1024 * 1024)}MB"
        except Exception:
            pass
        return "?MB"

    def resolve_video_path(self, clip: Dict) -> Optional[pathlib.Path]:
        """Resolve path to video file"""
        candidates = []
        for key in ("std_file", "file"):
            p = clip.get(key)
            if p:
                candidates.append(pathlib.Path(p))

        # Also try common locations
        for key in ("file", "std_file"):
            p = clip.get(key)
            if p:
                name = pathlib.Path(p).name
                candidates.extend([
                    self.base_dir / name,
                    self.base_dir / "work" / "proxies" / name,
                    self.base_dir / "clips_in" / name,
                ])

        for candidate in candidates:
            resolved = candidate if candidate.is_absolute() else (self.base_dir / candidate)
            if resolved.exists():
                return resolved

        return None

    def load_thumbnail_async(self, item_id: str, clip: Dict):
        """Load thumbnail for clip asynchronously"""
        def load_thumb():
            video_path = self.resolve_video_path(clip)
            if video_path:
                thumbnail = self.thumbnail_gen.get_thumbnail(video_path)
                if thumbnail:
                    # Convert to PhotoImage in main thread
                    self.after(0, lambda: self.set_thumbnail(item_id, thumbnail))

        threading.Thread(target=load_thumb, daemon=True).start()

    def set_thumbnail(self, item_id: str, thumbnail: Image.Image):
        """Set thumbnail for tree item (called from main thread)"""
        try:
            # Create a small thumbnail for the tree
            thumb_copy = thumbnail.copy()
            thumb_copy.thumbnail((32, 18), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(thumb_copy)

            # Store reference to prevent garbage collection
            if not hasattr(self, '_thumbnail_refs'):
                self._thumbnail_refs = {}
            self._thumbnail_refs[item_id] = photo

            # Update tree item with thumbnail
            self.tree.set(item_id, "#0", image=photo)

        except Exception as e:
            print(f"Error setting thumbnail: {e}")

    def on_tree_select(self, event):
        """Handle tree selection"""
        selection = self.tree.selection()
        if selection and self.on_selection_change:
            try:
                item = selection[0]
                index = self.tree.index(item)
                self.on_selection_change(index, self.clips[index])
            except (IndexError, tk.TclError):
                pass

    def on_tree_click(self, event):
        """Handle tree click for drag start"""
        item = self.tree.identify_row(event.y)
        if item:
            self.drag_item = item
            self.drag_start_y = event.y

    def on_tree_drag(self, event):
        """Handle tree drag for reordering"""
        if not self.drag_item:
            return

        # Find target item
        target = self.tree.identify_row(event.y)
        if target and target != self.drag_item:
            try:
                # Get indices
                drag_index = self.tree.index(self.drag_item)
                target_index = self.tree.index(target)

                # Reorder clips
                self.reorder_clips(drag_index, target_index)

                # Refresh display
                self.refresh_list()

                # Notify parent
                if self.on_order_change:
                    self.on_order_change(self.clips)

            except (IndexError, tk.TclError):
                pass

        self.drag_item = None

    def reorder_clips(self, from_index: int, to_index: int):
        """Reorder clips by moving item from one index to another"""
        if 0 <= from_index < len(self.clips) and 0 <= to_index < len(self.clips):
            clip = self.clips.pop(from_index)
            self.clips.insert(to_index, clip)

    def move_up(self):
        """Move selected item up"""
        selection = self.tree.selection()
        if selection:
            try:
                item = selection[0]
                index = self.tree.index(item)
                if index > 0:
                    self.reorder_clips(index, index - 1)
                    self.refresh_list()
                    if self.on_order_change:
                        self.on_order_change(self.clips)
            except (IndexError, tk.TclError):
                pass

    def move_down(self):
        """Move selected item down"""
        selection = self.tree.selection()
        if selection:
            try:
                item = selection[0]
                index = self.tree.index(item)
                if index < len(self.clips) - 1:
                    self.reorder_clips(index, index + 1)
                    self.refresh_list()
                    if self.on_order_change:
                        self.on_order_change(self.clips)
            except (IndexError, tk.TclError):
                pass

    def sort_alphabetically(self):
        """Sort clips alphabetically"""
        self.clips.sort(key=lambda clip: self.get_clip_name(clip).lower())
        self.refresh_list()
        if self.on_order_change:
            self.on_order_change(self.clips)

    def get_selected_index(self) -> Optional[int]:
        """Get index of selected clip"""
        selection = self.tree.selection()
        if selection:
            try:
                item = selection[0]
                return self.tree.index(item)
            except tk.TclError:
                pass
        return None

class EnhancedReorderGUI:
    """Enhanced reordering GUI with improved video player"""

    def __init__(self, base_dir: pathlib.Path):
        self.base_dir = base_dir
        self.project = self.load_project()
        self.clips = list(self.project.get("clips", []))

        self.setup_ui()

    def load_project(self) -> Dict:
        """Load project file"""
        project_file = self.base_dir / "project.json"
        if not project_file.exists():
            raise FileNotFoundError(f"{project_file} not found. Run mark_play.py first.")
        return json.loads(project_file.read_text())

    def save_project(self):
        """Save project file"""
        self.project["clips"] = self.clips
        project_file = self.base_dir / "project.json"
        project_file.write_text(json.dumps(self.project, indent=2))
        return project_file

    def setup_ui(self):
        """Setup the main UI"""
        self.root = tk.Tk()
        self.root.title(f"Enhanced Clip Reordering - {self.base_dir.name}")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)

        # Configure style
        style = ttk.Style()
        style.theme_use('clam')

        # Main paned window
        main_paned = ttk.PanedWindow(self.root, orient='horizontal')
        main_paned.pack(fill='both', expand=True, padx=5, pady=5)

        # Left panel - clip list
        left_frame = tk.Frame(main_paned, bg="#f0f0f0")
        main_paned.add(left_frame, minsize=350)

        self.clip_list = ClipListWidget(
            left_frame, self.clips, self.base_dir,
            on_selection_change=self.on_clip_selected,
            on_order_change=self.on_clips_reordered
        )
        self.clip_list.pack(fill='both', expand=True, padx=5, pady=5)

        # Right panel - video player
        right_frame = tk.Frame(main_paned, bg="#222")
        main_paned.add(right_frame, minsize=600)

        # Player header
        player_header = tk.Frame(right_frame, bg="#222")
        player_header.pack(fill='x', padx=5, pady=5)

        tk.Label(player_header, text="Preview Player", bg="#222", fg="white",
                font=("Segoe UI", 12, "bold")).pack(side='left')

        self.current_clip_label = tk.Label(player_header, text="No clip selected",
                                          bg="#222", fg="#aaa", font=("Segoe UI", 10))
        self.current_clip_label.pack(side='right')

        # Enhanced video player
        self.video_player = EnhancedVideoPlayer(
            right_frame, bg="#222",
            on_frame_change=self.on_frame_change
        )
        self.video_player.pack(fill='both', expand=True, padx=5, pady=5)

        # Bottom panel - action buttons
        button_frame = tk.Frame(self.root, bg="#f0f0f0")
        button_frame.pack(fill='x', padx=5, pady=5)

        tk.Button(button_frame, text="Save Order", command=self.save_order,
                 bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"),
                 padx=20).pack(side='left', padx=5)

        tk.Button(button_frame, text="Reset Order", command=self.reset_order,
                 font=("Segoe UI", 10), padx=20).pack(side='left', padx=5)

        tk.Button(button_frame, text="Preview Final Video", command=self.preview_final,
                 font=("Segoe UI", 10), padx=20).pack(side='left', padx=20)

        tk.Button(button_frame, text="Close", command=self.root.quit,
                 font=("Segoe UI", 10), padx=20).pack(side='right', padx=5)

        # Status bar
        self.status_var = tk.StringVar(value=f"Loaded {len(self.clips)} clips from {self.base_dir.name}")
        status_bar = tk.Label(self.root, textvariable=self.status_var,
                             relief='sunken', anchor='w', font=("Segoe UI", 9))
        status_bar.pack(fill='x', side='bottom')

    def on_clip_selected(self, index: int, clip: Dict):
        """Handle clip selection"""
        video_path = self.clip_list.resolve_video_path(clip)
        if video_path:
            clip_name = self.clip_list.get_clip_name(clip)
            self.current_clip_label.config(text=f"Playing: {clip_name}")

            if self.video_player.load_video(str(video_path)):
                self.status_var.set(f"Loaded clip {index + 1}: {clip_name}")
            else:
                self.status_var.set(f"Failed to load clip: {clip_name}")
        else:
            self.current_clip_label.config(text="Clip not found")
            self.status_var.set("Could not locate video file for selected clip")

    def on_clips_reordered(self, new_clips: List[Dict]):
        """Handle clip reordering"""
        self.clips = new_clips
        self.status_var.set(f"Clips reordered - {len(self.clips)} clips")

    def on_frame_change(self, frame_num: int):
        """Handle frame changes in video player"""
        # Could add marking overlay or other features here
        pass

    def save_order(self):
        """Save the current clip order"""
        try:
            project_file = self.save_project()
            messagebox.showinfo("Saved", f"Clip order saved to:\n{project_file}\n\n"
                                        f"You can now render the highlight video with:\n"
                                        f"python render_highlight.py --dir \"{self.base_dir}\"")
            self.status_var.set("Clip order saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save clip order:\n{e}")

    def reset_order(self):
        """Reset clips to original order"""
        if messagebox.askyesno("Reset Order", "Reset clips to original order?"):
            # Reload from file
            try:
                original_project = self.load_project()
                self.clips = list(original_project.get("clips", []))
                self.clip_list.clips = self.clips.copy()
                self.clip_list.refresh_list()
                self.status_var.set("Clip order reset to original")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reset order:\n{e}")

    def preview_final(self):
        """Preview what the final video would look like"""
        if not self.clips:
            messagebox.showwarning("No Clips", "No clips to preview")
            return

        # Create a simple preview by playing clips in sequence
        messagebox.showinfo("Preview", "Preview feature: Clips will play in the current order.\n"
                                      "Use the video player to preview individual clips.")

    def run(self):
        """Run the GUI"""
        self.root.mainloop()

def find_athletes() -> List[pathlib.Path]:
    """Find all athlete directories"""
    if not ATHLETES.exists():
        return []
    return sorted([p for p in ATHLETES.iterdir() if p.is_dir()])

def choose_athlete_interactive() -> Optional[pathlib.Path]:
    """Interactively choose an athlete"""
    options = find_athletes()
    if not options:
        print("No athlete folders found under ./athletes/")
        return None

    print("\nSelect an athlete:")
    for i, p in enumerate(options, 1):
        # Show status
        project_file = p / "project.json"
        status = " (ready)" if project_file.exists() else " (needs marking)"
        print(f"  {i}. {p.name}{status}")

    print("  q. Quit")

    while True:
        choice = input("Enter number: ").strip().lower()
        if choice in ("q", "quit", "exit"):
            return None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        print("Invalid choice. Try again.")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Enhanced GUI to reorder clips with advanced video player")
    parser.add_argument("--athlete", type=str, help="Athlete folder name under ./athletes")
    parser.add_argument("--dir", type=str, help="Full path to athlete folder")
    args = parser.parse_args()

    # Resolve athlete directory
    if args.dir:
        base_dir = pathlib.Path(args.dir).resolve()
    elif args.athlete:
        base_dir = (ATHLETES / args.athlete).resolve()
    else:
        base_dir = choose_athlete_interactive()
        if base_dir is None:
            sys.exit(0)

    if not base_dir.exists() or not base_dir.is_dir():
        print(f"Invalid athlete directory: {base_dir}")
        sys.exit(1)

    try:
        app = EnhancedReorderGUI(base_dir)
        app.run()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()