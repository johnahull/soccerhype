#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""
Enhanced Video Player Component
Provides advanced video playback controls with frame-accurate scrubbing,
multiple playback speeds, zoom functionality, and better user feedback.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import time
import threading
from PIL import Image, ImageTk
from typing import Optional, Callable, Tuple
import numpy as np

# Import OpenCV with fallback
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("OpenCV (cv2) not available. Enhanced video player functionality will be limited.")

class EnhancedVideoPlayer(tk.Frame):
    """Enhanced video player with advanced controls"""

    def __init__(self, master, bg="#222", on_frame_change: Optional[Callable] = None):
        super().__init__(master)
        self.configure(bg=bg)

        self.on_frame_change = on_frame_change
        self.bg_color = bg

        self.setup_ui()
        self.init_state()

    def setup_ui(self):
        """Setup the enhanced UI"""
        # Video display area
        self.display_frame = tk.Frame(self, bg=self.bg_color)
        self.display_frame.grid(row=0, column=0, columnspan=8, sticky="nsew", pady=(0, 10))

        self.display = tk.Label(self.display_frame, bd=2, relief="sunken", bg=self.bg_color,
                               text="No video loaded", fg="white", font=("Segoe UI", 12))
        self.display.pack(fill='both', expand=True)

        # Bind mouse events for interaction
        self.display.bind("<Button-1>", self.on_display_click)
        self.display.bind("<Motion>", self.on_display_motion)
        self.display.bind("<MouseWheel>", self.on_mouse_wheel)

        # Time display and progress
        time_frame = tk.Frame(self, bg=self.bg_color)
        time_frame.grid(row=1, column=0, columnspan=8, sticky="ew", pady=(0, 5))

        self.lbl_current_time = tk.Label(time_frame, text="00:00", bg=self.bg_color, fg="white", font=("Consolas", 10))
        self.lbl_current_time.pack(side='left')

        self.progress_var = tk.DoubleVar()
        self.progress_scale = tk.Scale(time_frame, from_=0, to=100, orient="horizontal",
                                     variable=self.progress_var, showvalue=False,
                                     command=self.on_progress_change, bg=self.bg_color,
                                     highlightthickness=0, troughcolor="#444")
        self.progress_scale.pack(side='left', fill='x', expand=True, padx=(10, 10))

        self.lbl_total_time = tk.Label(time_frame, text="00:00", bg=self.bg_color, fg="white", font=("Consolas", 10))
        self.lbl_total_time.pack(side='right')

        # Main control buttons
        control_frame = tk.Frame(self, bg=self.bg_color)
        control_frame.grid(row=2, column=0, columnspan=8, sticky="ew", pady=(0, 5))

        # Playback controls
        self.btn_play = tk.Button(control_frame, text="▶", width=3, command=self.toggle_play,
                                 font=("Segoe UI", 12, "bold"))
        self.btn_play.pack(side='left', padx=2)

        self.btn_stop = tk.Button(control_frame, text="⏹", width=3, command=self.stop,
                                 font=("Segoe UI", 12, "bold"))
        self.btn_stop.pack(side='left', padx=2)

        # Frame stepping
        tk.Button(control_frame, text="⏮", width=3, command=lambda: self.step_frame(-10),
                 font=("Segoe UI", 10)).pack(side='left', padx=1)
        tk.Button(control_frame, text="◀", width=3, command=lambda: self.step_frame(-1),
                 font=("Segoe UI", 10)).pack(side='left', padx=1)
        tk.Button(control_frame, text="▶", width=3, command=lambda: self.step_frame(1),
                 font=("Segoe UI", 10)).pack(side='left', padx=1)
        tk.Button(control_frame, text="⏭", width=3, command=lambda: self.step_frame(10),
                 font=("Segoe UI", 10)).pack(side='left', padx=1)

        # Speed control
        speed_frame = tk.Frame(control_frame, bg=self.bg_color)
        speed_frame.pack(side='left', padx=(20, 5))

        tk.Label(speed_frame, text="Speed:", bg=self.bg_color, fg="white", font=("Segoe UI", 9)).pack(side='top')
        self.speed_var = tk.StringVar(value="1.0x")
        self.speed_combo = ttk.Combobox(speed_frame, textvariable=self.speed_var, width=6,
                                       values=["0.1x", "0.25x", "0.5x", "0.75x", "1.0x",
                                              "1.25x", "1.5x", "2.0x", "3.0x", "4.0x"],
                                       state="readonly")
        self.speed_combo.pack(side='top')
        self.speed_combo.bind("<<ComboboxSelected>>", self.on_speed_change)

        # Volume and options (right side)
        options_frame = tk.Frame(control_frame, bg=self.bg_color)
        options_frame.pack(side='right', padx=5)

        self.loop_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="Loop", variable=self.loop_var,
                      bg=self.bg_color, fg="white", selectcolor="#444",
                      font=("Segoe UI", 9)).pack(side='top')

        self.zoom_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="Zoom", variable=self.zoom_var,
                      bg=self.bg_color, fg="white", selectcolor="#444",
                      font=("Segoe UI", 9), command=self.toggle_zoom).pack(side='top')

        # Information bar
        info_frame = tk.Frame(self, bg=self.bg_color)
        info_frame.grid(row=3, column=0, columnspan=8, sticky="ew")

        self.lbl_info = tk.Label(info_frame, text="Ready", bg=self.bg_color, fg="#aaa",
                                font=("Segoe UI", 8), anchor='w')
        self.lbl_info.pack(side='left', fill='x', expand=True)

        self.lbl_frame_info = tk.Label(info_frame, text="Frame: 0/0", bg=self.bg_color, fg="#aaa",
                                      font=("Consolas", 8))
        self.lbl_frame_info.pack(side='right')

        # Configure grid weights
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def init_state(self):
        """Initialize player state"""
        self.cap = None
        self.video_path = None
        self.fps = 30.0
        self.total_frames = 0
        self.current_frame = 0
        self.playing = False
        self.playback_speed = 1.0
        self.zoom_enabled = False
        self.zoom_center = None
        self.zoom_factor = 2.0

        # Playback thread control
        self._playback_thread = None
        self._stop_playback = False
        self._last_frame_time = 0

        # Display state
        self._current_display_image = None
        self._video_size = (0, 0)
        self._display_size = (0, 0)
        self._scale_factor = 1.0

        # Bind keyboard shortcuts
        self.master.bind_all("<space>", lambda e: self.toggle_play())
        self.master.bind_all("<Left>", lambda e: self.step_frame(-1))
        self.master.bind_all("<Right>", lambda e: self.step_frame(1))
        self.master.bind_all("<Up>", lambda e: self.step_frame(-10))
        self.master.bind_all("<Down>", lambda e: self.step_frame(10))

    def load_video(self, video_path: str) -> bool:
        """Load a video file"""
        if not CV2_AVAILABLE:
            self.update_info("OpenCV not available - cannot load video")
            messagebox.showerror("Missing Dependency",
                               "OpenCV (cv2) is required for video playback.\n"
                               "Please install it with: pip install opencv-python")
            return False

        self.stop()

        try:
            self.cap = cv2.VideoCapture(video_path)
            if not self.cap.isOpened():
                raise RuntimeError(f"Could not open video: {video_path}")

            self.video_path = video_path

            # Get video properties
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            self._video_size = (
                int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            )

            # Update UI
            self.progress_scale.config(to=max(1, self.total_frames - 1))
            self.update_time_display()
            self.update_frame_info()

            # Load first frame
            self.current_frame = 0
            self.show_frame()

            self.update_info(f"Loaded: {video_path}")
            return True

        except Exception as e:
            self.update_info(f"Error loading video: {e}")
            return False

    def show_frame(self):
        """Display the current frame"""
        if not self.cap:
            return

        # Seek to current frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()

        if not ret:
            return

        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Apply zoom if enabled
        if self.zoom_enabled and self.zoom_center:
            frame_rgb = self.apply_zoom(frame_rgb)

        # Convert to PIL Image
        pil_image = Image.fromarray(frame_rgb)

        # Resize to fit display
        display_w = self.display.winfo_width() or 640
        display_h = self.display.winfo_height() or 480

        # Calculate scale maintaining aspect ratio
        scale_x = display_w / pil_image.width
        scale_y = display_h / pil_image.height
        self._scale_factor = min(scale_x, scale_y, 1.0)  # Don't upscale

        new_w = int(pil_image.width * self._scale_factor)
        new_h = int(pil_image.height * self._scale_factor)

        pil_image = pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Convert to Tkinter format
        self._current_display_image = ImageTk.PhotoImage(pil_image)
        self.display.configure(image=self._current_display_image, text="")

        # Update displays
        self.update_time_display()
        self.update_frame_info()

        # Trigger callback
        if self.on_frame_change:
            self.on_frame_change(self.current_frame)

    def apply_zoom(self, frame: np.ndarray) -> np.ndarray:
        """Apply zoom to frame around zoom center"""
        h, w = frame.shape[:2]

        if not self.zoom_center:
            # Default to center
            self.zoom_center = (w // 2, h // 2)

        cx, cy = self.zoom_center

        # Calculate crop region
        crop_w = int(w / self.zoom_factor)
        crop_h = int(h / self.zoom_factor)

        x1 = max(0, min(w - crop_w, cx - crop_w // 2))
        y1 = max(0, min(h - crop_h, cy - crop_h // 2))
        x2 = x1 + crop_w
        y2 = y1 + crop_h

        # Crop and resize
        cropped = frame[y1:y2, x1:x2]
        zoomed = cv2.resize(cropped, (w, h))

        return zoomed

    def toggle_play(self):
        """Toggle play/pause"""
        if self.playing:
            self.pause()
        else:
            self.play()

    def play(self):
        """Start playback"""
        if not self.cap or self.playing:
            return

        self.playing = True
        self.btn_play.config(text="⏸")
        self._stop_playback = False

        # Start playback thread
        self._playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._playback_thread.start()

    def pause(self):
        """Pause playback"""
        self.playing = False
        self.btn_play.config(text="▶")
        self._stop_playback = True

    def stop(self):
        """Stop playback and reset to beginning"""
        self.pause()
        self.current_frame = 0
        self.progress_var.set(0)
        if self.cap:
            self.show_frame()

    def step_frame(self, step: int):
        """Step forward or backward by specified frames"""
        if not self.cap:
            return

        self.current_frame = max(0, min(self.total_frames - 1, self.current_frame + step))
        self.progress_var.set(self.current_frame)
        self.show_frame()

    def seek_to_frame(self, frame_num: int):
        """Seek to specific frame"""
        if not self.cap:
            return

        self.current_frame = max(0, min(self.total_frames - 1, frame_num))
        self.progress_var.set(self.current_frame)
        self.show_frame()

    def _playback_loop(self):
        """Main playback loop (runs in separate thread)"""
        while self.playing and not self._stop_playback and self.cap:
            start_time = time.time()

            # Advance frame
            self.current_frame += 1

            # Check for end of video
            if self.current_frame >= self.total_frames:
                if self.loop_var.get():
                    self.current_frame = 0
                else:
                    self.master.after(0, self.pause)
                    break

            # Update UI in main thread
            self.master.after(0, self._update_playback_ui)

            # Calculate delay for target FPS
            target_delay = 1.0 / (self.fps * self.playback_speed)
            elapsed = time.time() - start_time
            sleep_time = max(0, target_delay - elapsed)

            if sleep_time > 0:
                time.sleep(sleep_time)

    def _update_playback_ui(self):
        """Update UI during playback (called from main thread)"""
        self.progress_var.set(self.current_frame)
        self.show_frame()

    def on_progress_change(self, value):
        """Handle progress bar changes"""
        if not self.playing:  # Only allow seeking when paused
            frame_num = int(float(value))
            self.seek_to_frame(frame_num)

    def on_speed_change(self, event=None):
        """Handle speed changes"""
        speed_text = self.speed_var.get()
        try:
            self.playback_speed = float(speed_text.replace('x', ''))
        except ValueError:
            self.playback_speed = 1.0

    def on_display_click(self, event):
        """Handle clicks on video display"""
        if self.zoom_enabled:
            # Convert click position to video coordinates
            if self._scale_factor > 0:
                video_x = int(event.x / self._scale_factor)
                video_y = int(event.y / self._scale_factor)

                # Update zoom center
                self.zoom_center = (video_x, video_y)
                self.show_frame()

    def on_display_motion(self, event):
        """Handle mouse motion over display"""
        if self._scale_factor > 0:
            video_x = int(event.x / self._scale_factor)
            video_y = int(event.y / self._scale_factor)
            self.update_info(f"Mouse: ({video_x}, {video_y})")

    def on_mouse_wheel(self, event):
        """Handle mouse wheel for zoom factor adjustment"""
        if self.zoom_enabled:
            if event.delta > 0:
                self.zoom_factor = min(8.0, self.zoom_factor * 1.2)
            else:
                self.zoom_factor = max(1.0, self.zoom_factor / 1.2)
            self.show_frame()

    def toggle_zoom(self):
        """Toggle zoom mode"""
        self.zoom_enabled = self.zoom_var.get()
        if not self.zoom_enabled:
            self.zoom_center = None
        self.show_frame()

    def update_time_display(self):
        """Update time display labels"""
        if not self.cap:
            return

        current_seconds = self.current_frame / self.fps if self.fps > 0 else 0
        total_seconds = self.total_frames / self.fps if self.fps > 0 else 0

        def format_time(seconds):
            mins, secs = divmod(int(seconds), 60)
            return f"{mins:02d}:{secs:02d}"

        self.lbl_current_time.config(text=format_time(current_seconds))
        self.lbl_total_time.config(text=format_time(total_seconds))

    def update_frame_info(self):
        """Update frame information display"""
        self.lbl_frame_info.config(text=f"Frame: {self.current_frame}/{self.total_frames}")

    def update_info(self, message: str):
        """Update info bar message"""
        self.lbl_info.config(text=message)

    def destroy(self):
        """Clean up resources"""
        self.pause()
        if self.cap:
            self.cap.release()
        super().destroy()

# Example usage and testing
if __name__ == "__main__":
    import sys
    from tkinter import filedialog

    def test_player():
        root = tk.Tk()
        root.title("Enhanced Video Player Test")
        root.geometry("800x600")

        def on_frame_change(frame_num):
            print(f"Frame changed to: {frame_num}")

        player = EnhancedVideoPlayer(root, on_frame_change=on_frame_change)
        player.pack(fill='both', expand=True, padx=10, pady=10)

        def load_video():
            filename = filedialog.askopenfilename(
                title="Select Video File",
                filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")]
            )
            if filename:
                player.load_video(filename)

        tk.Button(root, text="Load Video", command=load_video).pack(pady=5)

        root.mainloop()

    test_player()