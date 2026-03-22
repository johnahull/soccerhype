"""Profile management dialog for the SoccerHype GUI."""

import pathlib
import time
import tkinter as tk
from tkinter import messagebox, ttk

from profile_manager import PlayerProfileManager, sanitize_profile_id


class ProfileManagementDialog:
    """Dialog for standalone player profile management"""

    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Manage Player Profiles")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.dialog.geometry(f"+{parent.winfo_rootx() + 100}+{parent.winfo_rooty() + 50}")

        profiles_db_path = pathlib.Path.cwd() / "players_database.json"
        self.profile_manager = PlayerProfileManager(profiles_db_path)

        self.setup_ui()
        self.refresh_profiles_list()

        self.dialog.wait_window()

    def setup_ui(self):
        main_frame = tk.Frame(self.dialog)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)

        tk.Label(main_frame, text="Player Profile Management",
                font=("Segoe UI", 16, "bold")).pack(pady=(0, 15))

        content_frame = tk.Frame(main_frame)
        content_frame.pack(fill='both', expand=True)

        # Left side - Profile list
        left_frame = tk.Frame(content_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        tk.Label(left_frame, text="Saved Profiles:", font=("Segoe UI", 12, "bold")).pack(anchor='w')

        list_frame = tk.Frame(left_frame)
        list_frame.pack(fill='both', expand=True, pady=(5, 0))

        self.profiles_listbox = tk.Listbox(list_frame, font=("Segoe UI", 10))
        scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=self.profiles_listbox.yview)
        self.profiles_listbox.configure(yscrollcommand=scrollbar.set)
        self.profiles_listbox.bind('<<ListboxSelect>>', self.on_profile_selected)

        self.profiles_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

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

        form_container = tk.Frame(right_frame)
        form_container.pack(fill='both', expand=True, pady=(5, 0))

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

        self.create_form_fields()

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

        self.current_profile_id = None
        self.enable_form(len(self.profile_manager.player_profiles) > 0)

    def create_form_fields(self):
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
        state = 'normal' if enabled else 'disabled'
        for entry in self.form_entries.values():
            entry.config(state=state)
        if hasattr(self, 'save_btn'):
            self.save_btn.config(state=state)
        if hasattr(self, 'revert_btn'):
            self.revert_btn.config(state=state)

    def refresh_profiles_list(self):
        self.profiles_listbox.delete(0, tk.END)
        for profile_id, profile in self.profile_manager.player_profiles.items():
            display_name = f"{profile['name']} ({profile.get('position', 'No Position')})"
            self.profiles_listbox.insert(tk.END, display_name)

    def on_profile_selected(self, event=None):
        selection = self.profiles_listbox.curselection()
        if not selection:
            return
        profile_ids = list(self.profile_manager.player_profiles.keys())
        if selection[0] < len(profile_ids):
            self.current_profile_id = profile_ids[selection[0]]
            self.load_profile_details(self.current_profile_id)
            self.enable_form(True)

    def load_profile_details(self, profile_id):
        if profile_id in self.profile_manager.player_profiles:
            profile = self.profile_manager.player_profiles[profile_id]
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
        for var in [self.name_var, self.title_var, self.position_var, self.grad_year_var,
                   self.club_team_var, self.high_school_var, self.height_weight_var,
                   self.gpa_var, self.email_var, self.phone_var]:
            var.set("")
        self.current_profile_id = None
        self.enable_form(True)
        self.form_entries["Player Name:"].focus_set()

    def validate_profile_data(self):
        errors = []
        name = self.name_var.get().strip()
        if not name:
            errors.append("Player name is required")
        elif len(name) > 100:
            errors.append("Player name must be 100 characters or less")

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

        email = self.email_var.get().strip()
        if email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                errors.append("Email address is not valid")

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
        validation_errors = self.validate_profile_data()
        if validation_errors:
            messagebox.showerror("Validation Error",
                               "Please fix the following errors:\n\n" +
                               "\n".join(f"- {error}" for error in validation_errors))
            return

        name = self.name_var.get().strip()

        if self.current_profile_id is None:
            timestamp = str(int(time.time()))
            profile_id = f"{sanitize_profile_id(name)}_{timestamp}"
            self.current_profile_id = profile_id

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
            "created": self.profile_manager.player_profiles.get(self.current_profile_id, {}).get("created",
                                                                                time.strftime("%Y-%m-%d %H:%M:%S")),
            "modified": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        self.profile_manager.player_profiles[self.current_profile_id] = profile
        self.profile_manager.save_player_profiles()
        self.refresh_profiles_list()

        profile_ids = list(self.profile_manager.player_profiles.keys())
        if self.current_profile_id in profile_ids:
            index = profile_ids.index(self.current_profile_id)
            self.profiles_listbox.selection_set(index)

        messagebox.showinfo("Success", f"Profile saved for {name}")

    def delete_profile(self):
        selection = self.profiles_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a profile to delete.")
            return

        profile_ids = list(self.profile_manager.player_profiles.keys())
        profile_id = profile_ids[selection[0]]
        profile_name = self.profile_manager.player_profiles[profile_id]["name"]

        if messagebox.askyesno("Confirm Delete",
                              f"Are you sure you want to delete the profile for {profile_name}?"):
            del self.profile_manager.player_profiles[profile_id]
            self.profile_manager.save_player_profiles()
            self.refresh_profiles_list()

            if not self.profile_manager.player_profiles:
                self.new_profile()
                self.enable_form(False)

            messagebox.showinfo("Success", f"Profile for {profile_name} has been deleted.")

    def duplicate_profile(self):
        selection = self.profiles_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a profile to duplicate.")
            return

        profile_ids = list(self.profile_manager.player_profiles.keys())
        original_id = profile_ids[selection[0]]
        original_profile = self.profile_manager.player_profiles[original_id].copy()

        original_name = original_profile["name"]
        new_name = f"{original_name} (Copy)"
        timestamp = str(int(time.time()))
        new_id = f"{sanitize_profile_id(new_name)}_{timestamp}"

        original_profile["name"] = new_name
        original_profile["created"] = time.strftime("%Y-%m-%d %H:%M:%S")
        original_profile["modified"] = time.strftime("%Y-%m-%d %H:%M:%S")

        self.profile_manager.player_profiles[new_id] = original_profile
        self.profile_manager.save_player_profiles()
        self.refresh_profiles_list()

        messagebox.showinfo("Success", f"Profile duplicated as '{new_name}'")

    def revert_changes(self):
        if self.current_profile_id and self.current_profile_id in self.profile_manager.player_profiles:
            self.load_profile_details(self.current_profile_id)
        else:
            self.new_profile()
