#!/usr/bin/env python3
import pathlib
import sys

ROOT = pathlib.Path.cwd() / "athletes"

def main():
    # Allow passing athlete name via command line
    if len(sys.argv) > 1:
        athlete_name = " ".join(sys.argv[1:]).strip()
    else:
        athlete_name = input("Enter athlete name: ").strip()

    if not athlete_name:
        print("No name entered. Exiting.")
        return

    athlete_dir = ROOT / athlete_name
    clips_in = athlete_dir / "clips_in"
    intro = athlete_dir / "intro"
    work = athlete_dir / "work" / "proxies"
    output = athlete_dir / "output"

    if athlete_dir.exists():
        print(f"⚠ Athlete folder '{athlete_name}' already exists at {athlete_dir}")
        return

    # Create directories
    clips_in.mkdir(parents=True, exist_ok=True)
    intro.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    print(f"\n✅ Created folder structure for '{athlete_name}':")
    print(athlete_dir)
    print(f"  ├─ {clips_in.relative_to(ROOT.parent)}")
    print(f"  ├─ {intro.relative_to(ROOT.parent)}")
    print(f"  ├─ {work.relative_to(ROOT.parent)}")
    print(f"  └─ {output.relative_to(ROOT.parent)}")
    print("\n📂 Drop clips into the clips_in folder before running mark_play.py.")
    print("🖼️  Drop player pictures or intro videos into the intro folder for slate customization.")

if __name__ == "__main__":
    main()

