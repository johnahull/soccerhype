#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""
Structure detection and path resolution for multi-project athlete folders.

This module provides centralized logic for detecting v1 (legacy) vs v2 (multi-project)
folder structures and resolving paths appropriately.

v1 (Legacy) Structure:
    athletes/<athlete_name>/
        ├─ clips_in/
        ├─ intro/
        ├─ work/proxies/
        ├─ output/
        └─ project.json  (contains both player info and clip data)

v2 (Multi-Project) Structure:
    athletes/<athlete_name>/
        ├─ athlete.json       (shared player profile)
        ├─ intro/             (shared intro media)
        └─ projects/
            └─ <project_name>/
                ├─ clips_in/
                ├─ work/proxies/
                ├─ output/
                └─ project.json  (clip data only, no player info)
"""

from __future__ import annotations

import json
import pathlib
import tempfile
from typing import Dict, Any, List, Optional, Literal

SCHEMA_VERSION = "2.0"

StructureType = Literal["v1", "v2"]


def detect_structure(path: pathlib.Path) -> StructureType:
    """
    Detect whether a path uses v1 (legacy) or v2 (multi-project) structure.

    Args:
        path: Any path within an athlete's folder structure

    Returns:
        "v1" for legacy structure, "v2" for multi-project structure

    The detection logic:
    - If athlete.json exists at the athlete root → v2
    - If projects/ directory exists at the athlete root → v2
    - Otherwise → v1
    """
    athlete_dir = resolve_athlete_dir(path)
    if athlete_dir is None:
        return "v1"  # Default to legacy for unknown paths

    # Check for v2 markers
    if (athlete_dir / "athlete.json").exists():
        return "v2"
    if (athlete_dir / "projects").is_dir():
        return "v2"

    return "v1"


def is_legacy_structure(path: pathlib.Path) -> bool:
    """Check if path uses legacy (v1) structure."""
    return detect_structure(path) == "v1"


def is_v2_structure(path: pathlib.Path) -> bool:
    """Check if path uses multi-project (v2) structure."""
    return detect_structure(path) == "v2"


def resolve_athlete_dir(path: pathlib.Path) -> Optional[pathlib.Path]:
    """
    Find the athlete root directory from any path within the athlete structure.

    Args:
        path: Any path (can be athlete root, project dir, clips_in, etc.)

    Returns:
        Path to athlete root directory, or None if not found

    For v1: athletes/<athlete_name>/
    For v2: athletes/<athlete_name>/ (parent of projects/)
    """
    path = path.resolve()

    # Walk up to find the athletes/ parent
    current = path
    while current != current.parent:
        if current.parent.name == "athletes":
            return current

        # Check if we're inside a projects/ subdirectory (v2)
        if current.parent.name == "projects":
            # Go up one more level to get athlete root
            return current.parent.parent

        current = current.parent

    # If path itself is under athletes/
    if path.name == "athletes":
        return None

    # Try direct parent check
    if path.parent.name == "athletes":
        return path

    return None


def resolve_project_dir(path: pathlib.Path, project_name: Optional[str] = None) -> Optional[pathlib.Path]:
    """
    Find the project directory from any path within the structure.

    Args:
        path: Any path within athlete/project structure
        project_name: Optional project name (required for v2 if path is athlete root)

    Returns:
        Path to project directory (containing clips_in/, project.json, etc.)

    For v1: Same as athlete_dir
    For v2: athletes/<athlete_name>/projects/<project_name>/
    """
    athlete_dir = resolve_athlete_dir(path)
    if athlete_dir is None:
        return None

    structure = detect_structure(athlete_dir)

    if structure == "v1":
        # In v1, athlete_dir IS the project dir
        return athlete_dir

    # v2 structure
    if project_name:
        project_dir = athlete_dir / "projects" / project_name
        return project_dir if project_dir.exists() else None

    # Try to determine project from path
    path = path.resolve()

    # Check if we're already in a project directory
    if path.parent.name == "projects":
        return path

    # Check if we're in a subdirectory of a project
    current = path
    while current != current.parent:
        if current.parent.name == "projects":
            return current
        current = current.parent

    return None


def get_athlete_profile(athlete_dir: pathlib.Path) -> Dict[str, Any]:
    """
    Load the athlete profile (player information).

    Args:
        athlete_dir: Path to athlete root directory

    Returns:
        Dictionary with player information

    For v1: Reads from project.json["player"]
    For v2: Reads from athlete.json
    """
    athlete_dir = athlete_dir.resolve()
    structure = detect_structure(athlete_dir)

    if structure == "v2":
        athlete_json = athlete_dir / "athlete.json"
        if athlete_json.exists():
            return json.loads(athlete_json.read_text())
        return {}

    # v1: Read from project.json
    project_json = athlete_dir / "project.json"
    if project_json.exists():
        data = json.loads(project_json.read_text())
        return data.get("player", {})

    return {}


def get_project_data(project_dir: pathlib.Path) -> Dict[str, Any]:
    """
    Load project data (clips, settings).

    Args:
        project_dir: Path to project directory

    Returns:
        Dictionary with project data including clips

    For v1: Reads from project.json (includes player info)
    For v2: Reads from project.json (no player info)
    """
    project_json = project_dir / "project.json"
    if project_json.exists():
        return json.loads(project_json.read_text())
    return {}


def save_project_data(project_dir: pathlib.Path, data: Dict[str, Any]) -> None:
    """
    Save project data atomically.

    Args:
        project_dir: Path to project directory
        data: Project data to save
    """
    project_json = project_dir / "project.json"
    _atomic_write_json(project_json, data)


def save_athlete_profile(athlete_dir: pathlib.Path, profile: Dict[str, Any]) -> None:
    """
    Save athlete profile atomically.

    Args:
        athlete_dir: Path to athlete root directory
        profile: Player profile data to save

    For v2: Writes to athlete.json
    For v1: Updates project.json["player"]
    """
    athlete_dir = athlete_dir.resolve()
    structure = detect_structure(athlete_dir)

    if structure == "v2":
        athlete_json = athlete_dir / "athlete.json"
        # Ensure schema version is set
        profile["schema_version"] = SCHEMA_VERSION
        _atomic_write_json(athlete_json, profile)
    else:
        # v1: Update project.json
        project_json = athlete_dir / "project.json"
        if project_json.exists():
            data = json.loads(project_json.read_text())
        else:
            data = {}
        data["player"] = profile
        _atomic_write_json(project_json, data)


def list_projects(athlete_dir: pathlib.Path) -> List[pathlib.Path]:
    """
    List all projects for an athlete.

    Args:
        athlete_dir: Path to athlete root directory

    Returns:
        List of project directory paths

    For v1: Returns [athlete_dir] (single implicit project)
    For v2: Returns list of project directories under projects/
    """
    athlete_dir = athlete_dir.resolve()
    structure = detect_structure(athlete_dir)

    if structure == "v1":
        # In v1, the athlete dir IS the project
        return [athlete_dir]

    # v2: List directories under projects/
    projects_dir = athlete_dir / "projects"
    if not projects_dir.exists():
        return []

    return sorted([
        p for p in projects_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ])


def get_intro_dir(path: pathlib.Path) -> pathlib.Path:
    """
    Get the intro media directory for an athlete.

    Args:
        path: Any path within athlete structure

    Returns:
        Path to intro directory (shared at athlete level for v2)

    For v1: athletes/<athlete_name>/intro/
    For v2: athletes/<athlete_name>/intro/ (shared across projects)
    """
    athlete_dir = resolve_athlete_dir(path)
    if athlete_dir is None:
        raise ValueError(f"Could not determine athlete directory from path: {path}")

    return athlete_dir / "intro"


def get_merged_project_data(project_dir: pathlib.Path) -> Dict[str, Any]:
    """
    Get project data merged with athlete profile (for display/rendering).

    Args:
        project_dir: Path to project directory

    Returns:
        Dictionary with merged data (clips + player info)
    """
    athlete_dir = resolve_athlete_dir(project_dir)
    if athlete_dir is None:
        return get_project_data(project_dir)

    structure = detect_structure(athlete_dir)
    project_data = get_project_data(project_dir)

    if structure == "v2":
        # Merge athlete profile into project data
        profile = get_athlete_profile(athlete_dir)
        return {
            **project_data,
            "player": profile,
        }

    # v1: project data already includes player
    return project_data


def create_v2_structure(athlete_dir: pathlib.Path, profile: Optional[Dict[str, Any]] = None) -> None:
    """
    Initialize v2 (multi-project) folder structure for an athlete.

    Args:
        athlete_dir: Path to athlete root directory
        profile: Optional player profile to save
    """
    athlete_dir = athlete_dir.resolve()

    # Create directories
    (athlete_dir / "intro").mkdir(parents=True, exist_ok=True)
    (athlete_dir / "projects").mkdir(parents=True, exist_ok=True)

    # Create athlete.json
    if profile is None:
        profile = {"name": athlete_dir.name}

    profile["schema_version"] = SCHEMA_VERSION
    _atomic_write_json(athlete_dir / "athlete.json", profile)


def create_project(athlete_dir: pathlib.Path, project_name: str) -> pathlib.Path:
    """
    Create a new project under an athlete (v2 structure).

    Args:
        athlete_dir: Path to athlete root directory
        project_name: Name for the new project

    Returns:
        Path to the created project directory

    Raises:
        ValueError: If athlete doesn't use v2 structure
        FileExistsError: If project already exists
    """
    athlete_dir = athlete_dir.resolve()

    # Ensure v2 structure exists
    if not is_v2_structure(athlete_dir):
        if not (athlete_dir / "projects").exists():
            raise ValueError(f"Athlete '{athlete_dir.name}' uses v1 structure. "
                           "Migrate to v2 first or use create_v2_structure().")

    project_dir = athlete_dir / "projects" / project_name

    if project_dir.exists():
        raise FileExistsError(f"Project '{project_name}' already exists for athlete '{athlete_dir.name}'")

    # Create project directories
    (project_dir / "clips_in").mkdir(parents=True, exist_ok=True)
    (project_dir / "work" / "proxies").mkdir(parents=True, exist_ok=True)
    (project_dir / "output").mkdir(parents=True, exist_ok=True)

    # Create empty project.json
    project_data = {
        "schema_version": SCHEMA_VERSION,
        "project_name": project_name,
        "include_intro": True,
        "intro_media": None,
        "clips": []
    }
    _atomic_write_json(project_dir / "project.json", project_data)

    return project_dir


def _atomic_write_json(path: pathlib.Path, data: Dict[str, Any]) -> None:
    """Write JSON data atomically using temp file + rename pattern."""
    import os

    temp_fd = None
    temp_path = None
    try:
        temp_fd, temp_path_str = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.stem}_",
            suffix=".json.tmp"
        )
        temp_path = pathlib.Path(temp_path_str)

        os.write(temp_fd, json.dumps(data, indent=2).encode('utf-8'))
        os.close(temp_fd)
        temp_fd = None

        temp_path.replace(path)
    finally:
        if temp_fd is not None:
            os.close(temp_fd)
        if temp_path and temp_path.exists():
            temp_path.unlink()
