#!/usr/bin/env python3
"""
SoccerHype GUI - Unified interface for athlete highlight video creation
Main launcher that provides a guided workflow for all video processing tasks.
"""

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from typing import Dict, List, Optional

# Import enhanced error handling
try:
    from utils.error_handling import (
        ErrorHandler, initialize_error_handling, error_handler,
        ValidationHelper, ProgressReporter
    )
    ERROR_HANDLING_AVAILABLE = True
except ImportError:
    ERROR_HANDLING_AVAILABLE = False
    print("Enhanced error handling not available, using basic error handling")

def sanitize_profile_id(name: str) -> str:
    """Sanitize a name to create a safe profile ID"""
    # Remove all non-alphanumeric characters except spaces, convert to lowercase
    clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name).strip().lower()
    # Replace spaces with underscores and collapse multiple underscores
    clean_name = re.sub(r'\s+', '_', clean_name)
    # Remove leading/trailing underscores and limit length
    clean_name = clean_name.strip('_')[:20]
    # Ensure it's not empty
    if not clean_name:
        clean_name = 'player'
    return clean_name

ROOT = pathlib.Path.cwd()
ATHLETES = ROOT / "athletes"

class AthleteManager:
    """Handles athlete data and folder management"""

    def __init__(self):
        if ERROR_HANDLING_AVAILABLE:
            self.error_handler = ErrorHandler("athlete_manager")
        else:
            self.error_handler = None

    def discover_athletes(self) -> List[pathlib.Path]:
        """Find all athlete directories"""
        if ERROR_HANDLING_AVAILABLE:
            return self._discover_athletes_with_error_handling()
        else:
            return self._discover_athletes_basic()

    def _discover_athletes_with_error_handling(self) -> List[pathlib.Path]:
        """Find all athlete directories with error handling"""
        @error_handler("Discovering athletes", show_dialog=False)
        def _discover():
            if ERROR_HANDLING_AVAILABLE:
                ValidationHelper.validate_directory(ATHLETES, create_if_missing=True)
            if not ATHLETES.exists():
                return []
            return sorted([p for p in ATHLETES.iterdir() if p.is_dir()])
        return _discover()

    def _discover_athletes_basic(self) -> List[pathlib.Path]:
        """Find all athlete directories without error handling"""
        try:
            if not ATHLETES.exists():
                ATHLETES.mkdir(exist_ok=True)
                return []
            return sorted([p for p in ATHLETES.iterdir() if p.is_dir()])
        except Exception:
            return []

    def get_athlete_status(self, athlete_dir: pathlib.Path) -> Dict[str, bool]:
        """Check completion status of workflow steps"""
        if ERROR_HANDLING_AVAILABLE:
            return self._get_athlete_status_with_error_handling(athlete_dir)
        else:
            return self._get_athlete_status_basic(athlete_dir)

    def _get_athlete_status_with_error_handling(self, athlete_dir: pathlib.Path) -> Dict[str, bool]:
        """Check athlete status with error handling"""
        @error_handler("Checking athlete status", show_dialog=False)
        def _get_status():
            if ERROR_HANDLING_AVAILABLE:
                ValidationHelper.validate_directory(athlete_dir)

            project_file = athlete_dir / "project.json"
            final_video = athlete_dir / "output" / "final.mp4"
            clips_in = athlete_dir / "clips_in"

            has_clips = clips_in.exists() and any(clips_in.iterdir())
            has_project = project_file.exists()
            has_final = final_video.exists()

            return {
                "has_clips": has_clips,
                "has_project": has_project,
                "has_final": has_final,
                "needs_marking": has_clips and not has_project,
                "needs_rendering": has_project and not has_final
            }
        return _get_status()

    def _get_athlete_status_basic(self, athlete_dir: pathlib.Path) -> Dict[str, bool]:
        """Check athlete status without error handling"""
        try:
            project_file = athlete_dir / "project.json"
            final_video = athlete_dir / "output" / "final.mp4"
            clips_in = athlete_dir / "clips_in"

            has_clips = clips_in.exists() and any(clips_in.iterdir())
            has_project = project_file.exists()
            has_final = final_video.exists()

            return {
                "has_clips": has_clips,
                "has_project": has_project,
                "has_final": has_final,
                "needs_marking": has_clips and not has_project,
                "needs_rendering": has_project and not has_final
            }
        except Exception:
            return {
                "has_clips": False,
                "has_project": False,
                "has_final": False,
                "needs_marking": False,
                "needs_rendering": False
            }

    def create_athlete(self, name: str) -> pathlib.Path:
        """Create new athlete folder structure"""
        if ERROR_HANDLING_AVAILABLE:
            return self._create_athlete_with_error_handling(name)
        else:
            return self._create_athlete_basic(name)

    def _create_athlete_with_error_handling(self, name: str) -> pathlib.Path:
        """Create athlete with error handling"""
        @error_handler("Creating athlete folder")
        def _create():
            if not name or not name.strip():
                raise ValueError("Athlete name cannot be empty")

            athlete_dir = ATHLETES / name.strip()
            if athlete_dir.exists():
                raise FileExistsError(f"Athlete '{name}' already exists")

            if ERROR_HANDLING_AVAILABLE:
                # Check disk space (estimate 1GB needed)
                ValidationHelper.validate_disk_space(ATHLETES, 1024 * 1024 * 1024)

            # Create directory structure
            (athlete_dir / "clips_in").mkdir(parents=True, exist_ok=True)
            (athlete_dir / "intro").mkdir(parents=True, exist_ok=True)
            (athlete_dir / "work" / "proxies").mkdir(parents=True, exist_ok=True)
            (athlete_dir / "output").mkdir(parents=True, exist_ok=True)

            return athlete_dir
        return _create()

    def _create_athlete_basic(self, name: str) -> pathlib.Path:
        """Create athlete without error handling"""
        if not name or not name.strip():
            raise ValueError("Athlete name cannot be empty")

        athlete_dir = ATHLETES / name.strip()
        if athlete_dir.exists():
            raise FileExistsError(f"Athlete '{name}' already exists")

        # Create directory structure
        (athlete_dir / "clips_in").mkdir(parents=True, exist_ok=True)
        (athlete_dir / "intro").mkdir(parents=True, exist_ok=True)
        (athlete_dir / "work" / "proxies").mkdir(parents=True, exist_ok=True)
        (athlete_dir / "output").mkdir(parents=True, exist_ok=True)

        return athlete_dir

class ProgressDialog:
    """Modal dialog showing operation progress"""

    def __init__(self, parent, title, operation_name):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x150")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center on parent
        self.dialog.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")

        # Progress elements
        tk.Label(self.dialog, text=operation_name, font=("Segoe UI", 10)).pack(pady=10)

        self.progress = ttk.Progressbar(self.dialog, mode='indeterminate')
        self.progress.pack(pady=10, padx=20, fill='x')
        self.progress.start()

        self.status_label = tk.Label(self.dialog, text="Starting...", font=("Segoe UI", 8))
        self.status_label.pack(pady=5)

        # Cancel button
        self.cancel_btn = tk.Button(self.dialog, text="Cancel", command=self.cancel)
        self.cancel_btn.pack(pady=10)

        self.cancelled = False
        self.process = None

    def update_status(self, text):
        """Update status text"""
        self.status_label.config(text=text)
        self.dialog.update()

    def cancel(self):
        """Cancel operation"""
        self.cancelled = True
        if self.process:
            self.process.terminate()
        self.dialog.destroy()

    def close(self):
        """Close dialog"""
        self.progress.stop()
        self.dialog.destroy()

class SoccerHypeGUI:
    """Main GUI application"""

    def __init__(self):
        # Initialize error handling
        if ERROR_HANDLING_AVAILABLE:
            initialize_error_handling()
            self.error_handler = ErrorHandler("soccerhype_gui")
        else:
            self.error_handler = None

        self.root = tk.Tk()
        self.root.title("SoccerHype - Athlete Highlight Video Creator")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)

        # Initialize athlete manager
        self.athlete_manager = AthleteManager()

        # Ensure athletes directory exists
        ATHLETES.mkdir(exist_ok=True)

        self.setup_ui()
        self.refresh_athletes()

    def setup_ui(self):
        """Initialize the user interface"""
        # Main menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Athlete...", command=self.new_athlete)
        file_menu.add_separator()
        file_menu.add_command(label="Manage Player Profiles...", command=self.manage_player_profiles)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        # Main layout
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Title and description
        title_frame = tk.Frame(main_frame)
        title_frame.pack(fill='x', pady=(0, 20))

        tk.Label(title_frame, text="SoccerHype", font=("Segoe UI", 20, "bold")).pack()
        tk.Label(title_frame, text="Create professional athlete highlight videos with red spotlight tracking",
                font=("Segoe UI", 10)).pack()

        # Control buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(0, 10))

        tk.Button(button_frame, text="New Athlete", command=self.new_athlete,
                 bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold")).pack(side='left', padx=(0, 10))
        tk.Button(button_frame, text="Refresh", command=self.refresh_athletes,
                 font=("Segoe UI", 10)).pack(side='left', padx=(0, 10))
        tk.Button(button_frame, text="Batch Operations", command=self.batch_operations,
                 font=("Segoe UI", 10)).pack(side='right')

        # Athletes list
        list_frame = tk.Frame(main_frame)
        list_frame.pack(fill='both', expand=True)

        tk.Label(list_frame, text="Athletes", font=("Segoe UI", 12, "bold")).pack(anchor='w')

        # Treeview for athletes with status
        columns = ("Name", "Status", "Clips", "Marked", "Rendered")
        self.athlete_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        # Configure columns
        self.athlete_tree.heading("Name", text="Athlete Name")
        self.athlete_tree.heading("Status", text="Workflow Status")
        self.athlete_tree.heading("Clips", text="Has Clips")
        self.athlete_tree.heading("Marked", text="Clips Marked")
        self.athlete_tree.heading("Rendered", text="Final Video")

        self.athlete_tree.column("Name", width=200)
        self.athlete_tree.column("Status", width=150)
        self.athlete_tree.column("Clips", width=80)
        self.athlete_tree.column("Marked", width=80)
        self.athlete_tree.column("Rendered", width=80)

        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.athlete_tree.yview)
        self.athlete_tree.configure(yscrollcommand=scrollbar.set)

        self.athlete_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Double-click to open athlete
        self.athlete_tree.bind("<Double-1>", self.open_athlete)

        # Action buttons for selected athlete
        action_frame = tk.Frame(main_frame)
        action_frame.pack(fill='x', pady=(10, 0))

        tk.Button(action_frame, text="Open Folder", command=self.open_folder,
                 font=("Segoe UI", 9)).pack(side='left', padx=(0, 5))
        tk.Button(action_frame, text="Mark Plays", command=self.mark_plays,
                 font=("Segoe UI", 9)).pack(side='left', padx=(0, 5))
        tk.Button(action_frame, text="Reorder Clips", command=self.reorder_clips,
                 font=("Segoe UI", 9)).pack(side='left', padx=(0, 5))
        tk.Button(action_frame, text="Render Video", command=self.render_video,
                 font=("Segoe UI", 9)).pack(side='left', padx=(0, 5))
        tk.Button(action_frame, text="View Final Video", command=self.view_final,
                 font=("Segoe UI", 9)).pack(side='right')

    def refresh_athletes(self):
        """Refresh the athletes list"""
        try:
            self._refresh_athletes_impl()
        except Exception as e:
            if ERROR_HANDLING_AVAILABLE and self.error_handler:
                self.error_handler.handle_error(e, "Refreshing athletes list", show_dialog=False)
            else:
                print(f"Error refreshing athletes: {e}")

    def _refresh_athletes_impl(self):
        """Implementation of refresh athletes"""
        # Clear existing items
        for item in self.athlete_tree.get_children():
            self.athlete_tree.delete(item)

        athletes = self.athlete_manager.discover_athletes()
        if not athletes:
            # Show helpful message when no athletes exist
            self.athlete_tree.insert("", 'end', values=("No athletes found", "Click 'New Athlete' to get started", "", "", ""))
            return

        for athlete_dir in athletes:
            status = self.athlete_manager.get_athlete_status(athlete_dir)

            # Determine workflow status
            if not status["has_clips"]:
                workflow_status = "Needs clips"
            elif status["needs_marking"]:
                workflow_status = "Ready to mark"
            elif status["needs_rendering"]:
                workflow_status = "Ready to render"
            elif status["has_final"]:
                workflow_status = "Complete"
            else:
                workflow_status = "Unknown"

            # Status indicators
            clips_status = "✓" if status["has_clips"] else "✗"
            marked_status = "✓" if status["has_project"] else "✗"
            rendered_status = "✓" if status["has_final"] else "✗"

            self.athlete_tree.insert("", 'end', values=(
                athlete_dir.name,
                workflow_status,
                clips_status,
                marked_status,
                rendered_status
            ))

    def get_selected_athlete(self) -> Optional[pathlib.Path]:
        """Get currently selected athlete directory"""
        selection = self.athlete_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an athlete first.")
            return None

        item = self.athlete_tree.item(selection[0])
        athlete_name = item['values'][0]

        if athlete_name == "No athletes found":
            return None

        return ATHLETES / athlete_name

    def new_athlete(self):
        """Create a new athlete"""
        dialog = tk.Toplevel(self.root)
        dialog.title("New Athlete")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Center on parent
        dialog.geometry(f"+{self.root.winfo_rootx() + 200}+{self.root.winfo_rooty() + 150}")

        tk.Label(dialog, text="Enter athlete name:", font=("Segoe UI", 10)).pack(pady=10)

        name_var = tk.StringVar()
        entry = tk.Entry(dialog, textvariable=name_var, font=("Segoe UI", 10), width=30)
        entry.pack(pady=5)
        entry.focus()

        def create():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Please enter a name.")
                return

            athlete_dir = self.athlete_manager.create_athlete(name)
            if athlete_dir:
                dialog.destroy()
                self.refresh_athletes()
                messagebox.showinfo("Success", f"Created athlete folder: {athlete_dir.name}\n\nNext step: Add video clips to the 'clips_in' folder.")

        def cancel():
            dialog.destroy()

        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Create", command=create, bg="#4CAF50", fg="white").pack(side='left', padx=5)
        tk.Button(button_frame, text="Cancel", command=cancel).pack(side='left', padx=5)

        # Enter key to create
        dialog.bind('<Return>', lambda e: create())

    def open_athlete(self, event=None):
        """Open athlete workflow (double-click handler)"""
        athlete_dir = self.get_selected_athlete()
        if not athlete_dir:
            return

        status = self.athlete_manager.get_athlete_status(athlete_dir)

        if not status["has_clips"]:
            self.open_folder()
        elif status["needs_marking"]:
            self.mark_plays()
        elif status["needs_rendering"]:
            self.render_video()
        else:
            self.view_final()

    def open_folder(self):
        """Open athlete folder in file manager"""
        athlete_dir = self.get_selected_athlete()
        if not athlete_dir:
            return

        try:
            import platform
            system = platform.system()
            if system == "Linux":
                subprocess.run(["xdg-open", str(athlete_dir)], check=True)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", str(athlete_dir)], check=True)
            elif system == "Windows":
                subprocess.run(["explorer", str(athlete_dir)], check=True)
            else:
                messagebox.showinfo("Info", f"Please open folder manually: {athlete_dir}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            messagebox.showerror("Error", f"Could not open folder: {athlete_dir}")

    def mark_plays(self):
        """Launch mark_play.py for selected athlete"""
        athlete_dir = self.get_selected_athlete()
        if not athlete_dir:
            return

        status = self.athlete_manager.get_athlete_status(athlete_dir)
        if not status["has_clips"]:
            messagebox.showwarning("No Clips", f"No clips found in {athlete_dir.name}/clips_in/\n\nAdd video clips first.")
            return

        # Check if project already exists
        project_exists = (athlete_dir / "project.json").exists()

        # Show player information dialog
        dialog = PlayerInfoDialog(self.root, athlete_dir.name, project_exists)

        if dialog.result is None:
            # User cancelled
            return

        if dialog.result == "save_only":
            # User chose to save info only, don't proceed with marking
            self.refresh_athletes()
            return

        player_data = dialog.result

        # Build command line arguments
        args = ["--dir", str(athlete_dir), "--overwrite"]

        if player_data["include_intro"]:
            args.append("--include-intro")

            # Add player information arguments
            if player_data["name"]:
                args.extend(["--player-name", player_data["name"]])
            if player_data["title"]:
                args.extend(["--title", player_data["title"]])
            if player_data["position"]:
                args.extend(["--position", player_data["position"]])
            if player_data["grad_year"]:
                args.extend(["--grad-year", player_data["grad_year"]])
            if player_data["club_team"]:
                args.extend(["--club-team", player_data["club_team"]])
            if player_data["high_school"]:
                args.extend(["--high-school", player_data["high_school"]])
            if player_data["height_weight"]:
                args.extend(["--height-weight", player_data["height_weight"]])
            if player_data["gpa"]:
                args.extend(["--gpa", player_data["gpa"]])
            if player_data["email"]:
                args.extend(["--email", player_data["email"]])
            if player_data["phone"]:
                args.extend(["--phone", player_data["phone"]])

        self.run_script_async("mark_play.py", args,
                             "Marking Plays", f"Launching play marking for {athlete_dir.name}")

    def reorder_clips(self):
        """Launch reorder_clips.py for selected athlete"""
        athlete_dir = self.get_selected_athlete()
        if not athlete_dir:
            return

        status = self.athlete_manager.get_athlete_status(athlete_dir)
        if not status["has_project"]:
            messagebox.showwarning("No Project", f"No project file found for {athlete_dir.name}\n\nMark plays first.")
            return

        self.run_script_async("reorder_clips.py", ["--dir", str(athlete_dir)],
                             "Reordering Clips", f"Launching clip reordering for {athlete_dir.name}")

    def render_video(self):
        """Launch render_highlight.py for selected athlete"""
        athlete_dir = self.get_selected_athlete()
        if not athlete_dir:
            return

        status = self.athlete_manager.get_athlete_status(athlete_dir)
        if not status["has_project"]:
            messagebox.showwarning("No Project", f"No project file found for {athlete_dir.name}\n\nMark plays first.")
            return

        self.run_script_async("render_highlight.py", ["--dir", str(athlete_dir)],
                             "Rendering Video", f"Rendering highlight video for {athlete_dir.name}")

    def view_final(self):
        """Open final video in default player"""
        athlete_dir = self.get_selected_athlete()
        if not athlete_dir:
            return

        final_video = athlete_dir / "output" / "final.mp4"
        if not final_video.exists():
            messagebox.showwarning("No Video", f"Final video not found for {athlete_dir.name}\n\nRender video first.")
            return

        try:
            import platform
            system = platform.system()
            if system == "Linux":
                subprocess.run(["xdg-open", str(final_video)], check=True)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", str(final_video)], check=True)
            elif system == "Windows":
                subprocess.run(["start", str(final_video)], shell=True, check=True)
            else:
                messagebox.showinfo("Info", f"Please open video manually: {final_video}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            messagebox.showerror("Error", f"Could not open video: {final_video}")

    def batch_operations(self):
        """Launch batch operations dialog"""
        BatchOperationsDialog(self.root, self.refresh_athletes)

    def run_script_async(self, script_name, args, title, description):
        """Run a Python script asynchronously with progress dialog"""
        progress = ProgressDialog(self.root, title, description)

        def run():
            try:
                cmd = [sys.executable, script_name] + args
                progress.update_status(f"Running: {' '.join(cmd)}")

                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                progress.process = process

                stdout, stderr = process.communicate()

                if not progress.cancelled:
                    if process.returncode == 0:
                        progress.update_status("Completed successfully!")
                        time.sleep(1)
                        progress.close()
                        self.refresh_athletes()
                    else:
                        progress.close()
                        messagebox.showerror("Error", f"Script failed:\n{stderr}")

            except Exception as e:
                if not progress.cancelled:
                    progress.close()
                    messagebox.showerror("Error", f"Failed to run script: {e}")

        threading.Thread(target=run, daemon=True).start()

    def manage_player_profiles(self):
        """Open standalone player profile management dialog"""
        ProfileManagementDialog(self.root)

    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About SoccerHype",
                           "SoccerHype v1.0\n\n"
                           "Professional athlete highlight video creator\n"
                           "with red spotlight tracking and intro slates.\n\n"
                           "Features:\n"
                           "• Interactive play marking\n"
                           "• Automated video processing\n"
                           "• Professional intro slates\n"
                           "• Batch processing\n\n"
                           "Created for parents, coaches, and athletes.")

    def run(self):
        """Start the GUI application"""
        self.root.mainloop()

class PlayerInfoDialog:
    """Dialog for collecting player information before marking plays"""

    def __init__(self, parent, athlete_name, project_exists=False):
        self.result = None
        self.athlete_name = athlete_name

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Player Information - {athlete_name}")
        self.dialog.geometry("650x650")  # Increased width for button visibility
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center on parent
        self.dialog.geometry(f"+{parent.winfo_rootx() + 150}+{parent.winfo_rooty() + 50}")

        # Variables for form fields
        self.name_var = tk.StringVar(value=athlete_name)
        self.title_var = tk.StringVar()
        self.position_var = tk.StringVar()
        self.grad_year_var = tk.StringVar()
        self.club_team_var = tk.StringVar()
        self.high_school_var = tk.StringVar()
        self.height_weight_var = tk.StringVar()
        self.gpa_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.include_intro_var = tk.BooleanVar(value=True)
        self.overwrite_var = tk.BooleanVar(value=project_exists)

        # Player profile management
        self.profiles_db_path = pathlib.Path.cwd() / "players_database.json"
        self.player_profiles = self.load_player_profiles()
        self.selected_profile_id = None

        self.setup_ui(project_exists)
        self.scan_existing_media()  # Check for existing intro media

        # Wait for dialog to complete
        self.dialog.wait_window()

    def setup_ui(self, project_exists):
        """Setup the player information form"""
        main_frame = tk.Frame(self.dialog)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # Title
        tk.Label(main_frame, text="Player Information",
                font=("Segoe UI", 16, "bold")).pack(pady=(0, 15))

        if project_exists:
            warning_frame = tk.Frame(main_frame, bg="#fff3cd", relief="solid", bd=1)
            warning_frame.pack(fill='x', pady=(0, 10))
            tk.Label(warning_frame, text="⚠ Project file exists and will be overwritten",
                    font=("Segoe UI", 9), bg="#fff3cd", fg="#856404").pack(pady=5)

        # Create scrollable frame for form fields
        canvas = tk.Canvas(main_frame, height=450)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Profile Selection Section (Always Show)
        profile_frame = tk.Frame(scrollable_frame, bg="#e8f4fd", relief="solid", bd=1)
        profile_frame.pack(fill='x', pady=(0, 15), padx=5)

        tk.Label(profile_frame, text="Player Profile Management:",
                font=("Segoe UI", 10, "bold"), bg="#e8f4fd").pack(anchor='w', padx=10, pady=(5, 0))

        profile_select_frame = tk.Frame(profile_frame, bg="#e8f4fd")
        profile_select_frame.pack(fill='x', padx=10, pady=5)

        # Profile dropdown
        self.profile_combo = ttk.Combobox(profile_select_frame, state="readonly", width=40)
        profile_names = ["<New Player>"]
        if self.player_profiles:
            profile_names.extend([p["name"] for p in self.player_profiles.values()])
        self.profile_combo['values'] = profile_names
        self.profile_combo.set("<New Player>")
        self.profile_combo.bind('<<ComboboxSelected>>', self.on_profile_selected)
        self.profile_combo.pack(side='left', fill='x', expand=True)

        # Profile management buttons
        profile_btn_frame = tk.Frame(profile_select_frame, bg="#e8f4fd")
        profile_btn_frame.pack(side='right', padx=(10, 0))

        tk.Button(profile_btn_frame, text="Save as Profile",
                 command=self.save_current_as_profile, font=("Segoe UI", 9)).pack(side='left', padx=2)
        tk.Button(profile_btn_frame, text="Delete Profile",
                 command=self.delete_selected_profile, font=("Segoe UI", 9)).pack(side='left', padx=2)

        # Dynamic help text
        help_text = "Select a profile to auto-fill fields, or choose '<New Player>' to enter manually."
        if not self.player_profiles:
            help_text = "Enter player information below, then click 'Save as Profile' to save for future use."
        tk.Label(profile_frame, text=help_text,
                font=("Segoe UI", 9), fg="#666", bg="#e8f4fd").pack(anchor='w', padx=10, pady=(0, 5))

        # Form fields
        fields = [
            ("Player Name:", self.name_var, True),
            ("Title (optional):", self.title_var, False),
            ("Position:", self.position_var, False),
            ("Graduation Year:", self.grad_year_var, False),
            ("Club Team:", self.club_team_var, False),
            ("High School:", self.high_school_var, False),
            ("Height/Weight:", self.height_weight_var, False),
            ("GPA:", self.gpa_var, False),
            ("Email:", self.email_var, False),
            ("Phone:", self.phone_var, False),
        ]

        for label_text, var, required in fields:
            field_frame = tk.Frame(scrollable_frame)
            field_frame.pack(fill='x', pady=8)

            label = tk.Label(field_frame, text=label_text, font=("Segoe UI", 10))
            if required:
                label.config(font=("Segoe UI", 10, "bold"))
            label.pack(anchor='w')

            entry = tk.Entry(field_frame, textvariable=var, font=("Segoe UI", 10), width=50)
            entry.pack(fill='x', pady=2)

            if required:
                entry.config(highlightbackground="#007ACC", highlightthickness=1)

        # Intro Media Section
        intro_frame = tk.Frame(scrollable_frame, relief="solid", bd=1, bg="#f8f9fa")
        intro_frame.pack(fill='x', pady=15)

        intro_title = tk.Label(intro_frame, text="Intro Media (Optional)",
                              font=("Segoe UI", 12, "bold"), bg="#f8f9fa")
        intro_title.pack(anchor='w', padx=10, pady=(10, 5))

        intro_desc = tk.Label(intro_frame,
                             text="Add a player picture or intro video for the highlight slate",
                             font=("Segoe UI", 9), bg="#f8f9fa", fg="#666")
        intro_desc.pack(anchor='w', padx=10, pady=(0, 10))

        # Media selection frame
        media_frame = tk.Frame(intro_frame, bg="#f8f9fa")
        media_frame.pack(fill='x', padx=10, pady=(0, 10))

        self.selected_media_var = tk.StringVar()
        self.media_files = []  # Store available media files

        # Current selection display
        self.current_media_label = tk.Label(media_frame, text="No media selected",
                                          font=("Segoe UI", 9), bg="#f8f9fa")
        self.current_media_label.pack(anchor='w', pady=(0, 5))

        # Buttons for media management
        media_btn_frame = tk.Frame(media_frame, bg="#f8f9fa")
        media_btn_frame.pack(fill='x')

        tk.Button(media_btn_frame, text="Browse & Upload", command=self.browse_media,
                 font=("Segoe UI", 9), bg="#007ACC", fg="white").pack(side='left', padx=(0, 5))
        tk.Button(media_btn_frame, text="Choose Existing", command=self.choose_existing_media,
                 font=("Segoe UI", 9)).pack(side='left', padx=(0, 5))
        tk.Button(media_btn_frame, text="Clear Selection", command=self.clear_media_selection,
                 font=("Segoe UI", 9)).pack(side='left')

        # Checkboxes
        checkbox_frame = tk.Frame(scrollable_frame)
        checkbox_frame.pack(fill='x', pady=15)

        tk.Checkbutton(checkbox_frame, text="Include intro screen with player slate",
                      variable=self.include_intro_var, font=("Segoe UI", 10)).pack(anchor='w')

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Buttons - stacked vertically for better visibility
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(15, 0))

        continue_btn = tk.Button(button_frame, text="Continue to Mark Plays", command=self.accept,
                               bg="#4CAF50", fg="white", font=("Segoe UI", 11, "bold"))
        continue_btn.pack(fill='x', pady=(0, 8))

        save_btn = tk.Button(button_frame, text="Save Info Only", command=self.save_only,
                           bg="#FF9800", fg="white", font=("Segoe UI", 10))
        save_btn.pack(fill='x', pady=(0, 8))

        cancel_btn = tk.Button(button_frame, text="Cancel", command=self.cancel,
                             font=("Segoe UI", 10))
        cancel_btn.pack(fill='x')

        # Focus on name field
        if hasattr(self, '_name_entry'):
            self._name_entry.focus()

    def scan_existing_media(self):
        """Scan for existing intro media files"""
        athlete_dir = pathlib.Path("athletes") / self.athlete_name
        intro_dir = athlete_dir / "intro"

        self.media_files = []
        if intro_dir.exists():
            # Supported image formats
            image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
            # Supported video formats
            video_exts = {'.mp4', '.mov', '.avi', '.mkv'}

            for file_path in intro_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in (image_exts | video_exts):
                    self.media_files.append(file_path)

            if self.media_files:
                self.current_media_label.config(text=f"Found {len(self.media_files)} media file(s) in intro folder")
            else:
                self.current_media_label.config(text="No media files found in intro folder")

    def browse_media(self):
        """Browse and upload media files"""
        filetypes = [
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.webp"),
            ("Video files", "*.mp4 *.mov *.avi *.mkv"),
            ("All supported", "*.jpg *.jpeg *.png *.bmp *.gif *.webp *.mp4 *.mov *.avi *.mkv"),
            ("All files", "*.*")
        ]

        files = filedialog.askopenfilenames(
            title="Select Player Pictures or Intro Videos",
            filetypes=filetypes,
            parent=self.dialog
        )

        if files:
            try:
                # Create intro directory if it doesn't exist
                athlete_dir = pathlib.Path("athletes") / self.athlete_name
                intro_dir = athlete_dir / "intro"
                intro_dir.mkdir(parents=True, exist_ok=True)

                copied_files = []
                failed_files = []

                for file_path in files:
                    source = pathlib.Path(file_path)
                    destination = intro_dir / source.name

                    try:
                        # Validate source file exists and is readable
                        if not source.exists():
                            failed_files.append(f"{source.name}: File not found")
                            continue

                        if not source.is_file():
                            failed_files.append(f"{source.name}: Not a regular file")
                            continue

                        # Validate destination path (prevent directory traversal)
                        if destination.resolve().parent != intro_dir.resolve():
                            failed_files.append(f"{source.name}: Invalid destination path")
                            continue

                        # Copy file to intro directory with error handling
                        shutil.copy2(source, destination)
                        copied_files.append(destination.name)

                    except PermissionError:
                        failed_files.append(f"{source.name}: Permission denied")
                    except OSError as e:
                        failed_files.append(f"{source.name}: {str(e)}")
                    except Exception as e:
                        failed_files.append(f"{source.name}: Unexpected error - {str(e)}")

                # Show results
                if copied_files and not failed_files:
                    messagebox.showinfo("Upload Success",
                                      f"Successfully copied {len(copied_files)} file(s):\n" +
                                      "\n".join(copied_files))
                elif copied_files and failed_files:
                    messagebox.showwarning("Partial Success",
                                         f"Successfully copied {len(copied_files)} file(s):\n" +
                                         "\n".join(copied_files) +
                                         f"\n\nFailed to copy {len(failed_files)} file(s):\n" +
                                         "\n".join(failed_files))
                elif failed_files:
                    messagebox.showerror("Upload Failed",
                                       f"Failed to copy {len(failed_files)} file(s):\n" +
                                       "\n".join(failed_files))

                # Refresh the media list
                self.scan_existing_media()

            except Exception as e:
                messagebox.showerror("Upload Error", f"Failed to copy files:\n{e}")

    def choose_existing_media(self):
        """Choose from existing media files"""
        if not self.media_files:
            messagebox.showwarning("No Media", "No media files found. Use 'Browse & Upload' to add files.")
            return

        # Create selection dialog
        selection_dialog = tk.Toplevel(self.dialog)
        selection_dialog.title("Choose Intro Media")
        selection_dialog.geometry("400x300")
        selection_dialog.resizable(False, False)
        selection_dialog.transient(self.dialog)
        selection_dialog.grab_set()

        # Center on parent
        selection_dialog.geometry(f"+{self.dialog.winfo_rootx() + 100}+{self.dialog.winfo_rooty() + 100}")

        tk.Label(selection_dialog, text="Select intro media file:",
                font=("Segoe UI", 10, "bold")).pack(pady=10)

        # Listbox for media files
        listbox_frame = tk.Frame(selection_dialog)
        listbox_frame.pack(fill='both', expand=True, padx=20, pady=(0, 10))

        listbox = tk.Listbox(listbox_frame, font=("Segoe UI", 9))
        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical")
        listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)

        # Add media files to listbox
        for media_file in self.media_files:
            file_type = "📷" if media_file.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'} else "🎥"
            listbox.insert(tk.END, f"{file_type} {media_file.name}")

        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Buttons
        btn_frame = tk.Frame(selection_dialog)
        btn_frame.pack(fill='x', padx=20, pady=(0, 10))

        selected_media = [None]  # Use list to modify from inner functions

        def select_media():
            selection = listbox.curselection()
            if selection:
                selected_media[0] = self.media_files[selection[0]]
                self.selected_media_var.set(str(selected_media[0]))
                self.current_media_label.config(text=f"Selected: {selected_media[0].name}")
                selection_dialog.destroy()
            else:
                messagebox.showwarning("No Selection", "Please select a media file.")

        def cancel_selection():
            selection_dialog.destroy()

        tk.Button(btn_frame, text="Select", command=select_media,
                 bg="#4CAF50", fg="white", font=("Segoe UI", 10)).pack(side='right', padx=(5, 0))
        tk.Button(btn_frame, text="Cancel", command=cancel_selection,
                 font=("Segoe UI", 10)).pack(side='right')

    def clear_media_selection(self):
        """Clear the current media selection"""
        self.selected_media_var.set("")
        self.current_media_label.config(text="No media selected")

    def accept(self):
        """Accept the form and return the data"""
        # Validate required fields
        if not self.name_var.get().strip():
            messagebox.showerror("Validation Error", "Player name is required.")
            return

        self.result = {
            "name": self.name_var.get().strip(),
            "title": self.title_var.get().strip(),
            "position": self.position_var.get().strip(),
            "grad_year": self.grad_year_var.get().strip(),
            "club_team": self.club_team_var.get().strip(),
            "high_school": self.high_school_var.get().strip(),
            "height_weight": self.height_weight_var.get().strip(),
            "gpa": self.gpa_var.get().strip(),
            "email": self.email_var.get().strip(),
            "phone": self.phone_var.get().strip(),
            "include_intro": self.include_intro_var.get(),
            "overwrite": self.overwrite_var.get(),
            "selected_media": self.selected_media_var.get() if self.selected_media_var.get() else None
        }
        self.dialog.destroy()

    def save_only(self):
        """Save player information only without proceeding to mark plays"""
        # Validate required fields
        if not self.name_var.get().strip():
            messagebox.showerror("Validation Error", "Player name is required.")
            return

        # Create player data dictionary
        player_data = {
            "name": self.name_var.get().strip(),
            "title": self.title_var.get().strip(),
            "position": self.position_var.get().strip(),
            "grad_year": self.grad_year_var.get().strip(),
            "club_team": self.club_team_var.get().strip(),
            "high_school": self.high_school_var.get().strip(),
            "height_weight": self.height_weight_var.get().strip(),
            "gpa": self.gpa_var.get().strip(),
            "email": self.email_var.get().strip(),
            "phone": self.phone_var.get().strip(),
        }

        # Determine the athlete directory path first
        import pathlib
        import json
        athletes_dir = pathlib.Path.cwd() / "athletes"
        athlete_dir = athletes_dir / self.athlete_name
        project_path = athlete_dir / "project.json"

        # Save to project.json with minimal structure
        selected_media_path = self.selected_media_var.get() if self.selected_media_var.get() else None
        intro_media = None
        if selected_media_path:
            # Convert absolute path to relative path from athlete directory
            media_path = pathlib.Path(selected_media_path)
            try:
                intro_media = str(media_path.relative_to(athlete_dir)) if media_path.exists() else None
            except ValueError:
                # Handle case where media path is not relative to athlete dir
                intro_media = str(media_path.name) if media_path.exists() else None

        project_data = {
            "player": player_data,
            "include_intro": self.include_intro_var.get(),
            "intro_media": intro_media,
            "clips": []
        }

        try:
            # Ensure the athlete directory exists
            athlete_dir.mkdir(parents=True, exist_ok=True)

            # Save the project file
            with open(project_path, 'w') as f:
                json.dump(project_data, f, indent=2)

            messagebox.showinfo("Success",
                f"Player information saved successfully!\n\nFile: {project_path}")

            # Set result to indicate save-only operation
            self.result = "save_only"
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save player information:\n{str(e)}")

    def load_player_profiles(self):
        """Load player profiles from database file"""
        try:
            if self.profiles_db_path.exists():
                with open(self.profiles_db_path, 'r') as f:
                    return json.load(f)
            else:
                return {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load player profiles: {e}")
            return {}

    def save_player_profiles(self):
        """Save player profiles to database file using atomic write"""
        try:
            # Use atomic write: write to temp file, then rename
            temp_fd, temp_path = tempfile.mkstemp(suffix='.json', dir=self.profiles_db_path.parent)
            try:
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(self.player_profiles, f, indent=2)
                # Atomic rename on same filesystem
                os.replace(temp_path, self.profiles_db_path)
            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
        except IOError as e:
            messagebox.showerror("Error", f"Could not save player profiles: {e}")

    def save_current_as_profile(self):
        """Save current form data as a new player profile"""
        name = self.name_var.get().strip()

        # Basic validation
        validation_errors = []
        if not name:
            validation_errors.append("Player name is required")
        elif len(name) > 100:
            validation_errors.append("Player name must be 100 characters or less")

        # Validate email if provided
        email = self.email_var.get().strip()
        if email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                validation_errors.append("Email address is not valid")

        if validation_errors:
            messagebox.showerror("Validation Error",
                               "Please fix the following errors:\n\n" +
                               "\n".join(f"• {error}" for error in validation_errors))
            return

        # Generate unique profile ID using timestamp
        import time
        timestamp = str(int(time.time()))
        profile_id = f"{sanitize_profile_id(name)}_{timestamp}"

        # Create profile data
        profile = {
            "name": name,
            "title": self.title_var.get().strip(),
            "position": self.position_var.get().strip(),
            "grad_year": self.grad_year_var.get().strip(),
            "club_team": self.club_team_var.get().strip(),
            "high_school": self.high_school_var.get().strip(),
            "height_weight": self.height_weight_var.get().strip(),
            "gpa": self.gpa_var.get().strip(),
            "email": self.email_var.get().strip(),
            "phone": self.phone_var.get().strip(),
            "created": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        self.player_profiles[profile_id] = profile
        self.save_player_profiles()

        # Update profile selection dropdown
        if hasattr(self, 'profile_combo'):
            profile_names = ["<New Player>"] + [p["name"] for p in self.player_profiles.values()]
            self.profile_combo['values'] = profile_names

        messagebox.showinfo("Success", f"Profile saved for {name}")

    def load_profile_data(self, profile_id):
        """Load profile data into form fields"""
        if profile_id in self.player_profiles:
            profile = self.player_profiles[profile_id]

            # Don't override the name field if it's already set for this athlete
            if not self.name_var.get().strip():
                self.name_var.set(profile.get("name", ""))

            self.title_var.set(profile.get("title", ""))
            self.position_var.set(profile.get("position", ""))
            self.grad_year_var.set(profile.get("grad_year", ""))
            self.club_team_var.set(profile.get("club_team", ""))
            self.high_school_var.set(profile.get("high_school", ""))
            self.height_weight_var.set(profile.get("height_weight", ""))
            self.gpa_var.set(profile.get("gpa", ""))
            self.email_var.set(profile.get("email", ""))
            self.phone_var.set(profile.get("phone", ""))

            self.selected_profile_id = profile_id

    def on_profile_selected(self, event=None):
        """Handle profile selection from dropdown"""
        if hasattr(self, 'profile_combo'):
            selection = self.profile_combo.get()
            if selection and selection != "<New Player>":
                # Find profile by name
                for profile_id, profile in self.player_profiles.items():
                    if profile["name"] == selection:
                        self.load_profile_data(profile_id)
                        break
            else:
                # Clear form for new player
                self.selected_profile_id = None

    def delete_selected_profile(self):
        """Delete the currently selected profile"""
        if self.selected_profile_id and self.selected_profile_id in self.player_profiles:
            profile_name = self.player_profiles[self.selected_profile_id]["name"]

            if messagebox.askyesno("Confirm Delete",
                                 f"Are you sure you want to delete the profile for {profile_name}?"):
                del self.player_profiles[self.selected_profile_id]
                self.save_player_profiles()

                # Update dropdown
                if hasattr(self, 'profile_combo'):
                    self.profile_combo['values'] = ["<New Player>"] + [p["name"] for p in self.player_profiles.values()]
                    self.profile_combo.set("<New Player>")

                self.selected_profile_id = None
                messagebox.showinfo("Success", f"Profile for {profile_name} has been deleted.")
        else:
            messagebox.showwarning("Warning", "No profile selected for deletion.")

    def cancel(self):
        """Cancel the dialog"""
        self.result = None
        self.dialog.destroy()

class BatchOperationsDialog:
    """Dialog for batch operations on multiple athletes"""

    def __init__(self, parent, refresh_callback):
        self.refresh_callback = refresh_callback

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Batch Operations")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center on parent
        self.dialog.geometry(f"+{parent.winfo_rootx() + 150}+{parent.winfo_rooty() + 100}")

        self.setup_ui()
        self.refresh_athletes()

    def setup_ui(self):
        """Setup batch operations UI"""
        tk.Label(self.dialog, text="Batch Operations", font=("Segoe UI", 14, "bold")).pack(pady=10)

        # Athlete selection
        tk.Label(self.dialog, text="Select athletes to process:", font=("Segoe UI", 10)).pack(anchor='w', padx=10)

        list_frame = tk.Frame(self.dialog)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.athlete_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, height=12)
        scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=self.athlete_listbox.yview)
        self.athlete_listbox.configure(yscrollcommand=scrollbar.set)

        self.athlete_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Selection buttons
        select_frame = tk.Frame(self.dialog)
        select_frame.pack(fill='x', padx=10, pady=5)

        tk.Button(select_frame, text="Select All", command=self.select_all).pack(side='left', padx=5)
        tk.Button(select_frame, text="Select None", command=self.select_none).pack(side='left', padx=5)
        tk.Button(select_frame, text="Select Ready to Render", command=self.select_ready).pack(side='left', padx=5)

        # Options
        options_frame = tk.Frame(self.dialog)
        options_frame.pack(fill='x', padx=10, pady=5)

        self.force_var = tk.BooleanVar()
        tk.Checkbutton(options_frame, text="Force re-render (overwrite existing)",
                      variable=self.force_var).pack(anchor='w')

        self.jobs_var = tk.IntVar(value=1)
        jobs_frame = tk.Frame(options_frame)
        jobs_frame.pack(anchor='w', pady=5)
        tk.Label(jobs_frame, text="Parallel jobs:").pack(side='left')
        tk.Spinbox(jobs_frame, from_=1, to=4, textvariable=self.jobs_var, width=5).pack(side='left', padx=5)

        # Action buttons
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(fill='x', padx=10, pady=10)

        tk.Button(button_frame, text="Render Selected", command=self.render_selected,
                 bg="#4CAF50", fg="white").pack(side='left', padx=5)
        tk.Button(button_frame, text="Close", command=self.dialog.destroy).pack(side='right', padx=5)

    def refresh_athletes(self):
        """Refresh athlete list"""
        self.athlete_listbox.delete(0, tk.END)
        athlete_manager = AthleteManager()
        self.athletes = athlete_manager.discover_athletes()

        for athlete_dir in self.athletes:
            status = athlete_manager.get_athlete_status(athlete_dir)
            status_text = "✓ Complete" if status["has_final"] else ("⚡ Ready" if status["has_project"] else "⚠ Needs work")
            self.athlete_listbox.insert(tk.END, f"{athlete_dir.name} - {status_text}")

    def select_all(self):
        """Select all athletes"""
        self.athlete_listbox.selection_set(0, tk.END)

    def select_none(self):
        """Clear selection"""
        self.athlete_listbox.selection_clear(0, tk.END)

    def select_ready(self):
        """Select athletes ready to render"""
        self.select_none()
        athlete_manager = AthleteManager()
        for i, athlete_dir in enumerate(self.athletes):
            status = athlete_manager.get_athlete_status(athlete_dir)
            if status["has_project"]:
                self.athlete_listbox.selection_set(i)

    def render_selected(self):
        """Render selected athletes using batch_render.py"""
        selected = self.athlete_listbox.curselection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select athletes to render.")
            return

        athlete_names = [self.athletes[i].name for i in selected]

        cmd = [sys.executable, "batch_render.py", "--names"] + athlete_names
        if self.force_var.get():
            cmd.append("--force")
        cmd.extend(["--jobs", str(self.jobs_var.get())])

        self.dialog.destroy()

        # Run batch render with progress
        progress = ProgressDialog(self.dialog.master, "Batch Rendering",
                                 f"Rendering {len(athlete_names)} athletes")

        def run():
            try:
                progress.update_status(f"Running: {' '.join(cmd)}")
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                progress.process = process

                stdout, stderr = process.communicate()

                if not progress.cancelled:
                    progress.close()
                    if process.returncode == 0:
                        messagebox.showinfo("Success", f"Batch rendering completed!\n\nProcessed {len(athlete_names)} athletes.")
                    else:
                        messagebox.showerror("Error", f"Batch rendering failed:\n{stderr}")
                    self.refresh_callback()

            except Exception as e:
                if not progress.cancelled:
                    progress.close()
                    messagebox.showerror("Error", f"Failed to run batch render: {e}")

        threading.Thread(target=run, daemon=True).start()


class ProfileManagementDialog:
    """Dialog for standalone player profile management"""

    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Manage Player Profiles")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center on parent
        self.dialog.geometry(f"+{parent.winfo_rootx() + 100}+{parent.winfo_rooty() + 50}")

        # Load profiles
        self.profiles_db_path = pathlib.Path.cwd() / "players_database.json"
        self.player_profiles = self.load_player_profiles()

        self.setup_ui()
        self.refresh_profiles_list()

        # Wait for dialog to complete
        self.dialog.wait_window()

    def setup_ui(self):
        """Setup the profile management UI"""
        main_frame = tk.Frame(self.dialog)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # Title
        tk.Label(main_frame, text="Player Profile Management",
                font=("Segoe UI", 16, "bold")).pack(pady=(0, 15))

        # Create layout: list on left, details on right
        content_frame = tk.Frame(main_frame)
        content_frame.pack(fill='both', expand=True)

        # Left side - Profile list
        left_frame = tk.Frame(content_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        tk.Label(left_frame, text="Saved Profiles:", font=("Segoe UI", 12, "bold")).pack(anchor='w')

        # Profile listbox with scrollbar
        list_frame = tk.Frame(left_frame)
        list_frame.pack(fill='both', expand=True, pady=(5, 0))

        self.profiles_listbox = tk.Listbox(list_frame, font=("Segoe UI", 10))
        scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=self.profiles_listbox.yview)
        self.profiles_listbox.configure(yscrollcommand=scrollbar.set)
        self.profiles_listbox.bind('<<ListboxSelect>>', self.on_profile_selected)

        self.profiles_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Profile action buttons
        profile_btn_frame = tk.Frame(left_frame)
        profile_btn_frame.pack(fill='x', pady=(10, 0))

        tk.Button(profile_btn_frame, text="New Profile",
                 command=self.new_profile).pack(side='left', padx=(0, 5))
        tk.Button(profile_btn_frame, text="Delete Selected",
                 command=self.delete_profile).pack(side='left', padx=(0, 5))
        tk.Button(profile_btn_frame, text="Duplicate",
                 command=self.duplicate_profile).pack(side='left')

        # Right side - Profile details
        right_frame = tk.Frame(content_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))

        tk.Label(right_frame, text="Profile Details:", font=("Segoe UI", 12, "bold")).pack(anchor='w')

        # Create form container (no scrollbar for now to avoid layout issues)
        form_container = tk.Frame(right_frame)
        form_container.pack(fill='both', expand=True, pady=(5, 0))

        # Create scrollable frame for form fields
        canvas = tk.Canvas(form_container, height=350)
        details_scrollbar = tk.Scrollbar(form_container, orient="vertical", command=canvas.yview)
        self.details_frame = tk.Frame(canvas)

        self.details_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.details_frame, anchor="nw")
        canvas.configure(yscrollcommand=details_scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True)
        details_scrollbar.pack(side='right', fill='y')

        # Form variables
        self.name_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.position_var = tk.StringVar()
        self.grad_year_var = tk.StringVar()
        self.club_team_var = tk.StringVar()
        self.high_school_var = tk.StringVar()
        self.height_weight_var = tk.StringVar()
        self.gpa_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.phone_var = tk.StringVar()

        # Form fields
        self.create_form_fields()

        # Detail action buttons (placed outside the scrollable area)
        detail_btn_frame = tk.Frame(right_frame)
        detail_btn_frame.pack(fill='x', pady=(10, 0))

        self.save_btn = tk.Button(detail_btn_frame, text="Save Changes",
                                 command=self.save_profile, bg="#4CAF50", fg="white",
                                 font=("Segoe UI", 10, "bold"))
        self.save_btn.pack(side='left', padx=(0, 5))

        self.revert_btn = tk.Button(detail_btn_frame, text="Revert Changes",
                                   command=self.revert_changes, font=("Segoe UI", 10))
        self.revert_btn.pack(side='left')

        # Bottom buttons
        bottom_frame = tk.Frame(main_frame)
        bottom_frame.pack(fill='x', pady=(15, 0))

        tk.Button(bottom_frame, text="Close",
                 command=self.dialog.destroy).pack(side='right')

        # Initially disable form if no profiles
        self.current_profile_id = None
        self.enable_form(len(self.player_profiles) > 0)

    def create_form_fields(self):
        """Create the profile detail form fields"""
        fields = [
            ("Player Name:", self.name_var, True),
            ("Title (optional):", self.title_var, False),
            ("Position:", self.position_var, False),
            ("Graduation Year:", self.grad_year_var, False),
            ("Club Team:", self.club_team_var, False),
            ("High School:", self.high_school_var, False),
            ("Height/Weight:", self.height_weight_var, False),
            ("GPA:", self.gpa_var, False),
            ("Email:", self.email_var, False),
            ("Phone:", self.phone_var, False),
        ]

        self.form_entries = {}

        for label_text, var, required in fields:
            field_frame = tk.Frame(self.details_frame)
            field_frame.pack(fill='x', pady=5)

            label = tk.Label(field_frame, text=label_text, font=("Segoe UI", 10))
            if required:
                label.config(font=("Segoe UI", 10, "bold"))
            label.pack(anchor='w')

            entry = tk.Entry(field_frame, textvariable=var, font=("Segoe UI", 10))
            entry.pack(fill='x', pady=2)

            if required:
                entry.config(highlightbackground="#007ACC", highlightthickness=1)

            self.form_entries[label_text] = entry

    def enable_form(self, enabled):
        """Enable or disable the form fields and action buttons"""
        state = 'normal' if enabled else 'disabled'

        # Enable/disable form entries
        for entry in self.form_entries.values():
            entry.config(state=state)

        # Enable/disable action buttons
        if hasattr(self, 'save_btn'):
            self.save_btn.config(state=state)
        if hasattr(self, 'revert_btn'):
            self.revert_btn.config(state=state)

    def load_player_profiles(self):
        """Load player profiles from database file"""
        try:
            if self.profiles_db_path.exists():
                with open(self.profiles_db_path, 'r') as f:
                    return json.load(f)
            else:
                return {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load player profiles: {e}")
            return {}

    def save_player_profiles(self):
        """Save player profiles to database file using atomic write"""
        try:
            # Use atomic write: write to temp file, then rename
            temp_fd, temp_path = tempfile.mkstemp(suffix='.json', dir=self.profiles_db_path.parent)
            try:
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(self.player_profiles, f, indent=2)
                # Atomic rename on same filesystem
                os.replace(temp_path, self.profiles_db_path)
            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
        except IOError as e:
            messagebox.showerror("Error", f"Could not save player profiles: {e}")

    def refresh_profiles_list(self):
        """Refresh the profiles listbox"""
        self.profiles_listbox.delete(0, tk.END)
        for profile_id, profile in self.player_profiles.items():
            display_name = f"{profile['name']} ({profile.get('position', 'No Position')})"
            self.profiles_listbox.insert(tk.END, display_name)

    def on_profile_selected(self, event=None):
        """Handle profile selection from listbox"""
        selection = self.profiles_listbox.curselection()
        if not selection:
            return

        # Get profile by index
        profile_ids = list(self.player_profiles.keys())
        if selection[0] < len(profile_ids):
            self.current_profile_id = profile_ids[selection[0]]
            self.load_profile_details(self.current_profile_id)
            self.enable_form(True)

    def load_profile_details(self, profile_id):
        """Load profile data into form fields"""
        if profile_id in self.player_profiles:
            profile = self.player_profiles[profile_id]

            self.name_var.set(profile.get("name", ""))
            self.title_var.set(profile.get("title", ""))
            self.position_var.set(profile.get("position", ""))
            self.grad_year_var.set(profile.get("grad_year", ""))
            self.club_team_var.set(profile.get("club_team", ""))
            self.high_school_var.set(profile.get("high_school", ""))
            self.height_weight_var.set(profile.get("height_weight", ""))
            self.gpa_var.set(profile.get("gpa", ""))
            self.email_var.set(profile.get("email", ""))
            self.phone_var.set(profile.get("phone", ""))

    def new_profile(self):
        """Create a new blank profile"""
        # Clear form
        for var in [self.name_var, self.title_var, self.position_var, self.grad_year_var,
                   self.club_team_var, self.high_school_var, self.height_weight_var,
                   self.gpa_var, self.email_var, self.phone_var]:
            var.set("")

        self.current_profile_id = None
        self.enable_form(True)

        # Focus on name field
        self.form_entries["Player Name:"].focus_set()

    def validate_profile_data(self):
        """Validate profile data and return validation errors"""
        errors = []

        name = self.name_var.get().strip()
        if not name:
            errors.append("Player name is required")
        elif len(name) > 100:
            errors.append("Player name must be 100 characters or less")

        # Validate graduation year if provided
        grad_year = self.grad_year_var.get().strip()
        if grad_year:
            try:
                year = int(grad_year)
                import datetime
                current_year = datetime.datetime.now().year
                if year < 1900 or year > current_year + 20:
                    errors.append("Graduation year must be between 1900 and " + str(current_year + 20))
            except ValueError:
                errors.append("Graduation year must be a valid number")

        # Validate email if provided
        email = self.email_var.get().strip()
        if email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                errors.append("Email address is not valid")

        # Validate GPA if provided
        gpa = self.gpa_var.get().strip()
        if gpa:
            try:
                gpa_float = float(gpa)
                if gpa_float < 0 or gpa_float > 4.0:
                    errors.append("GPA must be between 0.0 and 4.0")
            except ValueError:
                errors.append("GPA must be a valid number")

        return errors

    def save_profile(self):
        """Save the current profile"""
        # Validate input data
        validation_errors = self.validate_profile_data()
        if validation_errors:
            messagebox.showerror("Validation Error",
                               "Please fix the following errors:\n\n" +
                               "\n".join(f"• {error}" for error in validation_errors))
            return

        name = self.name_var.get().strip()

        # Generate profile ID if new profile
        if self.current_profile_id is None:
            import time
            timestamp = str(int(time.time()))
            profile_id = f"{sanitize_profile_id(name)}_{timestamp}"
            self.current_profile_id = profile_id

        # Create profile data
        profile = {
            "name": name,
            "title": self.title_var.get().strip(),
            "position": self.position_var.get().strip(),
            "grad_year": self.grad_year_var.get().strip(),
            "club_team": self.club_team_var.get().strip(),
            "high_school": self.high_school_var.get().strip(),
            "height_weight": self.height_weight_var.get().strip(),
            "gpa": self.gpa_var.get().strip(),
            "email": self.email_var.get().strip(),
            "phone": self.phone_var.get().strip(),
            "created": self.player_profiles.get(self.current_profile_id, {}).get("created",
                                                                                time.strftime("%Y-%m-%d %H:%M:%S")),
            "modified": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        self.player_profiles[self.current_profile_id] = profile
        self.save_player_profiles()
        self.refresh_profiles_list()

        # Select the saved profile in the list
        profile_ids = list(self.player_profiles.keys())
        if self.current_profile_id in profile_ids:
            index = profile_ids.index(self.current_profile_id)
            self.profiles_listbox.selection_set(index)

        messagebox.showinfo("Success", f"Profile saved for {name}")

    def delete_profile(self):
        """Delete the selected profile"""
        selection = self.profiles_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a profile to delete.")
            return

        profile_ids = list(self.player_profiles.keys())
        profile_id = profile_ids[selection[0]]
        profile_name = self.player_profiles[profile_id]["name"]

        if messagebox.askyesno("Confirm Delete",
                              f"Are you sure you want to delete the profile for {profile_name}?"):
            del self.player_profiles[profile_id]
            self.save_player_profiles()
            self.refresh_profiles_list()

            # Clear form and disable if no profiles left
            if not self.player_profiles:
                self.new_profile()
                self.enable_form(False)

            messagebox.showinfo("Success", f"Profile for {profile_name} has been deleted.")

    def duplicate_profile(self):
        """Duplicate the selected profile"""
        selection = self.profiles_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a profile to duplicate.")
            return

        profile_ids = list(self.player_profiles.keys())
        original_id = profile_ids[selection[0]]
        original_profile = self.player_profiles[original_id].copy()

        # Create new profile with modified name
        original_name = original_profile["name"]
        new_name = f"{original_name} (Copy)"
        import time
        timestamp = str(int(time.time()))
        new_id = f"{new_sanitize_profile_id(name)}_{timestamp}"

        original_profile["name"] = new_name
        original_profile["created"] = time.strftime("%Y-%m-%d %H:%M:%S")
        original_profile["modified"] = time.strftime("%Y-%m-%d %H:%M:%S")

        self.player_profiles[new_id] = original_profile
        self.save_player_profiles()
        self.refresh_profiles_list()

        messagebox.showinfo("Success", f"Profile duplicated as '{new_name}'")

    def revert_changes(self):
        """Revert form to last saved state"""
        if self.current_profile_id and self.current_profile_id in self.player_profiles:
            self.load_profile_details(self.current_profile_id)
        else:
            self.new_profile()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="SoccerHype GUI - Unified highlight video creator")
    args = parser.parse_args()

    try:
        app = SoccerHypeGUI()
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        messagebox.showerror("Error", f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()