#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Tests for utils/structure.py - structure detection and path resolution."""

import json
import tempfile
from pathlib import Path

import pytest
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.structure import (
    detect_structure,
    is_v2_structure,
    is_legacy_structure,
    resolve_athlete_dir,
    resolve_project_dir,
    get_athlete_profile,
    get_project_data,
    list_projects,
    create_project,
    create_v2_structure,
)


@pytest.fixture
def tmp_athletes(tmp_path):
    """Create a temporary athletes directory."""
    athletes = tmp_path / "athletes"
    athletes.mkdir()
    return athletes


def _make_v1(athletes_dir: Path, name: str) -> Path:
    """Create a v1 (legacy) athlete structure."""
    d = athletes_dir / name
    (d / "clips_in").mkdir(parents=True)
    (d / "intro").mkdir()
    (d / "work" / "proxies").mkdir(parents=True)
    (d / "output").mkdir()
    project = {"player": {"name": name}, "clips": []}
    (d / "project.json").write_text(json.dumps(project))
    return d


def _make_v2(athletes_dir: Path, name: str, projects: list[str] | None = None) -> Path:
    """Create a v2 (multi-project) athlete structure."""
    d = athletes_dir / name
    d.mkdir(parents=True)
    (d / "intro").mkdir()
    athlete_data = {"schema_version": "2.0", "name": name}
    (d / "athlete.json").write_text(json.dumps(athlete_data))
    (d / "projects").mkdir()

    for proj_name in (projects or ["Default"]):
        p = d / "projects" / proj_name
        (p / "clips_in").mkdir(parents=True)
        (p / "work" / "proxies").mkdir(parents=True)
        (p / "output").mkdir()
        proj_data = {"schema_version": "2.0", "project_name": proj_name, "clips": []}
        (p / "project.json").write_text(json.dumps(proj_data))

    return d


class TestDetectStructure:
    def test_v1_detected(self, tmp_athletes):
        d = _make_v1(tmp_athletes, "Jane Smith")
        assert detect_structure(d) == "v1"
        assert is_legacy_structure(d)
        assert not is_v2_structure(d)

    def test_v2_detected(self, tmp_athletes):
        d = _make_v2(tmp_athletes, "Jane Smith")
        assert detect_structure(d) == "v2"
        assert is_v2_structure(d)
        assert not is_legacy_structure(d)

    def test_v2_detected_from_project_subdir(self, tmp_athletes):
        d = _make_v2(tmp_athletes, "Jane Smith", ["Fall 2025"])
        proj_dir = d / "projects" / "Fall 2025"
        assert detect_structure(proj_dir) == "v2"

    def test_empty_dir_defaults_to_v1(self, tmp_athletes):
        d = tmp_athletes / "empty"
        d.mkdir()
        assert detect_structure(d) == "v1"


class TestResolveAthleteDir:
    def test_resolve_from_athlete_root(self, tmp_athletes):
        d = _make_v1(tmp_athletes, "test_athlete")
        result = resolve_athlete_dir(d)
        assert result is not None
        assert result.name == "test_athlete"

    def test_resolve_from_project_subdir(self, tmp_athletes):
        d = _make_v2(tmp_athletes, "test_athlete", ["Spring 2026"])
        proj = d / "projects" / "Spring 2026"
        result = resolve_athlete_dir(proj)
        assert result is not None
        assert result.name == "test_athlete"


class TestGetAthleteProfile:
    def test_v2_profile(self, tmp_athletes):
        d = _make_v2(tmp_athletes, "Jane Smith")
        profile = get_athlete_profile(d)
        assert profile["name"] == "Jane Smith"
        assert profile.get("schema_version") == "2.0"

    def test_v1_profile(self, tmp_athletes):
        d = _make_v1(tmp_athletes, "Jane Smith")
        profile = get_athlete_profile(d)
        assert profile["name"] == "Jane Smith"

    def test_missing_profile_returns_empty(self, tmp_athletes):
        d = tmp_athletes / "nobody"
        d.mkdir()
        profile = get_athlete_profile(d)
        assert profile == {} or profile.get("name", "") == ""


class TestListProjects:
    def test_v2_lists_projects(self, tmp_athletes):
        d = _make_v2(tmp_athletes, "Jane", ["Fall 2025", "Spring 2026"])
        projects = list_projects(d)
        names = [p.name for p in projects]
        assert "Fall 2025" in names
        assert "Spring 2026" in names

    def test_v1_returns_athlete_dir(self, tmp_athletes):
        d = _make_v1(tmp_athletes, "Jane")
        projects = list_projects(d)
        assert len(projects) == 1
        assert projects[0] == d


class TestGetProjectData:
    def test_reads_project_json(self, tmp_athletes):
        d = _make_v2(tmp_athletes, "Jane", ["Test Project"])
        proj = d / "projects" / "Test Project"
        data = get_project_data(proj)
        assert data["project_name"] == "Test Project"
        assert "clips" in data

    def test_v1_reads_project_json(self, tmp_athletes):
        d = _make_v1(tmp_athletes, "Jane")
        data = get_project_data(d)
        assert "player" in data
        assert "clips" in data


class TestCreateV2Structure:
    def test_creates_structure(self, tmp_athletes):
        d = tmp_athletes / "New Athlete"
        create_v2_structure(d, {"name": "New Athlete"})
        assert (d / "athlete.json").exists()
        assert (d / "intro").exists()
        assert (d / "projects").exists()

        profile = json.loads((d / "athlete.json").read_text())
        assert profile["name"] == "New Athlete"
        assert profile["schema_version"] == "2.0"


class TestCreateProject:
    def test_creates_project_dirs(self, tmp_athletes):
        d = _make_v2(tmp_athletes, "Jane", [])
        proj = create_project(d, "New Season")
        assert proj.exists()
        assert (proj / "clips_in").exists()
        assert (proj / "project.json").exists()

        data = json.loads((proj / "project.json").read_text())
        assert data["project_name"] == "New Season"
