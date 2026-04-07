# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Athlete and project CRUD API endpoints."""

from __future__ import annotations

import pathlib
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.structure import (
    detect_structure,
    is_v2_structure,
    create_v2_structure,
    create_project,
    list_projects,
    get_athlete_profile,
    save_athlete_profile,
    get_project_data,
)
from clip_sync import is_clip_marked

ROOT = pathlib.Path.cwd()
ATHLETES = ROOT / "athletes"

router = APIRouter()


class CreateAthleteBody(BaseModel):
    name: str


class CreateProjectBody(BaseModel):
    name: str


class ProfileUpdate(BaseModel):
    data: dict[str, Any]


def _athlete_dir(name: str) -> pathlib.Path:
    safe = pathlib.Path(name)
    if safe.parts != (name,):
        raise HTTPException(400, "Invalid athlete name")
    d = (ATHLETES / name).resolve()
    if not str(d).startswith(str(ATHLETES.resolve())):
        raise HTTPException(400, "Invalid athlete name")
    return d


@router.get("/athletes")
async def list_athletes():
    """List all athletes with project counts and structure info."""
    if not ATHLETES.exists():
        return []
    results = []
    for p in sorted(ATHLETES.iterdir()):
        if not p.is_dir() or p.name.startswith("."):
            continue
        structure = detect_structure(p)
        projects = list_projects(p)
        profile = get_athlete_profile(p)

        project_summaries = []
        for proj_dir in projects:
            pdata = get_project_data(proj_dir)
            clips = pdata.get("clips", [])
            marked = sum(1 for c in clips if is_clip_marked(c))
            has_output = (proj_dir / "output" / "final.mp4").exists()
            project_summaries.append({
                "name": proj_dir.name if structure == "v2" else "(default)",
                "clip_count": len(clips),
                "marked_count": marked,
                "rendered": has_output,
            })

        results.append({
            "name": p.name,
            "structure": structure,
            "profile": profile,
            "projects": project_summaries,
        })
    return results


@router.post("/athletes")
async def create_athlete(body: CreateAthleteBody):
    """Create a new v2 athlete."""
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Name cannot be empty")
    if "/" in name or "\\" in name:
        raise HTTPException(400, "Name cannot contain path separators")

    athlete_dir = ATHLETES / name
    if athlete_dir.exists():
        raise HTTPException(409, f"Athlete '{name}' already exists")

    ATHLETES.mkdir(parents=True, exist_ok=True)
    athlete_dir.mkdir()
    create_v2_structure(athlete_dir, {"name": name})
    return {"name": name, "structure": "v2"}


@router.get("/athletes/{name}/projects")
async def get_projects(name: str):
    """List projects for an athlete."""
    athlete_dir = _athlete_dir(name)
    if not athlete_dir.exists():
        raise HTTPException(404, f"Athlete '{name}' not found")

    projects = list_projects(athlete_dir)
    structure = detect_structure(athlete_dir)
    results = []
    for proj_dir in projects:
        pdata = get_project_data(proj_dir)
        clips = pdata.get("clips", [])
        marked = sum(1 for c in clips if is_clip_marked(c))
        has_output = (proj_dir / "output" / "final.mp4").exists()
        results.append({
            "name": proj_dir.name if structure == "v2" else "(default)",
            "clip_count": len(clips),
            "marked_count": marked,
            "rendered": has_output,
        })
    return results


@router.post("/athletes/{name}/projects")
async def create_new_project(name: str, body: CreateProjectBody):
    """Create a new project for an athlete."""
    athlete_dir = _athlete_dir(name)
    if not athlete_dir.exists():
        raise HTTPException(404, f"Athlete '{name}' not found")

    if not is_v2_structure(athlete_dir):
        raise HTTPException(400, "Cannot create projects for v1 athletes. Migrate to v2 first.")

    project_name = body.name.strip()
    if not project_name:
        raise HTTPException(400, "Project name cannot be empty")

    try:
        project_dir = create_project(athlete_dir, project_name)
    except FileExistsError:
        raise HTTPException(409, f"Project '{project_name}' already exists")
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {"name": project_name, "path": str(project_dir)}


@router.get("/athletes/{name}/profile")
async def get_profile(name: str):
    """Get athlete profile."""
    athlete_dir = _athlete_dir(name)
    if not athlete_dir.exists():
        raise HTTPException(404, f"Athlete '{name}' not found")
    return get_athlete_profile(athlete_dir)


@router.put("/athletes/{name}/profile")
async def update_profile(name: str, body: ProfileUpdate):
    """Update athlete profile fields."""
    athlete_dir = _athlete_dir(name)
    if not athlete_dir.exists():
        raise HTTPException(404, f"Athlete '{name}' not found")

    profile = get_athlete_profile(athlete_dir)
    profile.update(body.data)
    save_athlete_profile(athlete_dir, profile)
    return profile
