#!/usr/bin/env python3
"""
SoccerHype GUI - Unified interface for athlete highlight video creation
Main launcher that provides a guided workflow for all video processing tasks.
"""

import argparse
import json
import pathlib
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from typing import Dict, List, Optional
import time

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

ROOT = pathlib.Path.cwd()
ATHLETES = ROOT / "athletes"

class AthleteManager:
    """Handles athlete data and folder management"""

    def __init__(self):
        if ERROR_HANDLING_AVAILABLE:
            self.error_handler = ErrorHandler("athlete_manager")
        else:
            self.error_handler = None

    @error_handler("Discovering athletes", show_dialog=False)
    def discover_athletes(self) -> List[pathlib.Path]:
        """Find all athlete directories"""
        if ERROR_HANDLING_AVAILABLE:
            ValidationHelper.validate_directory(ATHLETES, create_if_missing=True)

        if not ATHLETES.exists():
            return []
        return sorted([p for p in ATHLETES.iterdir() if p.is_dir()])

    @error_handler("Checking athlete status", show_dialog=False)
    def get_athlete_status(self, athlete_dir: pathlib.Path) -> Dict[str, bool]:
        """Check completion status of workflow steps"""
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

    @error_handler("Creating athlete folder")
    def create_athlete(self, name: str) -> pathlib.Path:
        """Create new athlete folder structure"""
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

    @error_handler("Refreshing athletes list", show_dialog=False)
    def refresh_athletes(self):
        """Refresh the athletes list"""
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
            subprocess.run(["xdg-open", str(athlete_dir)], check=True)
        except subprocess.CalledProcessError:
            messagebox.showerror("Error", f"Could not open folder: {athlete_dir}")

    def mark_plays(self):
        """Launch mark_play.py for selected athlete"""
        athlete_dir = self.get_selected_athlete()
        if not athlete_dir:
            return

        status = AthleteManager.get_athlete_status(athlete_dir)
        if not status["has_clips"]:
            messagebox.showwarning("No Clips", f"No clips found in {athlete_dir.name}/clips_in/\n\nAdd video clips first.")
            return

        self.run_script_async("mark_play.py", ["--dir", str(athlete_dir)],
                             "Marking Plays", f"Launching play marking for {athlete_dir.name}")

    def reorder_clips(self):
        """Launch reorder_clips.py for selected athlete"""
        athlete_dir = self.get_selected_athlete()
        if not athlete_dir:
            return

        status = AthleteManager.get_athlete_status(athlete_dir)
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

        status = AthleteManager.get_athlete_status(athlete_dir)
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
            subprocess.run(["xdg-open", str(final_video)], check=True)
        except subprocess.CalledProcessError:
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
        self.athletes = AthleteManager.discover_athletes()

        for athlete_dir in self.athletes:
            status = AthleteManager.get_athlete_status(athlete_dir)
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
        for i, athlete_dir in enumerate(self.athletes):
            status = AthleteManager.get_athlete_status(athlete_dir)
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