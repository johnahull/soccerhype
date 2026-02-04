#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""
Create a new project under an existing athlete (v2 multi-project structure).

Usage:
    python create_project.py --athlete "Phia Hull" --project "Fall 2025"
    python create_project.py  # Interactive mode
"""

import argparse
import pathlib
import sys
from typing import List, Optional

from utils.structure import (
    create_project,
    clone_project,
    create_v2_structure,
    is_v2_structure,
    list_projects,
    get_athlete_profile,
)

ROOT = pathlib.Path.cwd() / "athletes"


def find_athletes() -> List[pathlib.Path]:
    """Find all athlete directories."""
    if not ROOT.exists():
        return []
    return sorted([p for p in ROOT.iterdir() if p.is_dir()])


def choose_athlete_interactive() -> pathlib.Path:
    """Interactively choose an athlete."""
    options = find_athletes()
    if not options:
        print("No athlete folders found under ./athletes/")
        print("Create one first with: python create_athlete.py \"Athlete Name\"")
        sys.exit(1)

    print("\nSelect an athlete:")
    for i, p in enumerate(options, 1):
        # Show existing projects count
        projects = list_projects(p)
        if is_v2_structure(p):
            project_count = len(projects)
            print(f"  {i}. {p.name} ({project_count} project{'s' if project_count != 1 else ''})")
        else:
            print(f"  {i}. {p.name} (v1 legacy - will upgrade)")

    print("  q. Quit")

    while True:
        choice = input("Enter number: ").strip().lower()
        if choice in ("q", "quit", "exit"):
            sys.exit(0)
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        print("Invalid choice. Try again.")


def get_project_name_interactive(athlete_dir: pathlib.Path) -> str:
    """Interactively get project name."""
    existing = list_projects(athlete_dir)
    existing_names = {p.name for p in existing}

    print(f"\nExisting projects for {athlete_dir.name}:")
    if existing and is_v2_structure(athlete_dir):
        for p in existing:
            print(f"  • {p.name}")
    else:
        print("  (none)")

    while True:
        name = input("\nEnter new project name: ").strip()
        if not name:
            print("Project name cannot be empty.")
            continue
        if name in existing_names:
            print(f"Project '{name}' already exists. Choose a different name.")
            continue
        # Validate name (no path separators)
        if "/" in name or "\\" in name:
            print("Project name cannot contain path separators.")
            continue
        return name


def choose_clone_source_interactive(athlete_dir: pathlib.Path) -> Optional[str]:
    """
    Ask user whether to start from scratch or clone, and if cloning, which project.

    Returns:
        Project name to clone from, or None if starting from scratch
    """
    existing = list_projects(athlete_dir)

    # If no existing projects, can't clone
    if not existing or not is_v2_structure(athlete_dir):
        return None

    print("\nHow would you like to create this project?")
    print("  1. Start from scratch (empty project)")
    print("  2. Clone existing project (copy clips and marks)")

    while True:
        choice = input("Enter choice [1]: ").strip()
        if choice == "" or choice == "1":
            return None
        if choice == "2":
            break
        print("Invalid choice. Enter 1 or 2.")

    # Show existing projects to clone from
    print("\nSelect project to clone from:")
    for i, p in enumerate(existing, 1):
        print(f"  {i}. {p.name}")

    while True:
        choice = input("Enter number: ").strip()
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(existing):
                return existing[idx - 1].name
        print("Invalid choice. Try again.")


def upgrade_to_v2_if_needed(athlete_dir: pathlib.Path) -> bool:
    """
    Check if athlete uses v1 structure and offer to upgrade.

    Returns True if upgrade happened or already v2, False if user declined.
    """
    if is_v2_structure(athlete_dir):
        return True

    print(f"\n⚠ Athlete '{athlete_dir.name}' uses v1 (legacy) structure.")
    print("To use multi-project features, it needs to be upgraded to v2.")
    print("\nThis will:")
    print("  • Create athlete.json with player profile")
    print("  • Create projects/ directory")
    print("  • Keep existing clips/project as-is (migration needed separately)")

    confirm = input("\nUpgrade to v2 structure? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return False

    # Read existing profile if available
    profile = get_athlete_profile(athlete_dir)
    if not profile.get("name"):
        profile["name"] = athlete_dir.name

    # Create v2 structure (athlete.json and projects/)
    create_v2_structure(athlete_dir, profile)
    print(f"✓ Upgraded {athlete_dir.name} to v2 structure")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Create a new project under an existing athlete",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_project.py --athlete "Phia Hull" --project "Fall 2025"
  python create_project.py --athlete "Phia Hull" --project "Spring 2026" --clone "Fall 2025"
  python create_project.py  # Interactive mode (offers clone option)
        """
    )
    parser.add_argument("--athlete", type=str, help="Athlete name")
    parser.add_argument("--project", type=str, help="New project name")
    parser.add_argument("--clone", type=str,
                       help="Clone from existing project instead of starting empty")

    args = parser.parse_args()

    # Resolve athlete directory
    if args.athlete:
        athlete_dir = ROOT / args.athlete
        if not athlete_dir.exists():
            print(f"Athlete folder not found: {athlete_dir}")
            print(f"Create it first with: python create_athlete.py \"{args.athlete}\"")
            sys.exit(1)
    else:
        athlete_dir = choose_athlete_interactive()

    # Upgrade to v2 if needed
    if not upgrade_to_v2_if_needed(athlete_dir):
        sys.exit(0)

    # Determine clone source (if any)
    clone_source = args.clone
    if clone_source is None and not args.project:
        # Interactive mode: ask about cloning
        clone_source = choose_clone_source_interactive(athlete_dir)

    # Get project name
    if args.project:
        project_name = args.project.strip()
    else:
        project_name = get_project_name_interactive(athlete_dir)

    # Create or clone the project
    try:
        if clone_source:
            project_dir = clone_project(athlete_dir, clone_source, project_name)
            print(f"\n✅ Cloned project '{clone_source}' → '{project_name}' for athlete '{athlete_dir.name}':")
            print(f"   {project_dir}")
            print(f"   ├─ clips_in/       # Copied from source")
            print(f"   ├─ work/proxies/   # Copied from source")
            print(f"   ├─ output/         # Empty (re-render needed)")
            print(f"   └─ project.json    # Clip marks preserved")
            print(f"\n📂 Next steps:")
            print(f"   1. Modify clips or marks as needed")
            print(f"   2. Mark plays: python mark_play.py --athlete \"{athlete_dir.name}\" --project \"{project_name}\"")
            print(f"   3. Render: python render_highlight.py --athlete \"{athlete_dir.name}\" --project \"{project_name}\"")
        else:
            project_dir = create_project(athlete_dir, project_name)
            print(f"\n✅ Created project '{project_name}' for athlete '{athlete_dir.name}':")
            print(f"   {project_dir}")
            print(f"   ├─ clips_in/       # Drop video clips here")
            print(f"   ├─ work/proxies/   # Auto-generated")
            print(f"   ├─ output/         # Final video here")
            print(f"   └─ project.json")
            print(f"\n📂 Next steps:")
            print(f"   1. Drop clips into: {project_dir / 'clips_in'}")
            print(f"   2. Mark plays: python mark_play.py --athlete \"{athlete_dir.name}\" --project \"{project_name}\"")
            print(f"   3. Render: python render_highlight.py --athlete \"{athlete_dir.name}\" --project \"{project_name}\"")
    except FileExistsError as e:
        print(f"⚠ {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"⚠ {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
