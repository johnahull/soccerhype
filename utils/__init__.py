# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""
SoccerHype utilities package.
"""

from .structure import (
    detect_structure,
    is_legacy_structure,
    is_v2_structure,
    resolve_athlete_dir,
    resolve_project_dir,
    get_athlete_profile,
    get_project_data,
    save_project_data,
    save_athlete_profile,
    list_projects,
    get_intro_dir,
    SCHEMA_VERSION,
)

__all__ = [
    "detect_structure",
    "is_legacy_structure",
    "is_v2_structure",
    "resolve_athlete_dir",
    "resolve_project_dir",
    "get_athlete_profile",
    "get_project_data",
    "save_project_data",
    "save_athlete_profile",
    "list_projects",
    "get_intro_dir",
    "SCHEMA_VERSION",
]
