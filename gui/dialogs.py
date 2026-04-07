"""Dialog classes for the SoccerHype GUI."""

import json
import pathlib
import shutil
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from typing import Optional

from profile_manager import PlayerProfileManager, sanitize_profile_id
from utils.structure import (
    is_v2_structure,
    clone_project,
    SCHEMA_VERSION,
)
from gui.utils import _VIDEO_EXTS, _extract_video_frame


class ProgressDialog:
    """Modal dialog showing operation progress"""

    def __init__(self, parent, title, operation_name):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x150")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.dialog.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")

        tk.Label(self.dialog, text=operation_name, font=("Segoe UI", 10)).pack(pady=10)

        self.progress = ttk.Progressbar(self.dialog, mode='indeterminate')
        self.progress.pack(pady=10, padx=20, fill='x')
        self.progress.start()

        self.status_label = tk.Label(self.dialog, text="Starting...", font=("Segoe UI", 8))
        self.status_label.pack(pady=5)

        self.cancel_btn = tk.Button(self.dialog, text="Cancel", command=self.cancel)
        self.cancel_btn.pack(pady=10)

        self.cancelled = False
        self.process = None

    def update_status(self, text):
        self.status_label.config(text=text)
        self.dialog.update()

    def cancel(self):
        self.cancelled = True
        if self.process:
            self.process.terminate()
        self.dialog.destroy()

    def close(self):
        self.progress.stop()
        self.dialog.destroy()


class ProjectSelectionDialog:
    """Dialog for selecting a project from a v2 athlete."""

    def __init__(self, parent, athlete_manager, athlete_dir: pathlib.Path, allow_create: bool = True):
        self.result = None
        self.athlete_dir = athlete_dir
        self.athlete_manager = athlete_manager

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Select Project - {athlete_dir.name}")
        self.dialog.geometry("450x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)

        self.dialog.geometry(f"+{parent.winfo_rootx() + 150}+{parent.winfo_rooty() + 100}")

        self.dialog.update_idletasks()
        self.dialog.wait_visibility()
        self.dialog.grab_set()

        self.setup_ui(allow_create)
        self.refresh_projects()

        self.dialog.wait_window()

    def setup_ui(self, allow_create: bool):
        main_frame = tk.Frame(self.dialog)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)

        tk.Label(main_frame, text=f"Projects for {self.athlete_dir.name}",
                font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))

        list_frame = tk.Frame(main_frame)
        list_frame.pack(fill='both', expand=True)

        self.project_listbox = tk.Listbox(list_frame, font=("Segoe UI", 10), height=12)
        scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=self.project_listbox.yview)
        self.project_listbox.configure(yscrollcommand=scrollbar.set)
        self.project_listbox.bind('<Double-Button-1>', lambda e: self.select_project())

        self.project_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(10, 0))

        tk.Button(button_frame, text="Select", command=self.select_project,
                 bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold")).pack(side='left', padx=(0, 5))

        if allow_create:
            tk.Button(button_frame, text="New Project", command=self.create_project,
                     font=("Segoe UI", 10)).pack(side='left', padx=(0, 5))

        tk.Button(button_frame, text="Cancel", command=self.cancel,
                 font=("Segoe UI", 10)).pack(side='right')

    def refresh_projects(self):
        self.project_listbox.delete(0, tk.END)
        self.projects = self.athlete_manager.discover_projects(self.athlete_dir)

        if not self.projects:
            self.project_listbox.insert(tk.END, "(No projects - click 'New Project' to create one)")
            return

        for project_dir in self.projects:
            status = self.athlete_manager.get_project_status(project_dir)
            clips_info = f"{status['marked_count']}/{status['clips_count']} marked" if status['clips_count'] > 0 else "No clips"
            final_status = " ✓" if status['has_final'] else ""
            self.project_listbox.insert(tk.END, f"{project_dir.name} ({clips_info}){final_status}")

    def select_project(self):
        selection = self.project_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a project.")
            return
        if not self.projects:
            messagebox.showwarning("No Projects", "No projects available. Create a new project first.")
            return
        self.result = self.projects[selection[0]]
        self.dialog.destroy()

    def create_project(self):
        is_v2 = self.athlete_manager.is_v2_athlete(self.athlete_dir)
        existing_projects = self.athlete_manager.discover_projects(self.athlete_dir) if is_v2 else []
        has_cloneable = len(existing_projects) > 0

        create_dialog = tk.Toplevel(self.dialog)
        create_dialog.title("New Project")
        create_dialog.resizable(False, False)
        create_dialog.transient(self.dialog)
        create_dialog.grab_set()
        create_dialog.geometry(f"+{self.dialog.winfo_rootx() + 50}+{self.dialog.winfo_rooty() + 100}")

        clone_source_var = tk.StringVar(value="")

        if has_cloneable:
            create_dialog.geometry("400x280")

            method_frame = tk.LabelFrame(create_dialog, text="Creation Method", font=("Segoe UI", 9))
            method_frame.pack(fill='x', padx=10, pady=10)

            method_var = tk.StringVar(value="scratch")

            tk.Radiobutton(method_frame, text="Start from scratch (empty project)",
                          variable=method_var, value="scratch",
                          font=("Segoe UI", 9)).pack(anchor='w', padx=5, pady=2)
            tk.Radiobutton(method_frame, text="Clone existing project (copy clips and marks)",
                          variable=method_var, value="clone",
                          font=("Segoe UI", 9)).pack(anchor='w', padx=5, pady=2)

            clone_frame = tk.LabelFrame(create_dialog, text="Clone From", font=("Segoe UI", 9))
            clone_frame.pack(fill='x', padx=10, pady=5)

            clone_combo = ttk.Combobox(clone_frame, textvariable=clone_source_var,
                                       values=[p.name for p in existing_projects],
                                       state='disabled', font=("Segoe UI", 9))
            clone_combo.pack(fill='x', padx=5, pady=5)
            if existing_projects:
                clone_combo.set(existing_projects[0].name)

            def on_method_change(*args):
                if method_var.get() == "clone":
                    clone_combo.config(state='readonly')
                else:
                    clone_combo.config(state='disabled')

            method_var.trace_add('write', on_method_change)
        else:
            create_dialog.geometry("350x140")
            method_var = tk.StringVar(value="scratch")

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
            try:
                if method_var.get() == "clone":
                    if not clone_source_var.get():
                        messagebox.showerror("Error", "Please select a project to clone from.")
                        return
                    project_dir = clone_project(self.athlete_dir, clone_source_var.get(), name)
                else:
                    project_dir = self.athlete_manager.create_project_for_athlete(self.athlete_dir, name)
                create_dialog.destroy()
                self.result = project_dir
                self.dialog.destroy()
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

    def cancel(self):
        self.result = None
        self.dialog.destroy()


class PlayerInfoDialog:
    """Dialog for collecting player information before marking plays"""

    def __init__(self, parent, athlete_name, project_exists=False, athlete_dir=None, is_v2=False):
        self.result = None
        self.athlete_name = athlete_name
        self.is_v2 = is_v2

        if athlete_dir:
            self.athlete_dir = pathlib.Path(athlete_dir)
        else:
            self.athlete_dir = pathlib.Path.cwd() / "athletes" / athlete_name

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Player Information - {athlete_name}")
        self.dialog.geometry("750x650")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.dialog.geometry(f"+{parent.winfo_rootx() + 150}+{parent.winfo_rooty() + 50}")

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

        profiles_db_path = pathlib.Path.cwd() / "players_database.json"
        self.profile_manager = PlayerProfileManager(profiles_db_path)
        self.selected_profile_id = None

        self.setup_ui(project_exists)
        self.load_existing_profile()
        self.scan_existing_media()

        self.dialog.wait_window()

    def setup_ui(self, project_exists):
        main_frame = tk.Frame(self.dialog)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)

        tk.Label(main_frame, text="Player Information",
                font=("Segoe UI", 16, "bold")).pack(pady=(0, 15))

        if project_exists:
            warning_frame = tk.Frame(main_frame, bg="#fff3cd", relief="solid", bd=1)
            warning_frame.pack(fill='x', pady=(0, 10))
            tk.Label(warning_frame, text="Warning: Project file exists and will be overwritten",
                    font=("Segoe UI", 9), bg="#fff3cd", fg="#856404").pack(pady=5)

        canvas_container = tk.Frame(main_frame)
        canvas_container.pack(fill='both', expand=True)

        canvas = tk.Canvas(canvas_container)
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=700)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Profile Selection Section
        profile_frame = tk.Frame(scrollable_frame, bg="#e8f4fd", relief="solid", bd=1)
        profile_frame.pack(fill='x', pady=(0, 15), padx=5)

        tk.Label(profile_frame, text="Player Profile Management:",
                font=("Segoe UI", 10, "bold"), bg="#e8f4fd").pack(anchor='w', padx=10, pady=(5, 0))

        profile_select_frame = tk.Frame(profile_frame, bg="#e8f4fd")
        profile_select_frame.pack(fill='x', padx=10, pady=5)

        self.profile_combo = ttk.Combobox(profile_select_frame, state="readonly")
        profile_names = ["<New Player>"]
        if self.profile_manager.player_profiles:
            profile_names.extend([p["name"] for p in self.profile_manager.player_profiles.values()])
        self.profile_combo['values'] = profile_names
        self.profile_combo.set("<New Player>")
        self.profile_combo.bind('<<ComboboxSelected>>', self.on_profile_selected)
        self.profile_combo.pack(fill='x', pady=(0, 5))

        profile_btn_frame = tk.Frame(profile_select_frame, bg="#e8f4fd")
        profile_btn_frame.pack(fill='x')

        tk.Button(profile_btn_frame, text="Save as Profile",
                 command=self.save_current_as_profile, font=("Segoe UI", 9)).pack(side='left', padx=(0, 5))
        tk.Button(profile_btn_frame, text="Delete Profile",
                 command=self.delete_selected_profile, font=("Segoe UI", 9)).pack(side='left')

        help_text = "Select a profile to auto-fill fields, or choose '<New Player>' to enter manually."
        if not self.profile_manager.player_profiles:
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

        tk.Label(intro_frame, text="Intro Media (Optional)",
                font=("Segoe UI", 12, "bold"), bg="#f8f9fa").pack(anchor='w', padx=10, pady=(10, 5))

        tk.Label(intro_frame,
                text="Add a player picture or intro video for the highlight slate",
                font=("Segoe UI", 9), bg="#f8f9fa", fg="#666").pack(anchor='w', padx=10, pady=(0, 10))

        media_frame = tk.Frame(intro_frame, bg="#f8f9fa")
        media_frame.pack(fill='x', padx=10, pady=(0, 10))

        self.selected_media_var = tk.StringVar()
        self.media_files = []

        self.current_media_label = tk.Label(media_frame, text="No media selected",
                                          font=("Segoe UI", 9), bg="#f8f9fa")
        self.current_media_label.pack(anchor='w', pady=(0, 5))

        media_btn_frame = tk.Frame(media_frame, bg="#f8f9fa")
        media_btn_frame.pack(fill='x')

        tk.Button(media_btn_frame, text="Browse & Upload", command=self.browse_media,
                 font=("Segoe UI", 9), bg="#007ACC", fg="white").pack(side='left', padx=(0, 5))
        tk.Button(media_btn_frame, text="Choose Existing", command=self.choose_existing_media,
                 font=("Segoe UI", 9)).pack(side='left', padx=(0, 5))
        tk.Button(media_btn_frame, text="Clear Selection", command=self.clear_media_selection,
                 font=("Segoe UI", 9)).pack(side='left')

        # Slate Template Section
        slate_frame = tk.Frame(scrollable_frame, relief="solid", bd=1, bg="#f8f9fa")
        slate_frame.pack(fill='x', pady=15)

        tk.Label(slate_frame, text="Slate Template",
                 font=("Segoe UI", 12, "bold"), bg="#f8f9fa").pack(anchor='w', padx=10, pady=(10, 5))

        slate_inner = tk.Frame(slate_frame, bg="#f8f9fa")
        slate_inner.pack(fill='x', padx=10, pady=(0, 10))

        self.slate_template_var = tk.StringVar(value="classic")
        self.slate_template_label = tk.Label(
            slate_inner, text="Current: Classic (default)",
            font=("Segoe UI", 9), bg="#f8f9fa")
        self.slate_template_label.pack(anchor='w', pady=(0, 5))

        tk.Button(slate_inner, text="Change Template...",
                  command=self._open_slate_chooser,
                  font=("Segoe UI", 9)).pack(anchor='w')

        # Checkboxes
        checkbox_frame = tk.Frame(scrollable_frame)
        checkbox_frame.pack(fill='x', pady=15)

        tk.Checkbutton(checkbox_frame, text="Include intro screen with player slate",
                      variable=self.include_intro_var, font=("Segoe UI", 10)).pack(anchor='w')

        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(10, 0))

        save_btn = tk.Button(button_frame, text="Save Profile", command=self.save_only,
                           bg="#4CAF50", fg="white", font=("Segoe UI", 11, "bold"))
        save_btn.pack(fill='x', pady=(0, 8))

        cancel_btn = tk.Button(button_frame, text="Cancel", command=self.cancel,
                             font=("Segoe UI", 10))
        cancel_btn.pack(fill='x')

    def load_existing_profile(self):
        try:
            if self.is_v2:
                athlete_json = self.athlete_dir / "athlete.json"
                if athlete_json.exists():
                    data = json.loads(athlete_json.read_text())
                    self._populate_form_from_data(data)
                projects_dir = self.athlete_dir / "projects"
                if projects_dir.exists():
                    for pdir in sorted(projects_dir.iterdir()):
                        pjson = pdir / "project.json"
                        if pjson.exists():
                            pdata = json.loads(pjson.read_text())
                            tpl = pdata.get("slate_template")
                            if tpl:
                                self.slate_template_var.set(tpl)
                                from slate_templates import get_template
                                self.slate_template_label.config(
                                    text=f"Current: {get_template(tpl).display_name}")
                            break
            else:
                project_json = self.athlete_dir / "project.json"
                if project_json.exists():
                    data = json.loads(project_json.read_text())
                    player_data = data.get("player", {})
                    self._populate_form_from_data(player_data)
                    self.include_intro_var.set(data.get("include_intro", True))
                    if data.get("intro_media"):
                        intro_path = self.athlete_dir / data["intro_media"]
                        if intro_path.exists():
                            self.selected_media_var.set(str(intro_path))
                            self.current_media_label.config(text=f"Selected: {intro_path.name}")
                    tpl = data.get("slate_template")
                    if tpl:
                        self.slate_template_var.set(tpl)
                        from slate_templates import get_template
                        self.slate_template_label.config(
                            text=f"Current: {get_template(tpl).display_name}")
        except (IOError, json.JSONDecodeError):
            pass

    def _populate_form_from_data(self, data: dict):
        field_map = {
            "name": self.name_var, "title": self.title_var,
            "position": self.position_var, "grad_year": self.grad_year_var,
            "club_team": self.club_team_var, "high_school": self.high_school_var,
            "height_weight": self.height_weight_var, "gpa": self.gpa_var,
            "email": self.email_var, "phone": self.phone_var,
        }
        for key, var in field_map.items():
            if data.get(key):
                var.set(data[key])

    def scan_existing_media(self):
        intro_dir = self.athlete_dir / "intro"
        self.media_files = []
        if intro_dir.exists():
            image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
            video_exts = {'.mp4', '.mov', '.avi', '.mkv'}
            for file_path in intro_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in (image_exts | video_exts):
                    self.media_files.append(file_path)
            if self.media_files:
                self.current_media_label.config(text=f"Found {len(self.media_files)} media file(s) in intro folder")
            else:
                self.current_media_label.config(text="No media files found in intro folder")

    def _open_slate_chooser(self):
        from slate_template_chooser import SlateTemplateChooser
        from slate_templates import get_template

        player = {
            "name": self.name_var.get().strip() or "Player Name",
            "position": self.position_var.get().strip(),
            "grad_year": self.grad_year_var.get().strip(),
            "club_team": self.club_team_var.get().strip(),
            "high_school": self.high_school_var.get().strip(),
            "height_weight": self.height_weight_var.get().strip(),
            "gpa": self.gpa_var.get().strip(),
            "email": self.email_var.get().strip(),
            "phone": self.phone_var.get().strip(),
        }

        intro_image = None
        _temp_frame = None
        media_path_str = self.selected_media_var.get()
        if media_path_str:
            candidate = pathlib.Path(media_path_str)
            if candidate.exists():
                if candidate.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}:
                    intro_image = candidate
                elif candidate.suffix.lower() in _VIDEO_EXTS:
                    _temp_frame = _extract_video_frame(candidate)
                    if _temp_frame:
                        intro_image = _temp_frame

        result = SlateTemplateChooser.choose(
            self.dialog, player, intro_image,
            current=self.slate_template_var.get()
        )

        if _temp_frame and _temp_frame.exists():
            _temp_frame.unlink(missing_ok=True)

        if result is not None:
            self.slate_template_var.set(result)
            tpl = get_template(result)
            self.slate_template_label.config(text=f"Current: {tpl.display_name}")

    def browse_media(self):
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
                intro_dir = self.athlete_dir / "intro"
                intro_dir.mkdir(parents=True, exist_ok=True)

                copied_files = []
                failed_files = []

                for file_path in files:
                    source = pathlib.Path(file_path)
                    destination = intro_dir / source.name

                    try:
                        if not source.exists():
                            failed_files.append(f"{source.name}: File not found")
                            continue
                        if not source.is_file():
                            failed_files.append(f"{source.name}: Not a regular file")
                            continue
                        if destination.resolve().parent != intro_dir.resolve():
                            failed_files.append(f"{source.name}: Invalid destination path")
                            continue
                        shutil.copy2(source, destination)
                        copied_files.append(destination.name)
                    except PermissionError:
                        failed_files.append(f"{source.name}: Permission denied")
                    except OSError as e:
                        failed_files.append(f"{source.name}: {str(e)}")
                    except Exception as e:
                        failed_files.append(f"{source.name}: Unexpected error - {str(e)}")

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

                self.scan_existing_media()

            except Exception as e:
                messagebox.showerror("Upload Error", f"Failed to copy files:\n{e}")

    def choose_existing_media(self):
        if not self.media_files:
            messagebox.showwarning("No Media", "No media files found. Use 'Browse & Upload' to add files.")
            return

        selection_dialog = tk.Toplevel(self.dialog)
        selection_dialog.title("Choose Intro Media")
        selection_dialog.geometry("400x300")
        selection_dialog.resizable(False, False)
        selection_dialog.transient(self.dialog)
        selection_dialog.grab_set()

        selection_dialog.geometry(f"+{self.dialog.winfo_rootx() + 100}+{self.dialog.winfo_rooty() + 100}")

        tk.Label(selection_dialog, text="Select intro media file:",
                font=("Segoe UI", 10, "bold")).pack(pady=10)

        listbox_frame = tk.Frame(selection_dialog)
        listbox_frame.pack(fill='both', expand=True, padx=20, pady=(0, 10))

        listbox = tk.Listbox(listbox_frame, font=("Segoe UI", 9))
        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical")
        listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)

        for media_file in self.media_files:
            file_type = "IMG" if media_file.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'} else "VID"
            listbox.insert(tk.END, f"[{file_type}] {media_file.name}")

        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        btn_frame = tk.Frame(selection_dialog)
        btn_frame.pack(fill='x', padx=20, pady=(0, 10))

        selected_media = [None]

        def select_media():
            selection = listbox.curselection()
            if selection:
                selected_media[0] = self.media_files[selection[0]]
                self.selected_media_var.set(str(selected_media[0]))
                self.current_media_label.config(text=f"Selected: {selected_media[0].name}")
                selection_dialog.destroy()
            else:
                messagebox.showwarning("No Selection", "Please select a media file.")

        tk.Button(btn_frame, text="Select", command=select_media,
                 bg="#4CAF50", fg="white", font=("Segoe UI", 10)).pack(side='right', padx=(5, 0))
        tk.Button(btn_frame, text="Cancel", command=selection_dialog.destroy,
                 font=("Segoe UI", 10)).pack(side='right')

    def clear_media_selection(self):
        self.selected_media_var.set("")
        self.current_media_label.config(text="No media selected")

    def save_only(self):
        if not self.name_var.get().strip():
            messagebox.showerror("Validation Error", "Player name is required.")
            return

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

        selected_media_path = self.selected_media_var.get() if self.selected_media_var.get() else None
        intro_media = None
        if selected_media_path:
            media_path = pathlib.Path(selected_media_path)
            try:
                intro_media = str(media_path.relative_to(self.athlete_dir)) if media_path.exists() else None
            except ValueError:
                intro_dir = self.athlete_dir / "intro"
                if media_path.exists() and intro_dir in media_path.parents:
                    intro_media = str(media_path.relative_to(self.athlete_dir))
                elif media_path.exists() and (intro_dir / media_path.name).exists():
                    intro_media = str(pathlib.Path("intro") / media_path.name)
                else:
                    print(f"Warning: Media file {media_path} is outside athlete directory")
                    intro_media = None

        try:
            self.athlete_dir.mkdir(parents=True, exist_ok=True)

            if self.is_v2:
                athlete_json_path = self.athlete_dir / "athlete.json"

                if athlete_json_path.exists():
                    try:
                        athlete_data = json.loads(athlete_json_path.read_text())
                    except (IOError, json.JSONDecodeError):
                        athlete_data = {}
                else:
                    athlete_data = {}

                athlete_data.update(player_data)
                athlete_data["schema_version"] = SCHEMA_VERSION

                with open(athlete_json_path, 'w') as f:
                    json.dump(athlete_data, f, indent=2)

                projects_dir = self.athlete_dir / "projects"
                if projects_dir.exists():
                    for project_dir in projects_dir.iterdir():
                        if project_dir.is_dir():
                            project_json_path = project_dir / "project.json"
                            if project_json_path.exists():
                                try:
                                    project_data = json.loads(project_json_path.read_text())
                                    project_data["include_intro"] = self.include_intro_var.get()
                                    if not project_data.get("intro_media") and intro_media:
                                        project_data["intro_media"] = intro_media
                                    tpl_val = self.slate_template_var.get()
                                    if tpl_val and tpl_val != "classic":
                                        project_data["slate_template"] = tpl_val
                                    elif "slate_template" in project_data and tpl_val == "classic":
                                        project_data["slate_template"] = None
                                    with open(project_json_path, 'w') as f:
                                        json.dump(project_data, f, indent=2)
                                except (IOError, json.JSONDecodeError):
                                    pass

                messagebox.showinfo("Success",
                    f"Player profile saved successfully!\n\nFile: {athlete_json_path}")
            else:
                project_path = self.athlete_dir / "project.json"

                existing_clips = []
                if project_path.exists():
                    try:
                        existing_data = json.loads(project_path.read_text())
                        existing_clips = existing_data.get("clips", [])
                    except (IOError, json.JSONDecodeError):
                        pass

                tpl_val = self.slate_template_var.get()
                project_data = {
                    "player": player_data,
                    "include_intro": self.include_intro_var.get(),
                    "intro_media": intro_media,
                    "slate_template": tpl_val if tpl_val != "classic" else None,
                    "clips": existing_clips
                }

                with open(project_path, 'w') as f:
                    json.dump(project_data, f, indent=2)

                messagebox.showinfo("Success",
                    f"Player information saved successfully!\n\nFile: {project_path}")

            self.result = "save_only"
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save player information:\n{str(e)}")

    def save_current_as_profile(self):
        name = self.name_var.get().strip()

        validation_errors = []
        if not name:
            validation_errors.append("Player name is required")
        elif len(name) > 100:
            validation_errors.append("Player name must be 100 characters or less")

        email = self.email_var.get().strip()
        if email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                validation_errors.append("Email address is not valid")

        if validation_errors:
            messagebox.showerror("Validation Error",
                               "Please fix the following errors:\n\n" +
                               "\n".join(f"- {error}" for error in validation_errors))
            return

        import time
        timestamp = str(int(time.time()))
        profile_id = f"{sanitize_profile_id(name)}_{timestamp}"

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

        self.profile_manager.player_profiles[profile_id] = profile
        self.profile_manager.save_player_profiles()

        if hasattr(self, 'profile_combo'):
            profile_names = ["<New Player>"] + [p["name"] for p in self.profile_manager.player_profiles.values()]
            self.profile_combo['values'] = profile_names

        messagebox.showinfo("Success", f"Profile saved for {name}")

    def load_profile_data(self, profile_id):
        if profile_id in self.profile_manager.player_profiles:
            profile = self.profile_manager.player_profiles[profile_id]
            self._populate_form_from_data(profile)
            self.selected_profile_id = profile_id

    def on_profile_selected(self, event=None):
        if hasattr(self, 'profile_combo'):
            selection = self.profile_combo.get()
            if selection and selection != "<New Player>":
                for profile_id, profile in self.profile_manager.player_profiles.items():
                    if profile["name"] == selection:
                        self.load_profile_data(profile_id)
                        break
            else:
                self.selected_profile_id = None

    def delete_selected_profile(self):
        if self.selected_profile_id and self.selected_profile_id in self.profile_manager.player_profiles:
            profile_name = self.profile_manager.player_profiles[self.selected_profile_id]["name"]

            if messagebox.askyesno("Confirm Delete",
                                 f"Are you sure you want to delete the profile for {profile_name}?"):
                del self.profile_manager.player_profiles[self.selected_profile_id]
                self.profile_manager.save_player_profiles()

                if hasattr(self, 'profile_combo'):
                    self.profile_combo['values'] = ["<New Player>"] + [p["name"] for p in self.profile_manager.player_profiles.values()]
                    self.profile_combo.set("<New Player>")

                self.selected_profile_id = None
                messagebox.showinfo("Success", f"Profile for {profile_name} has been deleted.")
        else:
            messagebox.showwarning("Warning", "No profile selected for deletion.")

    def cancel(self):
        self.result = None
        self.dialog.destroy()


class QuickStartWizard:
    """Step-by-step wizard that walks new users through the highlight video workflow."""

    STEPS = [
        {
            "title": "Step 1: Create or Select an Athlete",
            "desc": "Choose an existing athlete project or create a new one.",
            "action_label": "New Athlete",
            "check": "_check_athlete",
        },
        {
            "title": "Step 2: Add Video Clips",
            "desc": "Place source video clips (.mp4, .mov, etc.) into the clips_in/ folder.",
            "action_label": "Open Folder",
            "check": "_check_clips",
        },
        {
            "title": "Step 3: Order Clips",
            "desc": "Arrange the clips in the order you want them in the final video.",
            "action_label": "Order Clips",
            "check": "_check_order",
        },
        {
            "title": "Step 4: Mark Plays",
            "desc": "Mark the player position and spotlight moment in each clip.",
            "action_label": "Mark Plays",
            "check": "_check_marks",
        },
        {
            "title": "Step 5: Render Video",
            "desc": "Render the final highlight video with spotlight overlays and intro slate.",
            "action_label": "Render",
            "check": "_check_render",
        },
    ]

    def __init__(self, parent, gui):
        self.parent = parent
        self.gui = gui
        self.current_step = 0
        self.athlete_dir: Optional[pathlib.Path] = None
        self.project_dir: Optional[pathlib.Path] = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Quick Start Wizard")
        self.dialog.geometry("520x340")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.geometry(f"+{parent.winfo_rootx() + 140}+{parent.winfo_rooty() + 100}")

        self._build_ui()
        self._detect_initial_state()
        self._show_step()

    def _build_ui(self):
        main = tk.Frame(self.dialog)
        main.pack(fill='both', expand=True, padx=20, pady=15)

        self.progress_frame = tk.Frame(main)
        self.progress_frame.pack(fill='x', pady=(0, 12))
        self.step_labels = []
        for i in range(len(self.STEPS)):
            lbl = tk.Label(self.progress_frame, text=f" {i+1} ", font=("Segoe UI", 10, "bold"),
                           relief='groove', width=3)
            lbl.pack(side='left', padx=3)
            self.step_labels.append(lbl)

        self.title_var = tk.StringVar()
        tk.Label(main, textvariable=self.title_var, font=("Segoe UI", 14, "bold"),
                 anchor='w').pack(fill='x', pady=(0, 6))

        self.desc_var = tk.StringVar()
        tk.Label(main, textvariable=self.desc_var, font=("Segoe UI", 10),
                 anchor='w', wraplength=470, justify='left').pack(fill='x')

        self.status_var = tk.StringVar()
        self.status_label = tk.Label(main, textvariable=self.status_var,
                                     font=("Segoe UI", 10, "italic"), fg="#555",
                                     anchor='w', wraplength=470, justify='left')
        self.status_label.pack(fill='x', pady=(8, 0))

        btn_frame = tk.Frame(main)
        btn_frame.pack(fill='x', side='bottom', pady=(15, 0))

        self.close_btn = tk.Button(btn_frame, text="Close", command=self.dialog.destroy,
                                   font=("Segoe UI", 10))
        self.close_btn.pack(side='left')

        self.next_btn = tk.Button(btn_frame, text="Next \u2192", command=self._on_next,
                                  font=("Segoe UI", 10, "bold"), bg="#4CAF50", fg="white")
        self.next_btn.pack(side='right', padx=(5, 0))

        self.action_btn = tk.Button(btn_frame, text="Action", command=self._on_action,
                                    font=("Segoe UI", 10))
        self.action_btn.pack(side='right', padx=(5, 0))

        self.back_btn = tk.Button(btn_frame, text="\u2190 Back", command=self._on_back,
                                  font=("Segoe UI", 10))
        self.back_btn.pack(side='right')

    def _show_step(self):
        step = self.STEPS[self.current_step]
        self.title_var.set(step["title"])
        self.desc_var.set(step["desc"])
        self.action_btn.config(text=step["action_label"])

        for i, lbl in enumerate(self.step_labels):
            if i < self.current_step:
                lbl.config(bg="#4CAF50", fg="white")
            elif i == self.current_step:
                lbl.config(bg="#2196F3", fg="white")
            else:
                lbl.config(bg="#ddd", fg="#333")

        self.back_btn.config(state='normal' if self.current_step > 0 else 'disabled')

        ready, status_text = getattr(self, step["check"])()
        self.status_var.set(status_text)
        self.status_label.config(fg="#2e7d32" if ready else "#c62828")

        is_last = self.current_step == len(self.STEPS) - 1
        self.next_btn.config(text="Finish" if is_last else "Next \u2192",
                             state='normal' if ready else 'disabled')

    def _on_next(self):
        if self.current_step < len(self.STEPS) - 1:
            self.current_step += 1
            self._show_step()
        else:
            self.dialog.destroy()

    def _on_back(self):
        if self.current_step > 0:
            self.current_step -= 1
            self._show_step()

    def _on_action(self):
        actions = [
            self._action_new_athlete,
            self._action_open_folder,
            self._action_order_clips,
            self._action_mark_plays,
            self._action_render,
        ]
        actions[self.current_step]()

    def _detect_initial_state(self):
        """Pick up the currently selected project from the main GUI."""
        sel = self.gui.athlete_tree.selection()
        if not sel:
            return
        row_id = sel[0]
        if row_id == "_empty_" or "|" not in row_id:
            return
        parts = row_id.split("|", 1)
        from gui.utils import ATHLETES
        adir = ATHLETES / parts[0]
        if not adir.exists():
            return
        self.athlete_dir = adir
        pname = parts[1]
        if pname == "(default)":
            self.project_dir = adir
        elif pname != "_no_project_":
            pdir = adir / "projects" / pname
            if pdir.exists():
                self.project_dir = pdir

    # ── Readiness checks ────────────────────────────────────────────────

    def _check_athlete(self):
        if self.athlete_dir and self.athlete_dir.exists():
            return True, f"\u2713 Athlete selected: {self.athlete_dir.name}"
        athletes = self.gui.athlete_manager.discover_athletes()
        if athletes:
            return False, "Select an athlete from the main list, or create a new one."
        return False, "No athletes found. Click 'New Athlete' to create one."

    def _check_clips(self):
        if not self.project_dir:
            return False, "No project selected yet. Go back to Step 1."
        clips_in = self.project_dir / "clips_in"
        try:
            if clips_in.exists():
                clips = [f for f in clips_in.iterdir() if f.suffix.lower() in _VIDEO_EXTS]
                if clips:
                    return True, f"\u2713 {len(clips)} clip(s) found in clips_in/"
        except OSError:
            pass
        return False, "No clips in clips_in/. Click 'Open Folder' to add videos."

    def _check_order(self):
        if not self.project_dir:
            return False, "No project selected yet."
        pj = self.project_dir / "project.json"
        if pj.exists():
            try:
                data = json.loads(pj.read_text())
                clips = data.get("clips", [])
                if clips:
                    return True, f"\u2713 {len(clips)} clip(s) in project order."
            except (IOError, json.JSONDecodeError):
                pass
        clips_in = self.project_dir / "clips_in"
        try:
            if clips_in.exists() and any(
                f.suffix.lower() in _VIDEO_EXTS for f in clips_in.iterdir()
            ):
                return True, "Clips found. You can order them or proceed to marking."
        except OSError:
            pass
        return False, "Add clips first (Step 2)."

    def _check_marks(self):
        if not self.project_dir:
            return False, "No project selected yet."
        pj = self.project_dir / "project.json"
        if pj.exists():
            try:
                from clip_sync import is_clip_marked
                data = json.loads(pj.read_text())
                clips = data.get("clips", [])
                marked = sum(1 for c in clips if is_clip_marked(c))
                if clips and marked == len(clips):
                    return True, f"\u2713 All {marked} clip(s) marked."
                if clips:
                    return False, f"{marked}/{len(clips)} clips marked. Click 'Mark Plays' to continue."
            except (IOError, json.JSONDecodeError):
                pass
        return False, "No marked clips. Use 'Mark Plays' to mark player positions."

    def _check_render(self):
        if not self.project_dir:
            return False, "No project selected yet."
        final = self.project_dir / "output" / "final.mp4"
        if final.exists():
            return True, f"\u2713 Rendered video exists: {final.name}"
        return False, "Not yet rendered. Click 'Render' to create the highlight video."

    # ── Actions ─────────────────────────────────────────────────────────

    def _action_new_athlete(self):
        before = set(self.gui.athlete_manager.discover_athletes())
        self.gui.new_athlete()
        after = set(self.gui.athlete_manager.discover_athletes())
        new = after - before
        if new:
            self.athlete_dir = next(iter(new))
            projects = self.gui.athlete_manager.discover_projects(self.athlete_dir)
            if projects:
                self.project_dir = projects[0]
        self._show_step()

    def _action_open_folder(self):
        if not self.project_dir:
            messagebox.showwarning("No Project", "Select or create an athlete first (Step 1).")
            return
        folder = self.project_dir / "clips_in"
        folder.mkdir(parents=True, exist_ok=True)
        import platform
        import subprocess
        system = platform.system()
        try:
            if system == "Linux":
                subprocess.run(["xdg-open", str(folder)], check=True)
            elif system == "Darwin":
                subprocess.run(["open", str(folder)], check=True)
            elif system == "Windows":
                subprocess.run(["explorer", str(folder)], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            messagebox.showinfo("Info", f"Open manually: {folder}")
        self._show_step()

    def _action_order_clips(self):
        if not self.project_dir:
            return
        self._select_project_in_tree()
        self.gui.reorder_clips()

    def _action_mark_plays(self):
        if not self.project_dir:
            return
        self._select_project_in_tree()
        self.gui.mark_plays()

    def _action_render(self):
        if not self.project_dir:
            return
        self._select_project_in_tree()
        self.gui.render_video()

    def _select_project_in_tree(self):
        """Ensure the wizard's project is selected in the main Treeview."""
        if not self.athlete_dir or not self.project_dir:
            return
        v2 = is_v2_structure(self.athlete_dir)
        pname = self.project_dir.name if v2 and self.project_dir != self.athlete_dir else "(default)"
        row_id = f"{self.athlete_dir.name}|{pname}"
        try:
            self.gui.athlete_tree.selection_set(row_id)
        except tk.TclError:
            pass
