#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Tests for create_athlete.py - directory structure creation."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.structure import create_v2_structure, create_project


class TestCreateV2Structure:
    def test_creates_athlete_json(self, tmp_path):
        athlete_dir = tmp_path / "Test Athlete"
        create_v2_structure(athlete_dir, {"name": "Test Athlete"})

        athlete_json = athlete_dir / "athlete.json"
        assert athlete_json.exists()
        data = json.loads(athlete_json.read_text())
        assert data["name"] == "Test Athlete"
        assert data["schema_version"] == "2.0"

    def test_creates_intro_dir(self, tmp_path):
        athlete_dir = tmp_path / "Test Athlete"
        create_v2_structure(athlete_dir, {"name": "Test Athlete"})
        assert (athlete_dir / "intro").is_dir()

    def test_creates_projects_dir(self, tmp_path):
        athlete_dir = tmp_path / "Test Athlete"
        create_v2_structure(athlete_dir, {"name": "Test Athlete"})
        assert (athlete_dir / "projects").is_dir()

    def test_preserves_extra_profile_fields(self, tmp_path):
        athlete_dir = tmp_path / "Test"
        profile = {
            "name": "Test",
            "position": "MF",
            "grad_year": "2026",
            "club_team": "FC Test",
        }
        create_v2_structure(athlete_dir, profile)
        data = json.loads((athlete_dir / "athlete.json").read_text())
        assert data["position"] == "MF"
        assert data["grad_year"] == "2026"
        assert data["club_team"] == "FC Test"


class TestCreateProject:
    def test_creates_project_structure(self, tmp_path):
        athlete_dir = tmp_path / "Athlete"
        create_v2_structure(athlete_dir, {"name": "Athlete"})

        proj = create_project(athlete_dir, "Fall 2025")
        assert proj.exists()
        assert (proj / "clips_in").is_dir()
        assert (proj / "work" / "proxies").is_dir()
        assert (proj / "output").is_dir()

    def test_creates_project_json(self, tmp_path):
        athlete_dir = tmp_path / "Athlete"
        create_v2_structure(athlete_dir, {"name": "Athlete"})

        proj = create_project(athlete_dir, "Spring 2026")
        pj = proj / "project.json"
        assert pj.exists()
        data = json.loads(pj.read_text())
        assert data["project_name"] == "Spring 2026"
        assert data["schema_version"] == "2.0"
        assert isinstance(data.get("clips"), list)

    def test_duplicate_project_raises(self, tmp_path):
        athlete_dir = tmp_path / "Athlete"
        create_v2_structure(athlete_dir, {"name": "Athlete"})
        create_project(athlete_dir, "Test")

        with pytest.raises((FileExistsError, ValueError, OSError)):
            create_project(athlete_dir, "Test")
