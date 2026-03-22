#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""
Create athlete folder structure.

Supports two folder structure versions:
- v2 (default): Multi-project structure with shared profile and intro
- v1 (legacy): Single-project structure for backward compatibility

Usage:
    python create_athlete.py "Jane Doe"
    python create_athlete.py "Jane Doe" --legacy    # Create v1 structure
    python create_athlete.py "Jane Doe" --project "Fall 2025"  # Create with initial project
"""

import argparse
import pathlib
import sys

from utils.structure import create_v2_structure, create_project, SCHEMA_VERSION

ROOT = pathlib.Path.cwd() / "athletes"


def create_v1_athlete(athlete_name: str) -> pathlib.Path:
    """Create legacy (v1) folder structure."""
    athlete_dir = ROOT / athlete_name
    clips_in = athlete_dir / "clips_in"
    intro = athlete_dir / "intro"
    work = athlete_dir / "work" / "proxies"
    output = athlete_dir / "output"

    if athlete_dir.exists():
        print(f"⚠ Athlete folder '{athlete_name}' already exists at {athlete_dir}")
        sys.exit(1)

    # Create directories
    clips_in.mkdir(parents=True, exist_ok=True)
    intro.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    return athlete_dir


def create_v2_athlete(athlete_name: str, initial_project: str = None) -> pathlib.Path:
    """Create multi-project (v2) folder structure."""
    athlete_dir = ROOT / athlete_name

    if athlete_dir.exists():
        print(f"⚠ Athlete folder '{athlete_name}' already exists at {athlete_dir}")
        sys.exit(1)

    # Create athlete directory first
    athlete_dir.mkdir(parents=True, exist_ok=True)

    # Initialize v2 structure with basic profile
    profile = {
        "name": athlete_name,
        "position": "",
        "grad_year": "",
        "club_team": "",
        "high_school": "",
        "height_weight": "",
        "gpa": "",
        "email": "",
        "phone": "",
    }
    create_v2_structure(athlete_dir, profile)

    # Create initial project if specified
    if initial_project:
        create_project(athlete_dir, initial_project)

    return athlete_dir


def main():
    from version import __version__
    parser = argparse.ArgumentParser(
        description="Create athlete folder structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_athlete.py "Jane Doe"
  python create_athlete.py "Jane Doe" --project "Fall 2025"
  python create_athlete.py "Jane Doe" --legacy
        """
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("name", nargs="?", help="Athlete name")
    parser.add_argument("--legacy", action="store_true",
                       help="Create v1 (legacy) structure instead of v2")
    parser.add_argument("--project", type=str, metavar="NAME",
                       help="Create initial project with this name (v2 only)")

    args = parser.parse_args()

    # Get athlete name from args or prompt
    if args.name:
        athlete_name = args.name.strip()
    else:
        athlete_name = input("Enter athlete name: ").strip()

    if not athlete_name:
        print("No name entered. Exiting.")
        return

    # Validate options
    if args.legacy and args.project:
        print("⚠ Cannot use --project with --legacy. Projects are a v2 feature.")
        sys.exit(1)

    # Create structure
    if args.legacy:
        athlete_dir = create_v1_athlete(athlete_name)
        print(f"\n✅ Created v1 (legacy) folder structure for '{athlete_name}':")
        print(athlete_dir)
        print(f"  ├─ clips_in/")
        print(f"  ├─ intro/")
        print(f"  ├─ work/proxies/")
        print(f"  └─ output/")
        print("\n📂 Drop clips into the clips_in folder before running mark_play.py.")
        print("🖼️  Drop player pictures or intro videos into the intro folder.")
    else:
        athlete_dir = create_v2_athlete(athlete_name, args.project)
        print(f"\n✅ Created v2 (multi-project) folder structure for '{athlete_name}':")
        print(athlete_dir)
        print(f"  ├─ athlete.json         # Shared player profile")
        print(f"  ├─ intro/               # Shared intro media")
        print(f"  └─ projects/")
        if args.project:
            print(f"      └─ {args.project}/")
            print(f"          ├─ clips_in/")
            print(f"          ├─ work/proxies/")
            print(f"          ├─ output/")
            print(f"          └─ project.json")
            print(f"\n📂 Drop clips into projects/{args.project}/clips_in/")
        else:
            print(f"      (no projects yet)")
            print(f"\n📝 Next: Create a project with:")
            print(f"   python create_project.py --athlete \"{athlete_name}\" --project \"Project Name\"")
        print("🖼️  Drop player pictures or intro videos into the intro folder.")


if __name__ == "__main__":
    main()


