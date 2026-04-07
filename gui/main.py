"""Main SoccerHype GUI application window."""

import json
import pathlib
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from version import __version__
from clip_sync import is_clip_marked
from utils.structure import (
    is_v2_structure,
    get_athlete_profile,
    get_project_data,
    clone_project,
)
from gui.utils import ATHLETES, _VIDEO_EXTS, _extract_video_frame, ERROR_HANDLING_AVAILABLE
from gui.athletes import AthleteManager
from gui.dialogs import ProgressDialog, ProjectSelectionDialog, PlayerInfoDialog, QuickStartWizard
from gui.batch import BatchOperationsDialog
from gui.profiles import ProfileManagementDialog

if ERROR_HANDLING_AVAILABLE:
    from utils.error_handling import ErrorHandler, initialize_error_handling


class SoccerHypeGUI:
    """Main GUI application"""

    def __init__(self):
        if ERROR_HANDLING_AVAILABLE:
            initialize_error_handling()
            self.error_handler = ErrorHandler("soccerhype_gui")
        else:
            self.error_handler = None

        self.root = tk.Tk()
        self.root.title(f"SoccerHype v{__version__} - Athlete Highlight Video Creator")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)

        self.athlete_manager = AthleteManager()

        ATHLETES.mkdir(exist_ok=True)

        self.setup_ui()
        self.refresh_athletes()

    def setup_ui(self):
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

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        title_frame = tk.Frame(main_frame)
        title_frame.pack(fill='x', pady=(0, 20))

        tk.Label(title_frame, text="SoccerHype", font=("Segoe UI", 20, "bold")).pack()
        tk.Label(title_frame, text="Create professional athlete highlight videos with red spotlight tracking",
                font=("Segoe UI", 10)).pack()

        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(0, 10))

        tk.Button(button_frame, text="New Athlete", command=self.new_athlete,
                 bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold")).pack(side='left', padx=(0, 10))
        tk.Button(button_frame, text="New Project", command=self.new_project,
                 font=("Segoe UI", 10)).pack(side='left', padx=(0, 10))
        tk.Button(button_frame, text="Refresh", command=self.refresh_athletes,
                 font=("Segoe UI", 10)).pack(side='left', padx=(0, 10))
        tk.Button(button_frame, text="Quick Start", command=self.quick_start_wizard,
                 font=("Segoe UI", 10, "bold"), bg="#2196F3", fg="white").pack(side='left', padx=(0, 10))
        tk.Button(button_frame, text="Batch Operations", command=self.batch_operations,
                 font=("Segoe UI", 10)).pack(side='right')

        list_frame = tk.Frame(main_frame)
        list_frame.pack(fill='both', expand=True)

        tk.Label(list_frame, text="Projects", font=("Segoe UI", 12, "bold")).pack(anchor='w')

        columns = ("Athlete", "Project", "Status", "Clips", "Marked", "Rendered")
        self.athlete_tree = ttk.Treeview(list_frame, columns=columns, show='tree headings', height=15)

        # Tree column (#0) holds the thumbnail image
        self.athlete_tree.heading("#0", text="")
        self.athlete_tree.column("#0", width=90, minwidth=90, stretch=False)

        self.athlete_tree.heading("Athlete", text="Athlete")
        self.athlete_tree.heading("Project", text="Project")
        self.athlete_tree.heading("Status", text="Status")
        self.athlete_tree.heading("Clips", text="Clips")
        self.athlete_tree.heading("Marked", text="Marked")
        self.athlete_tree.heading("Rendered", text="Rendered")

        self.athlete_tree.column("Athlete", width=150)
        self.athlete_tree.column("Project", width=120)
        self.athlete_tree.column("Status", width=130)
        self.athlete_tree.column("Clips", width=60, anchor='center')
        self.athlete_tree.column("Marked", width=80, anchor='center')
        self.athlete_tree.column("Rendered", width=70, anchor='center')

        # Keep references to PhotoImage objects so they aren't garbage-collected
        self._thumbnail_images: dict[str, tk.PhotoImage] = {}
        self._placeholder_image: Optional[tk.PhotoImage] = None

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.athlete_tree.yview)
        self.athlete_tree.configure(yscrollcommand=scrollbar.set)

        self.athlete_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self.athlete_tree.bind("<Double-1>", self.open_athlete)

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Open Folder", command=self.open_folder)
        self.context_menu.add_command(label="Set Profile", command=self.set_profile)
        self.context_menu.add_command(label="Choose Slate...", command=self.choose_slate_template)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Order Clips", command=self.reorder_clips)
        self.context_menu.add_command(label="Mark Plays", command=self.mark_plays)
        self.context_menu.add_command(label="Render Video", command=self.render_video)
        self.context_menu.add_command(label="View Final Video", command=self.view_final)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete Project...", command=self.delete_project)

        self.athlete_tree.bind("<Button-3>", self.show_context_menu)

        action_frame = tk.Frame(main_frame)
        action_frame.pack(fill='x', pady=(10, 0))

        tk.Button(action_frame, text="Open Folder", command=self.open_folder,
                 font=("Segoe UI", 9)).pack(side='left', padx=(0, 5))
        tk.Button(action_frame, text="Set Profile", command=self.set_profile,
                 font=("Segoe UI", 9)).pack(side='left', padx=(0, 5))
        tk.Button(action_frame, text="Order Clips", command=self.reorder_clips,
                 font=("Segoe UI", 9)).pack(side='left', padx=(0, 5))
        tk.Button(action_frame, text="Mark Plays", command=self.mark_plays,
                 font=("Segoe UI", 9)).pack(side='left', padx=(0, 5))
        tk.Button(action_frame, text="Render Video", command=self.render_video,
                 font=("Segoe UI", 9)).pack(side='left', padx=(0, 5))
        tk.Button(action_frame, text="View Final Video", command=self.view_final,
                 font=("Segoe UI", 9)).pack(side='right')

    def refresh_athletes(self):
        try:
            self._refresh_athletes_impl()
        except Exception as e:
            if ERROR_HANDLING_AVAILABLE and self.error_handler:
                self.error_handler.handle_error(e, "Refreshing athletes list", show_dialog=False)
            else:
                print(f"Error refreshing athletes: {e}")

    def _refresh_athletes_impl(self):
        for item in self.athlete_tree.get_children():
            self.athlete_tree.delete(item)

        athletes = self.athlete_manager.discover_athletes()
        if not athletes:
            self.athlete_tree.insert("", 'end', iid="_empty_",
                                    values=("(No projects)", "Click 'New Athlete' to get started", "", "", "", ""))
            return

        any_projects = False

        for athlete_dir in athletes:
            v2 = is_v2_structure(athlete_dir)
            if v2:
                profile = get_athlete_profile(athlete_dir)
                has_profile = bool(profile.get("name", "").strip())
            else:
                project_json = athlete_dir / "project.json"
                if project_json.exists():
                    try:
                        data = json.loads(project_json.read_text())
                        has_profile = bool(data.get("player", {}).get("name", "").strip())
                    except (IOError, json.JSONDecodeError):
                        has_profile = False
                else:
                    has_profile = False

            projects = self.athlete_manager.discover_projects(athlete_dir)

            if not projects:
                row_id = f"{athlete_dir.name}|_no_project_"
                self.athlete_tree.insert("", 'end', iid=row_id,
                                        values=(athlete_dir.name, "(no projects)", "Needs project", "X", "X", "X"))
                any_projects = True
                continue

            for project_dir in projects:
                any_projects = True
                status = self.athlete_manager.get_project_status(project_dir)

                project_name = project_dir.name if v2 else "(default)"
                row_id = f"{athlete_dir.name}|{project_name}"

                if not status["has_clips"]:
                    workflow_status = "Needs clips"
                elif not has_profile:
                    workflow_status = "Needs profile"
                elif status["needs_marking"]:
                    workflow_status = "Ready to mark"
                elif status["needs_rendering"]:
                    workflow_status = "Ready to render"
                elif status["has_final"]:
                    workflow_status = "Complete"
                else:
                    workflow_status = "Unknown"

                clips_status = "Y" if status["has_clips"] else "X"
                if status["all_clips_marked"]:
                    marked_status = "Y"
                elif status["marked_count"] > 0:
                    marked_status = f"{status['marked_count']}/{status['clips_count']}"
                else:
                    marked_status = "X"
                rendered_status = "Y" if status["has_final"] else "X"

                self.athlete_tree.insert("", 'end', iid=row_id, values=(
                    athlete_dir.name, project_name, workflow_status,
                    clips_status, marked_status, rendered_status
                ))

        if not any_projects:
            self.athlete_tree.insert("", 'end', iid="_empty_",
                                    values=("(No projects)", "Click 'New Athlete' to get started", "", "", "", ""))
            return

        # Load thumbnails in background
        self._load_thumbnails_async()

    def _get_placeholder_image(self) -> tk.PhotoImage:
        """Create a small gray placeholder PhotoImage (80x60)."""
        if self._placeholder_image is not None:
            return self._placeholder_image
        import base64
        w, h = 80, 60
        pixels = bytes([180, 180, 180]) * (w * h)
        header = f"P6\n{w} {h}\n255\n".encode()
        self._placeholder_image = tk.PhotoImage(data=base64.b64encode(header + pixels))
        return self._placeholder_image

    def _get_thumbnail_path(self, project_dir: pathlib.Path) -> pathlib.Path:
        """Return the cached thumbnail path for a project."""
        return project_dir / "work" / "thumb_preview.png"

    def _generate_thumbnail(self, project_dir: pathlib.Path) -> Optional[pathlib.Path]:
        """Extract a frame from the first clip and save as a small PNG thumbnail."""
        thumb_path = self._get_thumbnail_path(project_dir)

        clips_in = project_dir / "clips_in"
        if not clips_in.exists():
            return None

        video_exts = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}
        clips = sorted(f for f in clips_in.iterdir() if f.suffix.lower() in video_exts)
        if not clips:
            return None

        # Use cached thumbnail if it's newer than the first clip
        if (thumb_path.exists() and thumb_path.stat().st_size > 0
                and thumb_path.stat().st_mtime >= clips[0].stat().st_mtime):
            return thumb_path

        try:
            thumb_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["ffmpeg", "-y", "-ss", "1", "-i", str(clips[0]),
                 "-frames:v", "1", "-vf", "scale=80:60:force_original_aspect_ratio=decrease,pad=80:60:(ow-iw)/2:(oh-ih)/2:color=gray",
                 str(thumb_path)],
                capture_output=True, timeout=15,
            )
            if thumb_path.exists() and thumb_path.stat().st_size > 0:
                return thumb_path
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    def _load_thumbnails_async(self):
        """Generate thumbnails in a background thread and update the Treeview."""
        # Collect row_id -> project_dir mappings
        items = []
        for row_id in self.athlete_tree.get_children():
            if row_id == "_empty_" or row_id.endswith("|_no_project_"):
                continue
            if "|" not in row_id:
                continue
            athlete_name, project_name = row_id.split("|", 1)
            athlete_dir = ATHLETES / athlete_name
            if project_name == "(default)":
                project_dir = athlete_dir
            else:
                project_dir = athlete_dir / "projects" / project_name
            if project_dir.exists():
                items.append((row_id, project_dir))

        if not items:
            return

        def generate_all():
            results = []
            for row_id, project_dir in items:
                thumb = self._generate_thumbnail(project_dir)
                results.append((row_id, thumb))
            # Schedule UI update on the main thread
            self.root.after(0, lambda: self._apply_thumbnails(results))

        threading.Thread(target=generate_all, daemon=True).start()

    def _apply_thumbnails(self, results: list):
        """Apply generated thumbnails to Treeview rows (must be called on main thread)."""
        for row_id, thumb_path in results:
            try:
                if not self.athlete_tree.exists(row_id):
                    continue
                if thumb_path and thumb_path.exists():
                    img = tk.PhotoImage(file=str(thumb_path))
                    self._thumbnail_images[row_id] = img
                    self.athlete_tree.item(row_id, image=img)
                else:
                    placeholder = self._get_placeholder_image()
                    self.athlete_tree.item(row_id, image=placeholder)
            except Exception:
                pass

    def get_selected_athlete(self) -> Optional[pathlib.Path]:
        athlete_dir, _ = self.get_selected_project()
        return athlete_dir

    def _get_selected_athlete_silent(self) -> Optional[pathlib.Path]:
        selection = self.athlete_tree.selection()
        if not selection:
            return None
        row_id = selection[0]
        if row_id == "_empty_":
            return None
        if row_id.endswith("|_no_project_"):
            athlete_name = row_id.rsplit("|", 1)[0]
            return ATHLETES / athlete_name
        if "|" not in row_id:
            return None
        athlete_name = row_id.split("|", 1)[0]
        athlete_dir = ATHLETES / athlete_name
        return athlete_dir if athlete_dir.exists() else None

    def get_selected_project(self) -> tuple[Optional[pathlib.Path], Optional[pathlib.Path]]:
        selection = self.athlete_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a project first.")
            return None, None

        row_id = selection[0]

        if row_id == "_empty_" or row_id.endswith("|_no_project_"):
            if row_id.endswith("|_no_project_"):
                athlete_name = row_id.rsplit("|", 1)[0]
                return ATHLETES / athlete_name, None
            return None, None

        if "|" not in row_id:
            return None, None

        athlete_name, project_name = row_id.split("|", 1)
        athlete_dir = ATHLETES / athlete_name

        if not athlete_dir.exists():
            return None, None

        if project_name == "(default)":
            project_dir = athlete_dir
        else:
            project_dir = athlete_dir / "projects" / project_name

        return athlete_dir, project_dir

    def show_context_menu(self, event):
        row_id = self.athlete_tree.identify_row(event.y)
        if row_id and row_id != "_empty_":
            self.athlete_tree.selection_set(row_id)
            self.context_menu.post(event.x_root, event.y_root)

    def new_athlete(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("New Athlete")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

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
                messagebox.showinfo("Success",
                    f"Created athlete: {athlete_dir.name}\n\n"
                    f"A 'Default' project was created.\n\n"
                    f"Next step: Add video clips to:\n"
                    f"{athlete_dir}/projects/Default/clips_in/")

        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Create", command=create, bg="#4CAF50", fg="white").pack(side='left', padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side='left', padx=5)

        dialog.bind('<Return>', lambda e: create())

    def new_project(self):
        all_athletes = self.athlete_manager.discover_athletes()
        if not all_athletes:
            messagebox.showerror("No Athletes", "No athletes found. Please create an athlete first.")
            return

        preselected_athlete = self._get_selected_athlete_silent()

        create_dialog = tk.Toplevel(self.root)
        create_dialog.title("New Project")
        create_dialog.resizable(False, False)
        create_dialog.transient(self.root)
        create_dialog.grab_set()
        create_dialog.geometry(f"+{self.root.winfo_rootx() + 150}+{self.root.winfo_rooty() + 100}")

        athlete_frame = tk.LabelFrame(create_dialog, text="Athlete", font=("Segoe UI", 9))
        athlete_frame.pack(fill='x', padx=10, pady=10)

        athlete_names = [a.name for a in all_athletes]
        athlete_var = tk.StringVar()
        athlete_combo = ttk.Combobox(athlete_frame, textvariable=athlete_var,
                                     values=athlete_names, state='readonly',
                                     font=("Segoe UI", 9))
        athlete_combo.pack(fill='x', padx=5, pady=5)

        if preselected_athlete and preselected_athlete.name in athlete_names:
            athlete_combo.set(preselected_athlete.name)
        else:
            athlete_combo.set(athlete_names[0])

        clone_source_var = tk.StringVar(value="")
        method_var = tk.StringVar(value="scratch")

        method_frame = tk.LabelFrame(create_dialog, text="Creation Method", font=("Segoe UI", 9))
        tk.Radiobutton(method_frame, text="Start from scratch (empty project)",
                      variable=method_var, value="scratch",
                      font=("Segoe UI", 9)).pack(anchor='w', padx=5, pady=2)
        tk.Radiobutton(method_frame, text="Clone existing project (copy clips and marks)",
                      variable=method_var, value="clone",
                      font=("Segoe UI", 9)).pack(anchor='w', padx=5, pady=2)

        clone_frame = tk.LabelFrame(create_dialog, text="Clone From", font=("Segoe UI", 9))
        clone_combo = ttk.Combobox(clone_frame, textvariable=clone_source_var,
                                   state='disabled', font=("Segoe UI", 9))
        clone_combo.pack(fill='x', padx=5, pady=5)

        def on_method_change(*args):
            if method_var.get() == "clone":
                clone_combo.config(state='readonly')
            else:
                clone_combo.config(state='disabled')

        method_var.trace_add('write', on_method_change)

        def update_clone_options(*args):
            selected_name = athlete_var.get()
            if not selected_name:
                return
            athlete_dir = ATHLETES / selected_name
            is_v2 = self.athlete_manager.is_v2_athlete(athlete_dir)
            existing_projects = self.athlete_manager.discover_projects(athlete_dir) if is_v2 else []
            has_cloneable = len(existing_projects) > 0

            if has_cloneable:
                method_frame.pack(fill='x', padx=10, pady=5, after=athlete_frame)
                clone_frame.pack(fill='x', padx=10, pady=5, after=method_frame)
                clone_combo.config(values=[p.name for p in existing_projects])
                clone_combo.set(existing_projects[0].name)
                create_dialog.geometry("400x330")
            else:
                method_frame.pack_forget()
                clone_frame.pack_forget()
                method_var.set("scratch")
                create_dialog.geometry("350x190")

        athlete_var.trace_add('write', update_clone_options)
        update_clone_options()

        name_frame = tk.LabelFrame(create_dialog, text="Project Name", font=("Segoe UI", 9))
        name_frame.pack(fill='x', padx=10, pady=5)

        name_var = tk.StringVar()
        entry = tk.Entry(name_frame, textvariable=name_var, font=("Segoe UI", 10), width=35)
        entry.pack(padx=5, pady=5)
        entry.focus()

        def do_create():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Please enter a project name.")
                return
            selected_athlete_name = athlete_var.get()
            if not selected_athlete_name:
                messagebox.showerror("Error", "Please select an athlete.")
                return
            if "/" in selected_athlete_name or "\\" in selected_athlete_name:
                messagebox.showerror("Error", "Invalid athlete name.")
                return
            athlete_dir = ATHLETES / selected_athlete_name
            try:
                if method_var.get() == "clone":
                    if not clone_source_var.get():
                        messagebox.showerror("Error", "Please select a project to clone from.")
                        return
                    project_dir = clone_project(athlete_dir, clone_source_var.get(), name)
                else:
                    project_dir = self.athlete_manager.create_project_for_athlete(athlete_dir, name)
                create_dialog.destroy()
                self.refresh_athletes()
                messagebox.showinfo("Success",
                    f"Created project: {name}\n\nNext step: Add video clips to:\n{project_dir}/clips_in/")
            except FileExistsError:
                messagebox.showerror("Error", f"Project '{name}' already exists.")
            except ValueError as e:
                messagebox.showerror("Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create project: {e}")

        btn_frame = tk.Frame(create_dialog)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Create", command=do_create, bg="#4CAF50", fg="white").pack(side='left', padx=5)
        tk.Button(btn_frame, text="Cancel", command=create_dialog.destroy).pack(side='left', padx=5)

        create_dialog.bind('<Return>', lambda e: do_create())

    def open_athlete(self, event=None):
        athlete_dir, project_dir = self.get_selected_project()
        if not athlete_dir:
            return
        if not project_dir:
            self.open_folder()
            return
        status = self.athlete_manager.get_project_status(project_dir)
        if not status["has_clips"]:
            self.open_folder()
        elif status["needs_marking"]:
            self.mark_plays()
        elif status["needs_rendering"]:
            self.render_video()
        else:
            self.view_final()

    def open_folder(self):
        athlete_dir, project_dir = self.get_selected_project()
        if not athlete_dir:
            return
        folder_to_open = project_dir if project_dir else athlete_dir
        try:
            import platform
            system = platform.system()
            if system == "Linux":
                subprocess.run(["xdg-open", str(folder_to_open)], check=True)
            elif system == "Darwin":
                subprocess.run(["open", str(folder_to_open)], check=True)
            elif system == "Windows":
                subprocess.run(["explorer", str(folder_to_open)], check=True)
            else:
                messagebox.showinfo("Info", f"Please open folder manually: {folder_to_open}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            messagebox.showerror("Error", f"Could not open folder: {folder_to_open}")

    def delete_project(self):
        import shutil
        athlete_dir, project_dir = self.get_selected_project()
        if not athlete_dir or not project_dir:
            return
        try:
            project_dir.resolve().relative_to(ATHLETES.resolve())
        except ValueError:
            messagebox.showerror("Error", "Invalid project path.")
            return
        if athlete_dir == project_dir:
            messagebox.showerror("Cannot Delete",
                "This is a legacy (v1) athlete folder.\n\n"
                "To delete it, remove the folder manually from the file system.")
            return
        project_name = project_dir.name
        athlete_name = athlete_dir.name
        result = messagebox.askyesno("Delete Project",
            f"Delete project '{project_name}' for {athlete_name}?\n\n"
            f"This will permanently delete:\n"
            f"  - All video clips in clips_in/\n"
            f"  - All marking data\n"
            f"  - The rendered video (if any)\n\n"
            f"This cannot be undone.",
            icon='warning')
        if result:
            try:
                shutil.rmtree(project_dir)
                self.refresh_athletes()
                messagebox.showinfo("Deleted", f"Project '{project_name}' has been deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete project: {e}")

    def set_profile(self):
        athlete_dir = self.get_selected_athlete()
        if not athlete_dir:
            return
        v2 = is_v2_structure(athlete_dir)
        if v2:
            profile_exists = (athlete_dir / "athlete.json").exists()
        else:
            profile_exists = (athlete_dir / "project.json").exists()
        dialog = PlayerInfoDialog(
            self.root, athlete_dir.name,
            project_exists=profile_exists,
            athlete_dir=athlete_dir, is_v2=v2
        )
        if dialog.result == "save_only":
            self.refresh_athletes()

    def choose_slate_template(self):
        from slate_template_chooser import SlateTemplateChooser

        athlete_dir, project_dir = self.get_selected_project()
        if not athlete_dir or not project_dir:
            return

        v2 = is_v2_structure(athlete_dir)
        if v2:
            player = get_athlete_profile(athlete_dir)
        else:
            project_path = project_dir / "project.json"
            if project_path.exists():
                try:
                    data = json.loads(project_path.read_text())
                    player = data.get("player", {})
                except (IOError, json.JSONDecodeError):
                    player = {}
            else:
                player = {}

        if not player.get("name"):
            messagebox.showwarning("No Profile",
                                   "Set a player profile first so previews can be rendered.")
            return

        intro_image = None
        _temp_frame = None
        project_path = project_dir / "project.json"
        if project_path.exists():
            try:
                proj_data = json.loads(project_path.read_text())
                media_rel = proj_data.get("intro_media")
                if media_rel:
                    candidate = (athlete_dir if v2 else project_dir) / media_rel
                    if candidate.exists():
                        if candidate.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}:
                            intro_image = candidate
                        elif candidate.suffix.lower() in _VIDEO_EXTS:
                            _temp_frame = _extract_video_frame(candidate)
                            if _temp_frame:
                                intro_image = _temp_frame
            except (IOError, json.JSONDecodeError):
                pass

        current_template = None
        if project_path.exists():
            try:
                proj_data = json.loads(project_path.read_text())
                current_template = proj_data.get("slate_template")
            except (IOError, json.JSONDecodeError):
                pass

        result = SlateTemplateChooser.choose(
            self.root, player, intro_image, current=current_template
        )

        if result is not None:
            if project_path.exists():
                try:
                    proj_data = json.loads(project_path.read_text())
                    proj_data["slate_template"] = result
                    with open(project_path, "w") as f:
                        json.dump(proj_data, f, indent=2)
                    messagebox.showinfo("Slate Template",
                                        f"Template set to: {result.title()}")
                except (IOError, json.JSONDecodeError) as e:
                    messagebox.showerror("Error", f"Failed to save template choice:\n{e}")
            else:
                messagebox.showwarning("No Project",
                                       "No project.json found. Set up the project first.")

        if _temp_frame and _temp_frame.exists():
            _temp_frame.unlink(missing_ok=True)

    def mark_plays(self):
        athlete_dir, project_dir = self.get_selected_project()
        if not athlete_dir:
            return
        if not project_dir:
            messagebox.showwarning("No Project", "Please select a project first, or create one with 'New Project'.")
            return

        clips_in = project_dir / "clips_in"
        has_clips = clips_in.exists() and any(clips_in.iterdir()) if clips_in.exists() else False
        if not has_clips:
            messagebox.showwarning("No Clips", f"No clips found in {project_dir}/clips_in/\n\nAdd video clips first.")
            return

        v2 = is_v2_structure(athlete_dir)
        if v2:
            profile = get_athlete_profile(athlete_dir)
            has_profile = bool(profile.get("name", "").strip())
        else:
            project_path = project_dir / "project.json"
            if project_path.exists():
                try:
                    data = json.loads(project_path.read_text())
                    has_profile = bool(data.get("player", {}).get("name", "").strip())
                except (IOError, json.JSONDecodeError):
                    has_profile = False
            else:
                has_profile = False

        if not has_profile:
            messagebox.showwarning("No Profile",
                                 f"No player profile found for {athlete_dir.name}\n\n"
                                 "Please click 'Set Profile' first to enter player information.")
            return

        if v2:
            player_data = get_athlete_profile(athlete_dir)
            project_path = project_dir / "project.json"
            if project_path.exists():
                try:
                    project_data = json.loads(project_path.read_text())
                except (IOError, json.JSONDecodeError):
                    project_data = {}
            else:
                project_data = {}
        else:
            project_path = project_dir / "project.json"
            try:
                project_data = json.loads(project_path.read_text())
                player_data = project_data.get("player", {})
            except (IOError, json.JSONDecodeError) as e:
                messagebox.showerror("Error", f"Failed to read profile: {e}")
                return

        include_intro = project_data.get("include_intro", True)
        intro_media = project_data.get("intro_media")

        args = ["--dir", str(project_dir), "--overwrite"]

        if include_intro:
            args.append("--include-intro")
            for key, flag in [("name", "--player-name"), ("title", "--title"),
                              ("position", "--position"), ("grad_year", "--grad-year"),
                              ("club_team", "--club-team"), ("high_school", "--high-school"),
                              ("height_weight", "--height-weight"), ("gpa", "--gpa"),
                              ("email", "--email"), ("phone", "--phone")]:
                if player_data.get(key):
                    args.extend([flag, player_data[key]])

        if intro_media:
            args.extend(["--intro-media", intro_media])

        display_name = f"{athlete_dir.name}/{project_dir.name}" if v2 else athlete_dir.name
        self.run_script_async("mark_play.py", args,
                             "Marking Plays", f"Launching play marking for {display_name}")

    def reorder_clips(self):
        athlete_dir, project_dir = self.get_selected_project()
        if not athlete_dir:
            return
        if not project_dir:
            messagebox.showwarning("No Project", "Please select a project first, or create one with 'New Project'.")
            return
        project_path = project_dir / "project.json"
        if not project_path.exists():
            messagebox.showwarning("No Project", f"No project file found.\n\nSet Profile first.")
            return
        v2 = is_v2_structure(athlete_dir)
        display_name = f"{athlete_dir.name}/{project_dir.name}" if v2 else athlete_dir.name
        self.run_script_async("reorder_clips.py", ["--dir", str(project_dir)],
                             "Ordering Clips", f"Launching clip ordering for {display_name}")

    def render_video(self):
        athlete_dir, project_dir = self.get_selected_project()
        if not athlete_dir:
            return
        if not project_dir:
            messagebox.showwarning("No Project", "Please select a project first, or create one with 'New Project'.")
            return
        project_path = project_dir / "project.json"
        if not project_path.exists():
            messagebox.showwarning("No Project", f"No project file found.\n\nSet Profile first, then Order Clips and Mark Plays.")
            return
        try:
            project_data = json.loads(project_path.read_text())
            clips = project_data.get("clips", [])
            clips_count = len(clips)
            marked_count = sum(1 for clip in clips if is_clip_marked(clip))
            all_marked = clips_count > 0 and marked_count == clips_count
        except (IOError, json.JSONDecodeError):
            messagebox.showerror("Error", "Failed to read project file.")
            return

        v2 = is_v2_structure(athlete_dir)
        display_name = f"{athlete_dir.name}/{project_dir.name}" if v2 else athlete_dir.name

        if not all_marked:
            if clips_count == 0:
                messagebox.showwarning("No Clips", f"No clips in project for {display_name}\n\nUse Order Clips to sync clips from clips_in/ folder.")
            else:
                messagebox.showwarning("Clips Not Marked",
                    f"{marked_count}/{clips_count} clips marked for {display_name}\n\n"
                    "Use Mark Plays to mark all clips before rendering.")
            return

        final_video = project_dir / "output" / "final.mp4"
        if final_video.exists():
            result = messagebox.askyesno(
                "Re-render Video",
                f"A rendered video already exists for {display_name}.\n\n"
                "Do you want to render it again?\n\nThis will overwrite the existing video.",
                icon='question')
            if not result:
                return

        self.run_script_async("render_highlight.py", ["--dir", str(project_dir)],
                             "Rendering Video", f"Rendering highlight video for {display_name}")

    def view_final(self):
        athlete_dir, project_dir = self.get_selected_project()
        if not athlete_dir:
            return
        if not project_dir:
            messagebox.showwarning("No Project", "Please select a project first.")
            return

        v2 = is_v2_structure(athlete_dir)
        display_name = f"{athlete_dir.name}/{project_dir.name}" if v2 else athlete_dir.name

        final_video = project_dir / "output" / "final.mp4"
        if not final_video.exists():
            messagebox.showwarning("No Video", f"Final video not found for {display_name}\n\nRender video first.")
            return
        try:
            import platform
            system = platform.system()
            if system == "Linux":
                subprocess.run(["xdg-open", str(final_video)], check=True)
            elif system == "Darwin":
                subprocess.run(["open", str(final_video)], check=True)
            elif system == "Windows":
                import os
                os.startfile(str(final_video))
            else:
                messagebox.showinfo("Info", f"Please open video manually: {final_video}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            messagebox.showerror("Error", f"Could not open video: {final_video}")

    def batch_operations(self):
        BatchOperationsDialog(self.root, self.refresh_athletes)

    def run_script_async(self, script_name, args, title, description):
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
        ProfileManagementDialog(self.root)

    def quick_start_wizard(self):
        QuickStartWizard(self.root, self)

    def show_about(self):
        messagebox.showinfo("About SoccerHype",
                           f"SoccerHype v{__version__}\n\n"
                           "Professional athlete highlight video creator\n"
                           "with red spotlight tracking and intro slates.\n\n"
                           "Features:\n"
                           "- Interactive play marking\n"
                           "- Automated video processing\n"
                           "- Professional intro slates\n"
                           "- Batch processing\n\n"
                           "Created for parents, coaches, and athletes.")

    def run(self):
        self.root.mainloop()


def main():
    """Main entry point"""
    try:
        app = SoccerHypeGUI()
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        messagebox.showerror("Error", f"Application error: {e}")
        sys.exit(1)
