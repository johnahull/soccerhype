#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""
Migrate a legacy (v1) athlete folder to multi-project (v2) structure.

This script handles the conversion of athlete folders from the legacy structure
to the new multi-project structure, preserving all data.

Usage:
    python migrate_athlete.py "athletes/Phia Hull - Dec Highlight"
    python migrate_athlete.py --dry-run "athletes/Phia Hull - Dec Highlight"
    python migrate_athlete.py --all  # Migrate all legacy folders

The migration:
1. Parses folder name: "Athlete - Project" → athlete_name, project_name
2. Creates new v2 structure if athlete folder doesn't exist
3. Creates athlete.json from project.json["player"]
4. Moves clips_in/, work/, output/ to projects/<name>/
5. Moves intro/ to athlete level (if not already there)
6. Updates project.json (removes player field, adds schema_version)
"""

import argparse
import json
import pathlib
import re
import shutil
import sys
from typing import Tuple, Optional, List

from utils.structure import (
    is_v2_structure,
    create_v2_structure,
    SCHEMA_VERSION,
)

ROOT = pathlib.Path.cwd() / "athletes"


def parse_legacy_name(folder_name: str) -> Tuple[str, str]:
    """
    Parse legacy folder name into athlete name and project name.

    Patterns supported:
    - "Athlete Name - Project Name" → ("Athlete Name", "Project Name")
    - "Athlete Name" → ("Athlete Name", "Default")

    Returns:
        Tuple of (athlete_name, project_name)

    Raises:
        ValueError: If names contain path traversal characters
    """
    # Try to split on " - " (with spaces around hyphen)
    if " - " in folder_name:
        parts = folder_name.split(" - ", 1)
        athlete_name, project_name = parts[0].strip(), parts[1].strip()
    else:
        # No separator found, use folder name as athlete and default project
        athlete_name, project_name = folder_name.strip(), "Default"

    # Validate no path traversal characters
    for name, label in [(athlete_name, "Athlete"), (project_name, "Project")]:
        if "/" in name or "\\" in name or name.startswith(".") or name in (".", ".."):
            raise ValueError(f"{label} name contains invalid characters: {name}")

    return athlete_name, project_name


def _atomic_write_json(path: pathlib.Path, data: dict) -> None:
    """Write JSON atomically using temp file + rename pattern."""
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(path)


def find_legacy_folders() -> List[pathlib.Path]:
    """Find all v1 (legacy) athlete folders."""
    if not ROOT.exists():
        return []

    legacy = []
    for p in ROOT.iterdir():
        if p.is_dir() and not is_v2_structure(p):
            # Check if it has the v1 structure markers
            if (p / "clips_in").exists() or (p / "project.json").exists():
                legacy.append(p)

    return sorted(legacy)


def migrate_athlete(
    source_dir: pathlib.Path,
    dry_run: bool = False,
    force: bool = False
) -> dict:
    """
    Migrate a legacy athlete folder to v2 structure.

    Args:
        source_dir: Path to the legacy athlete folder
        dry_run: If True, only show what would be done
        force: If True, overwrite existing target

    Returns:
        Dictionary with migration results:
        {
            "success": bool,
            "athlete_name": str,
            "project_name": str,
            "athlete_dir": Path,
            "project_dir": Path,
            "actions": [list of actions taken]
        }
    """
    result = {
        "success": False,
        "athlete_name": "",
        "project_name": "",
        "athlete_dir": None,
        "project_dir": None,
        "actions": []
    }

    source_dir = source_dir.resolve()

    if not source_dir.exists():
        result["actions"].append(f"ERROR: Source folder not found: {source_dir}")
        return result

    if is_v2_structure(source_dir):
        result["actions"].append(f"SKIP: Already v2 structure: {source_dir}")
        return result

    # Parse folder name
    athlete_name, project_name = parse_legacy_name(source_dir.name)
    result["athlete_name"] = athlete_name
    result["project_name"] = project_name

    # Determine target paths
    athlete_dir = ROOT / athlete_name
    project_dir = athlete_dir / "projects" / project_name

    result["athlete_dir"] = athlete_dir
    result["project_dir"] = project_dir

    # Check if source is already the athlete dir (no name parsing needed)
    is_same_location = source_dir == athlete_dir

    # Check for conflicts
    if project_dir.exists() and not force:
        result["actions"].append(f"ERROR: Target project already exists: {project_dir}")
        result["actions"].append("Use --force to overwrite")
        return result

    # Load existing data
    project_json_path = source_dir / "project.json"
    player_data = {}
    project_data = {}

    if project_json_path.exists():
        try:
            project_data = json.loads(project_json_path.read_text())
            player_data = project_data.pop("player", {})
        except json.JSONDecodeError as e:
            result["actions"].append(f"ERROR: Invalid project.json: {e}")
            return result

    # Set player name from folder if not in project.json
    if not player_data.get("name"):
        player_data["name"] = athlete_name

    # Plan the migration
    actions = []

    if not athlete_dir.exists() or not is_same_location:
        actions.append(f"CREATE: Athlete directory: {athlete_dir}")

    if not (athlete_dir / "athlete.json").exists():
        actions.append(f"CREATE: athlete.json with player profile")

    if not is_same_location:
        # Moving to new location
        actions.append(f"CREATE: Project directory: {project_dir}")
        actions.append(f"MOVE: clips_in/ → {project_dir}/clips_in/")
        actions.append(f"MOVE: work/ → {project_dir}/work/")
        actions.append(f"MOVE: output/ → {project_dir}/output/")

        if (source_dir / "intro").exists():
            if (athlete_dir / "intro").exists():
                actions.append(f"MERGE: intro/ files to {athlete_dir}/intro/")
            else:
                actions.append(f"MOVE: intro/ → {athlete_dir}/intro/")

        actions.append(f"UPDATE: project.json (remove player, add schema_version)")
        actions.append(f"DELETE: Empty source folder: {source_dir}")
    else:
        # Converting in place
        actions.append(f"CREATE: projects/ directory")
        actions.append(f"MOVE: clips_in/ → projects/{project_name}/clips_in/")
        actions.append(f"MOVE: work/ → projects/{project_name}/work/")
        actions.append(f"MOVE: output/ → projects/{project_name}/output/")
        actions.append(f"UPDATE: project.json (remove player, add schema_version)")

    result["actions"] = actions

    if dry_run:
        result["success"] = True
        return result

    # Execute the migration
    try:
        # Create athlete directory structure
        if not athlete_dir.exists():
            athlete_dir.mkdir(parents=True, exist_ok=True)

        # Create or update athlete.json
        athlete_json_path = athlete_dir / "athlete.json"
        if not athlete_json_path.exists():
            player_data["schema_version"] = SCHEMA_VERSION
            _atomic_write_json(athlete_json_path, player_data)

        # Create projects directory
        (athlete_dir / "projects").mkdir(exist_ok=True)

        # Create project directory
        project_dir.mkdir(parents=True, exist_ok=True)

        # Move/copy content
        for folder_name in ["clips_in", "work", "output"]:
            src = source_dir / folder_name
            dst = project_dir / folder_name
            if src.exists():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.move(str(src), str(dst))

        # Handle intro folder
        src_intro = source_dir / "intro"
        dst_intro = athlete_dir / "intro"
        if src_intro.exists():
            if dst_intro.exists():
                # Merge files
                for f in src_intro.iterdir():
                    target = dst_intro / f.name
                    if not target.exists():
                        shutil.move(str(f), str(target))
                shutil.rmtree(src_intro)
            else:
                shutil.move(str(src_intro), str(dst_intro))

        # Update project.json
        project_data["schema_version"] = SCHEMA_VERSION
        project_data["project_name"] = project_name
        project_json_dst = project_dir / "project.json"
        _atomic_write_json(project_json_dst, project_data)

        # Remove old project.json if in different location
        if not is_same_location and project_json_path.exists():
            project_json_path.unlink()

        # Remove empty source directory
        if not is_same_location:
            try:
                # Remove only if empty
                remaining = list(source_dir.iterdir())
                if not remaining:
                    source_dir.rmdir()
                elif remaining == [source_dir / "project.json"]:
                    (source_dir / "project.json").unlink()
                    source_dir.rmdir()
            except OSError:
                result["actions"].append(f"NOTE: Could not remove source directory (not empty)")

        result["success"] = True

    except Exception as e:
        result["actions"].append(f"ERROR: Migration failed: {e}")
        result["success"] = False

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Migrate legacy athlete folders to v2 multi-project structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate_athlete.py "athletes/Phia Hull - Dec Highlight"
  python migrate_athlete.py --dry-run "athletes/Phia Hull - Dec Highlight"
  python migrate_athlete.py --all
  python migrate_athlete.py --all --dry-run
        """
    )
    parser.add_argument("folder", nargs="?", help="Path to legacy athlete folder")
    parser.add_argument("--all", action="store_true",
                       help="Migrate all legacy folders")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would change without modifying anything")
    parser.add_argument("--force", action="store_true",
                       help="Overwrite existing target folders")

    args = parser.parse_args()

    if not args.folder and not args.all:
        parser.print_help()
        print("\n\nLegacy folders found:")
        legacy = find_legacy_folders()
        if legacy:
            for f in legacy:
                athlete, project = parse_legacy_name(f.name)
                print(f"  • {f.name}")
                print(f"    → Athlete: {athlete}, Project: {project}")
        else:
            print("  (none)")
        sys.exit(0)

    # Collect folders to migrate
    folders = []
    if args.all:
        folders = find_legacy_folders()
        if not folders:
            print("No legacy folders found to migrate.")
            sys.exit(0)
    else:
        folder_path = pathlib.Path(args.folder)
        if not folder_path.is_absolute():
            # Try as relative to athletes/
            if (ROOT / args.folder).exists():
                folder_path = ROOT / args.folder
            elif (ROOT.parent / args.folder).exists():
                folder_path = (ROOT.parent / args.folder).resolve()
        folders = [folder_path]

    # Run migrations
    if args.dry_run:
        print("DRY RUN - No changes will be made\n")

    success_count = 0
    for folder in folders:
        print(f"\n{'='*60}")
        print(f"Migrating: {folder.name}")
        print(f"{'='*60}")

        result = migrate_athlete(folder, dry_run=args.dry_run, force=args.force)

        for action in result["actions"]:
            prefix = "  "
            if action.startswith("ERROR"):
                prefix = "  ❌ "
            elif action.startswith("SKIP"):
                prefix = "  ⏭️ "
            elif action.startswith("NOTE"):
                prefix = "  ℹ️ "
            else:
                prefix = "  ✓ " if not args.dry_run else "  → "
            print(f"{prefix}{action}")

        if result["success"]:
            if result["athlete_name"]:
                print(f"\n  Athlete: {result['athlete_name']}")
                print(f"  Project: {result['project_name']}")
            success_count += 1

    print(f"\n{'='*60}")
    print(f"Migration complete: {success_count}/{len(folders)} successful")
    if args.dry_run:
        print("(This was a dry run - no changes were made)")


if __name__ == "__main__":
    main()
