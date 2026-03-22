"""Batch operations dialog for the SoccerHype GUI."""

import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from gui.athletes import AthleteManager
from gui.dialogs import ProgressDialog


class BatchOperationsDialog:
    """Dialog for batch operations on multiple athletes"""

    def __init__(self, parent, refresh_callback):
        self.refresh_callback = refresh_callback

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Batch Operations")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.dialog.geometry(f"+{parent.winfo_rootx() + 150}+{parent.winfo_rooty() + 100}")

        self.setup_ui()
        self.refresh_athletes()

    def setup_ui(self):
        tk.Label(self.dialog, text="Batch Operations", font=("Segoe UI", 14, "bold")).pack(pady=10)

        tk.Label(self.dialog, text="Select athletes to process:", font=("Segoe UI", 10)).pack(anchor='w', padx=10)

        list_frame = tk.Frame(self.dialog)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.athlete_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, height=12)
        scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=self.athlete_listbox.yview)
        self.athlete_listbox.configure(yscrollcommand=scrollbar.set)

        self.athlete_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        select_frame = tk.Frame(self.dialog)
        select_frame.pack(fill='x', padx=10, pady=5)

        tk.Button(select_frame, text="Select All", command=self.select_all).pack(side='left', padx=5)
        tk.Button(select_frame, text="Select None", command=self.select_none).pack(side='left', padx=5)
        tk.Button(select_frame, text="Select Ready to Render", command=self.select_ready).pack(side='left', padx=5)

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

        button_frame = tk.Frame(self.dialog)
        button_frame.pack(fill='x', padx=10, pady=10)

        tk.Button(button_frame, text="Render Selected", command=self.render_selected,
                 bg="#4CAF50", fg="white").pack(side='left', padx=5)
        tk.Button(button_frame, text="Close", command=self.dialog.destroy).pack(side='right', padx=5)

    def refresh_athletes(self):
        self.athlete_listbox.delete(0, tk.END)
        athlete_manager = AthleteManager()
        self.athletes = athlete_manager.discover_athletes()

        for athlete_dir in self.athletes:
            status = athlete_manager.get_athlete_status(athlete_dir)
            if status["has_final"]:
                status_text = "Complete"
            elif status["all_clips_marked"]:
                status_text = "Ready"
            elif status["marked_count"] > 0:
                status_text = f"{status['marked_count']}/{status['clips_count']} marked"
            else:
                status_text = "Needs work"
            self.athlete_listbox.insert(tk.END, f"{athlete_dir.name} - {status_text}")

    def select_all(self):
        self.athlete_listbox.selection_set(0, tk.END)

    def select_none(self):
        self.athlete_listbox.selection_clear(0, tk.END)

    def select_ready(self):
        self.select_none()
        athlete_manager = AthleteManager()
        for i, athlete_dir in enumerate(self.athletes):
            status = athlete_manager.get_athlete_status(athlete_dir)
            if status["all_clips_marked"]:
                self.athlete_listbox.selection_set(i)

    def render_selected(self):
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
