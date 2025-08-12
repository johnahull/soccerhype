#!/usr/bin/env python3
# batch_render.py
# Batch runner for multi-athlete render_highlight.py

import argparse
import pathlib
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = pathlib.Path.cwd()
ATHLETES = ROOT / "athletes"

def discover_athletes(names=None):
    if names:
        return [ATHLETES / n for n in names]
    return sorted([p for p in ATHLETES.iterdir() if p.is_dir()])

def should_skip(ath_dir: pathlib.Path, force: bool) -> bool:
    proj = ath_dir / "project.json"
    out  = ath_dir / "output" / "final.mp4"
    if not proj.exists():
        print(f"⏭️  Skip (no project.json): {ath_dir.name}")
        return True
    if out.exists() and not force:
        print(f"⏭️  Skip (final exists, use --force to re-render): {ath_dir.name}")
        return True
    return False

def render_one(ath_dir: pathlib.Path, keep_work: bool, python: str) -> tuple[str, int]:
    cmd = [python, "render_highlight.py", "--dir", str(ath_dir)]
    if keep_work:
        cmd.append("--keep-work")
    print("•", " ".join(cmd))
    proc = subprocess.run(cmd)
    return (ath_dir.name, proc.returncode)

def main():
    ap = argparse.ArgumentParser(description="Batch render all/selected athletes.")
    ap.add_argument("--names", nargs="*", help="Specific athlete folder names under ./athletes")
    ap.add_argument("--jobs", type=int, default=1, help="Parallel renders (default 1)")
    ap.add_argument("--keep-work", action="store_true", help="Keep intermediates")
    ap.add_argument("--force", action="store_true", help="Re-render even if final.mp4 exists")
    ap.add_argument("--dry-run", action="store_true", help="List targets without running")
    ap.add_argument("--python", default="python", help="Python executable to run render_highlight.py")
    args = ap.parse_args()

    if not ATHLETES.exists():
        print("No ./athletes directory found.")
        return

    targets = discover_athletes(args.names)
    if not targets:
        print("No athlete folders found to process.")
        return

    # Filter by presence of project.json / final.mp4 unless --force
    queue = [a for a in targets if not should_skip(a, args.force)]
    if not queue:
        print("Nothing to do.")
        return

    print(f"\nBatch size: {len(queue)}  |  Parallel jobs: {args.jobs}\n")

    if args.dry_run:
        for a in queue:
            print(f"DRY RUN → would render: {a.name}")
        return

    if args.jobs <= 1:
        # Sequential (safest, uses all cores per ffmpeg job)
        failures = 0
        for a in queue:
            name, rc = render_one(a, args.keep_work, args.python)
            if rc != 0:
                print(f"❌ Failed: {name} (rc={rc})")
                failures += 1
        print(f"\n✅ Done. {len(queue)-failures} succeeded, {failures} failed.")
    else:
        # Parallel (be mindful of CPU/GPU/IO load)
        failures = 0
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            futs = [ex.submit(render_one, a, args.keep_work, args.python) for a in queue]
            for fut in as_completed(futs):
                name, rc = fut.result()
                if rc == 0:
                    print(f"✔ Success: {name}")
                else:
                    print(f"❌ Failed: {name} (rc={rc})")
                    failures += 1
        print(f"\n✅ Done. {len(queue)-failures} succeeded, {failures} failed.")

if __name__ == "__main__":
    main()

