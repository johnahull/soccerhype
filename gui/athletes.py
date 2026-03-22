"""Athlete management for the SoccerHype GUI."""

import json
import pathlib
from typing import Dict, List

from clip_sync import is_clip_marked
from utils.structure import (
    is_v2_structure,
    get_athlete_profile,
    get_project_data,
    list_projects,
    create_project,
    create_v2_structure,
)
from gui.utils import ATHLETES, ERROR_HANDLING_AVAILABLE

if ERROR_HANDLING_AVAILABLE:
    from utils.error_handling import ErrorHandler, error_handler, ValidationHelper


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
        """Check athlete status with error handling (supports both v1 and v2)."""
        @error_handler("Checking athlete status", show_dialog=False)
        def _get_status():
            if ERROR_HANDLING_AVAILABLE:
                ValidationHelper.validate_directory(athlete_dir)
            return self._compute_athlete_status(athlete_dir)
        return _get_status()

    def _get_athlete_status_basic(self, athlete_dir: pathlib.Path) -> Dict[str, bool]:
        """Check athlete status without error handling (supports both v1 and v2)."""
        try:
            return self._compute_athlete_status(athlete_dir)
        except Exception:
            return {
                "is_v2": False, "project_count": 0, "has_clips": False,
                "has_project": False, "has_profile": False, "has_final": False,
                "all_clips_marked": False, "clips_count": 0, "marked_count": 0,
                "needs_marking": False, "needs_rendering": False
            }

    def _compute_athlete_status(self, athlete_dir: pathlib.Path) -> Dict:
        """Core status computation shared by both error handling paths."""
        v2 = is_v2_structure(athlete_dir)
        projects = list_projects(athlete_dir) if v2 else [athlete_dir]

        total_clips = 0
        total_marked = 0
        any_has_clips = False
        any_has_project = False
        all_have_final = True
        any_needs_marking = False
        any_needs_rendering = False

        for project_dir in projects:
            project_file = project_dir / "project.json"
            final_video = project_dir / "output" / "final.mp4"
            clips_in = project_dir / "clips_in"

            has_clips = clips_in.exists() and any(clips_in.iterdir()) if clips_in.exists() else False
            has_project = project_file.exists()
            has_final = final_video.exists()

            if has_clips:
                any_has_clips = True
            if has_project:
                any_has_project = True
            if not has_final:
                all_have_final = False

            if has_project:
                try:
                    project_data = get_project_data(project_dir)
                    clips = project_data.get("clips", [])
                    total_clips += len(clips)
                    marked = sum(1 for clip in clips if is_clip_marked(clip))
                    total_marked += marked
                    if has_clips and (len(clips) == 0 or marked < len(clips)):
                        any_needs_marking = True
                    if marked == len(clips) and len(clips) > 0 and not has_final:
                        any_needs_rendering = True
                except (IOError, json.JSONDecodeError):
                    pass

        has_profile = False
        if v2:
            profile = get_athlete_profile(athlete_dir)
            has_profile = bool(profile.get("name", "").strip())
        elif projects and (projects[0] / "project.json").exists():
            try:
                project_data = json.loads((projects[0] / "project.json").read_text())
                has_profile = bool(project_data.get("player", {}).get("name", "").strip())
            except (IOError, json.JSONDecodeError):
                pass

        return {
            "is_v2": v2,
            "project_count": len(projects),
            "has_clips": any_has_clips,
            "has_project": any_has_project,
            "has_profile": has_profile,
            "has_final": all_have_final and len(projects) > 0,
            "all_clips_marked": total_clips > 0 and total_marked == total_clips,
            "clips_count": total_clips,
            "marked_count": total_marked,
            "needs_marking": any_needs_marking,
            "needs_rendering": any_needs_rendering
        }

    def create_athlete(self, name: str) -> pathlib.Path:
        """Create new athlete folder structure"""
        if ERROR_HANDLING_AVAILABLE:
            return self._create_athlete_with_error_handling(name)
        else:
            return self._create_athlete_basic(name)

    def _create_athlete_with_error_handling(self, name: str) -> pathlib.Path:
        """Create athlete with error handling (v2 structure with default project)"""
        @error_handler("Creating athlete folder")
        def _create():
            if not name or not name.strip():
                raise ValueError("Athlete name cannot be empty")
            athlete_dir = ATHLETES / name.strip()
            if athlete_dir.exists():
                raise FileExistsError(f"Athlete '{name}' already exists")
            if ERROR_HANDLING_AVAILABLE:
                ValidationHelper.validate_disk_space(ATHLETES, 1024 * 1024 * 1024)
            create_v2_structure(athlete_dir, {"name": name.strip()})
            create_project(athlete_dir, "Default")
            return athlete_dir
        return _create()

    def _create_athlete_basic(self, name: str) -> pathlib.Path:
        """Create athlete without error handling (v2 structure with default project)"""
        if not name or not name.strip():
            raise ValueError("Athlete name cannot be empty")
        athlete_dir = ATHLETES / name.strip()
        if athlete_dir.exists():
            raise FileExistsError(f"Athlete '{name}' already exists")
        create_v2_structure(athlete_dir, {"name": name.strip()})
        create_project(athlete_dir, "Default")
        return athlete_dir

    def is_v2_athlete(self, athlete_dir: pathlib.Path) -> bool:
        """Check if athlete uses v2 (multi-project) structure."""
        return is_v2_structure(athlete_dir)

    def discover_projects(self, athlete_dir: pathlib.Path) -> List[pathlib.Path]:
        """List all projects for an athlete."""
        return list_projects(athlete_dir)

    def get_project_status(self, project_dir: pathlib.Path) -> Dict:
        """Get status for a specific project (works for both v1 and v2)."""
        project_file = project_dir / "project.json"
        final_video = project_dir / "output" / "final.mp4"
        clips_in = project_dir / "clips_in"

        has_clips = clips_in.exists() and any(clips_in.iterdir()) if clips_in.exists() else False
        has_project = project_file.exists()
        has_final = final_video.exists()

        clips_count = 0
        marked_count = 0
        all_clips_marked = False

        if has_project:
            try:
                project_data = get_project_data(project_dir)
                clips = project_data.get("clips", [])
                clips_count = len(clips)
                marked_count = sum(1 for clip in clips if is_clip_marked(clip))
                all_clips_marked = clips_count > 0 and marked_count == clips_count
            except (IOError, json.JSONDecodeError):
                pass

        return {
            "has_clips": has_clips,
            "has_project": has_project,
            "has_final": has_final,
            "clips_count": clips_count,
            "marked_count": marked_count,
            "all_clips_marked": all_clips_marked,
            "needs_marking": has_clips and (not has_project or not all_clips_marked),
            "needs_rendering": has_project and all_clips_marked and not has_final
        }

    def create_project_for_athlete(self, athlete_dir: pathlib.Path, project_name: str) -> pathlib.Path:
        """Create a new project under an athlete."""
        if not is_v2_structure(athlete_dir):
            profile = get_athlete_profile(athlete_dir)
            if not profile.get("name"):
                profile["name"] = athlete_dir.name
            create_v2_structure(athlete_dir, profile)
        return create_project(athlete_dir, project_name)

    def load_athlete_profile(self, athlete_dir: pathlib.Path) -> Dict:
        """Load athlete profile (works for both v1 and v2)."""
        return get_athlete_profile(athlete_dir)
