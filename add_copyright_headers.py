#!/usr/bin/env python3
"""
Script to add copyright headers to all Python files in the project.
Copyright (c) 2025 John Hull
Licensed under the MIT License - see LICENSE file
"""

import os
import pathlib
import sys

# Copyright header to add
COPYRIGHT_HEADER = """# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""

def has_copyright_header(file_path):
    """Check if file already has a copyright header."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(500)  # Check first 500 chars
            return 'Copyright' in content or 'copyright' in content
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return True  # Skip on error

def add_header_to_file(file_path):
    """Add copyright header to a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip if already has header
        if has_copyright_header(file_path):
            return False

        # Handle shebang line if present
        lines = content.split('\n')
        if lines and lines[0].startswith('#!'):
            # Keep shebang, add header after it
            shebang = lines[0] + '\n'
            rest = '\n'.join(lines[1:])
            new_content = shebang + COPYRIGHT_HEADER + rest
        else:
            # Add header at the beginning
            new_content = COPYRIGHT_HEADER + content

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Find and process all Python files."""
    root = pathlib.Path.cwd()

    # Find all Python files (excluding virtual environments)
    python_files = []
    for pattern in ['*.py', 'tests/*.py', 'utils/*.py']:
        python_files.extend(root.glob(pattern))

    # Remove duplicates and sort
    python_files = sorted(set(python_files))

    # Filter out virtual environment files
    python_files = [
        f for f in python_files
        if '.venv' not in str(f) and 'venv' not in str(f)
    ]

    print(f"Found {len(python_files)} Python files")
    print("Adding copyright headers...\n")

    modified = 0
    skipped = 0

    for file_path in python_files:
        relative_path = file_path.relative_to(root)
        if add_header_to_file(file_path):
            print(f"✓ Added header to {relative_path}")
            modified += 1
        else:
            print(f"○ Skipped {relative_path} (already has header)")
            skipped += 1

    print(f"\nSummary:")
    print(f"  Modified: {modified}")
    print(f"  Skipped: {skipped}")
    print(f"  Total: {len(python_files)}")

if __name__ == "__main__":
    main()
