#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""
Merge multiple legacy athlete folders into a single multi-project athlete.

This script finds all folders matching "Athlete Name - *" pattern and merges
them into a single v2 athlete with multiple projects.

Usage:
    python merge_athletes.py "Phia Hull"
    python merge_athletes.py --dry-run "Phia Hull"
    python merge_athletes.py --list  # Show potential merges

The merge process:
1. Finds all folders matching "Athlete Name - *" pattern
2. Creates v2 athlete folder if needed
3. Merges player profiles (uses most complete profile)
4. Migrates each folder as a separate project
5. Merges intro/ folders (combining all media)
"""

import argparse
import json
import pathlib
import sys
from typing import Dict, List, Any

from utils.structure import (
    is_v2_structure,
    create_v2_structure,
    get_athlete_profile,
    SCHEMA_VERSION,
)

ROOT = pathlib.Path.cwd() / "athletes"


def find_matching_folders(athlete_name: str) -> List[pathlib.Path]:
    """
    Find all folders that match the athlete name pattern.

    Matches:
    - Exact name: "Phia Hull"
    - With project suffix: "Phia Hull - *"
    """
    if not ROOT.exists():
        return []

    matches = []
    name_lower = athlete_name.lower().strip()

    for folder in ROOT.iterdir():
        if not folder.is_dir():
            continue

        folder_name_lower = folder.name.lower()

        # Exact match
        if folder_name_lower == name_lower:
            matches.append(folder)
            continue

        # Pattern match: "Athlete Name - *"
        if folder_name_lower.startswith(f"{name_lower} - "):
            matches.append(folder)
            continue

    return sorted(matches)


def find_all_merge_candidates() -> Dict[str, List[pathlib.Path]]:
    """
    Find all athletes that have multiple legacy folders.

    Returns:
        Dictionary mapping athlete names to their matching folders
    """
    if not ROOT.exists():
        return {}

    # Group folders by base athlete name
    groups: Dict[str, List[pathlib.Path]] = {}

    for folder in ROOT.iterdir():
        if not folder.is_dir():
            continue

        # Skip v2 folders
        if is_v2_structure(folder):
            continue

        name = folder.name
        # Extract base name (before " - ")
        if " - " in name:
            base_name = name.split(" - ", 1)[0].strip()
        else:
            base_name = name.strip()

        if base_name not in groups:
            groups[base_name] = []
        groups[base_name].append(folder)

    # Filter to only those with multiple folders
    return {k: v for k, v in groups.items() if len(v) > 1}


def merge_profiles(profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge multiple player profiles, preferring non-empty values.

    Args:
        profiles: List of player profile dictionaries

    Returns:
        Merged profile with most complete data
    """
    merged = {}

    fields = [
        "name", "title", "position", "grad_year", "club_team",
        "high_school", "height_weight", "gpa", "email", "phone"
    ]

    for field in fields:
        # Find first non-empty value
        for profile in profiles:
            value = profile.get(field, "")
            if value and str(value).strip():
                merged[field] = value
                break
        if field not in merged:
            merged[field] = ""

    return merged


def extract_project_name(folder_name: str, athlete_name: str) -> str:
    """
    Extract project name from folder name.

    Examples:
    - "Phia Hull - Dec Highlight" with athlete "Phia Hull" → "Dec Highlight"
    - "Phia Hull" with athlete "Phia Hull" → "Default"
    """
    name_lower = athlete_name.lower()
    folder_lower = folder_name.lower()

    if folder_lower.startswith(f"{name_lower} - "):
        # Has project suffix
        return folder_name[len(athlete_name) + 3:].strip()

    # Same as athlete name
    return "Default"


def merge_athletes(
    athlete_name: str,
    dry_run: bool = False,
    force: bool = False
) -> dict:
    """
    Merge multiple legacy folders into a single v2 athlete.

    Args:
        athlete_name: The athlete name to merge folders for
        dry_run: If True, only show what would be done
        force: If True, overwrite existing projects

    Returns:
        Dictionary with merge results
    """
    result = {
        "success": False,
        "athlete_name": athlete_name,
        "folders_merged": [],
        "projects_created": [],
        "actions": []
    }

    # Find matching folders
    folders = find_matching_folders(athlete_name)

    if not folders:
        result["actions"].append(f"ERROR: No folders found matching '{athlete_name}'")
        return result

    if len(folders) == 1 and not is_v2_structure(folders[0]):
        result["actions"].append(f"NOTE: Only one folder found. Use migrate_athlete.py instead.")
        return result

    # Target athlete directory
    athlete_dir = ROOT / athlete_name

    # Check if athlete already exists as v2
    existing_v2 = athlete_dir.exists() and is_v2_structure(athlete_dir)

    # Collect player profiles from all folders
    profiles = []
    for folder in folders:
        if is_v2_structure(folder):
            profiles.append(get_athlete_profile(folder))
        else:
            project_json = folder / "project.json"
            if project_json.exists():
                try:
                    data = json.loads(project_json.read_text())
                    if "player" in data:
                        profiles.append(data["player"])
                except json.JSONDecodeError:
                    pass

    # Merge profiles
    merged_profile = merge_profiles(profiles)
    merged_profile["name"] = athlete_name

    # Plan actions
    if not existing_v2:
        result["actions"].append(f"CREATE: v2 athlete structure: {athlete_dir}")
        result["actions"].append(f"CREATE: athlete.json with merged player profile")

    # Plan folder migrations
    for folder in folders:
        if is_v2_structure(folder):
            if folder == athlete_dir:
                result["actions"].append(f"SKIP: Already target v2 folder: {folder}")
            else:
                # Merge projects from another v2 folder
                result["actions"].append(f"MERGE: projects from {folder}")
        else:
            project_name = extract_project_name(folder.name, athlete_name)
            project_dir = athlete_dir / "projects" / project_name

            if project_dir.exists() and not force:
                result["actions"].append(f"SKIP: Project already exists: {project_name}")
            else:
                result["actions"].append(f"MIGRATE: {folder.name} → projects/{project_name}")
                result["projects_created"].append(project_name)
                result["folders_merged"].append(folder)

    if dry_run:
        result["success"] = True
        return result

    # Execute the merge
    try:
        # Create v2 structure if needed
        if not existing_v2:
            athlete_dir.mkdir(parents=True, exist_ok=True)
            create_v2_structure(athlete_dir, merged_profile)
        else:
            # Update profile if we have better data
            athlete_json = athlete_dir / "athlete.json"
            if athlete_json.exists():
                existing = json.loads(athlete_json.read_text())
                updated = merge_profiles([existing, merged_profile])
                updated["schema_version"] = SCHEMA_VERSION
                athlete_json.write_text(json.dumps(updated, indent=2))

        # Migrate each folder
        from migrate_athlete import migrate_athlete

        for folder in folders:
            if is_v2_structure(folder):
                if folder != athlete_dir:
                    # TODO: Merge projects from another v2 folder
                    result["actions"].append(f"NOTE: Merging v2 folders not yet implemented")
                continue

            # Run migration
            project_name = extract_project_name(folder.name, athlete_name)

            # Temporarily rename folder to match expected pattern
            # The migrate_athlete function expects "Athlete - Project" format

            migrate_result = migrate_athlete(folder, dry_run=False, force=force)

            if not migrate_result["success"]:
                result["actions"].append(f"WARNING: Failed to migrate {folder.name}")
                for action in migrate_result["actions"]:
                    if "ERROR" in action:
                        result["actions"].append(f"  {action}")

        result["success"] = True

    except Exception as e:
        result["actions"].append(f"ERROR: Merge failed: {e}")
        result["success"] = False

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Merge multiple legacy folders into a single multi-project athlete",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python merge_athletes.py "Phia Hull"
  python merge_athletes.py --dry-run "Phia Hull"
  python merge_athletes.py --list
        """
    )
    parser.add_argument("athlete", nargs="?", help="Athlete name to merge folders for")
    parser.add_argument("--list", action="store_true",
                       help="List all potential merge candidates")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would change without modifying anything")
    parser.add_argument("--force", action="store_true",
                       help="Overwrite existing projects")

    args = parser.parse_args()

    if args.list or not args.athlete:
        candidates = find_all_merge_candidates()

        if not candidates:
            print("No merge candidates found.")
            print("\nMerge candidates are athletes with multiple folders like:")
            print("  - 'Phia Hull'")
            print("  - 'Phia Hull - Dec Highlight'")
            print("  - 'Phia Hull - STXCL Playoffs'")
            sys.exit(0)

        print("Potential merge candidates:\n")
        for athlete_name, folders in sorted(candidates.items()):
            print(f"  {athlete_name}:")
            for folder in folders:
                project = extract_project_name(folder.name, athlete_name)
                print(f"    • {folder.name} → project: {project}")
            print()

        if not args.athlete:
            print("Usage: python merge_athletes.py \"Athlete Name\"")
            sys.exit(0)

    # Run merge
    if args.dry_run:
        print("DRY RUN - No changes will be made\n")

    result = merge_athletes(args.athlete, dry_run=args.dry_run, force=args.force)

    print(f"{'='*60}")
    print(f"Merging folders for: {args.athlete}")
    print(f"{'='*60}")

    for action in result["actions"]:
        prefix = "  "
        if action.startswith("ERROR"):
            prefix = "  ❌ "
        elif action.startswith("SKIP"):
            prefix = "  ⏭️ "
        elif action.startswith("NOTE"):
            prefix = "  ℹ️ "
        elif action.startswith("WARNING"):
            prefix = "  ⚠️ "
        else:
            prefix = "  ✓ " if not args.dry_run else "  → "
        print(f"{prefix}{action}")

    if result["success"]:
        print(f"\n✓ Merge successful")
        if result["projects_created"]:
            print(f"  Projects created: {', '.join(result['projects_created'])}")
    else:
        print(f"\n✗ Merge failed")

    if args.dry_run:
        print("\n(This was a dry run - no changes were made)")


if __name__ == "__main__":
    main()
