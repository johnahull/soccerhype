# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **soccerhype** - a Python + FFmpeg tool for creating athlete highlight videos. It combines video clips into professional highlight reels with red spotlight rings to mark players, optional intro slates, and batch processing capabilities.

## Setup and Installation

**Enhanced Setup (Recommended):**
```bash
# Run the enhanced setup script for GUI improvements
./setup_enhanced.sh

# This includes all dependencies plus enhanced features
```

**Standard Setup:**
```bash
# Run the automated setup script
./setup.sh

# Or manual setup:
sudo apt install ffmpeg python3-opencv python3-pil python3-tk fonts-dejavu-core
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Dependencies:**
- Python 3.9+ with PyYAML, Tkinter (Note: OpenCV and Pillow removed from reorder_clips.py for security)
- FFmpeg with libx264, libfreetype support
- Ubuntu 24.04+ (should work on other Linux distros)

**Important Dependency Changes:**
- **reorder_clips.py**: Now uses system video player instead of embedded OpenCV player for security
- **Trade-off**: Better security and codec support vs. no embedded scrubbing/looping controls
- **Benefit**: Eliminates complex video decoding dependencies and security vulnerabilities

## Core Workflow Commands

**Enhanced GUI Workflow (Recommended):**
```bash
# Launch unified GUI application
python soccerhype_gui.py
# Or use launcher: ./launch_soccerhype.sh
```

**Enhanced Command Line Tools:**
```bash
# Enhanced marking with smart defaults and templates
python mark_play_enhanced.py
python mark_play_enhanced.py --template "soccer_player_template"

# Enhanced clip reordering with thumbnail preview
python reorder_clips_enhanced.py
```

**Standard Command Line Workflow:**

**1. Create athlete folder structure:**
```bash
# Create v2 athlete with default project
python create_athlete.py "Athlete Name"

# Create additional projects for existing athlete
python create_project.py --athlete "Athlete Name" --project "Spring 2026"

# Create legacy v1 structure (single project)
python create_athlete.py --legacy "Athlete Name"
```

**2. Order clips with GUI (syncs clips_in/ folder):**
```bash
python reorder_clips.py
# Target specific athlete (prompts for project if v2):
python reorder_clips.py --athlete "Athlete Name"
# Target specific project directly:
python reorder_clips.py --athlete "Athlete Name" --project "Fall 2025"
python reorder_clips.py --dir athletes/Athlete\ Name/projects/Fall\ 2025
# Note: Auto-syncs clips_in/ folder on launch
# Uses system video player for preview (xdg-open/open/os.startfile)
```

**3. Mark plays interactively:**
```bash
python mark_play.py
# Target specific athlete (prompts for project if v2):
python mark_play.py --athlete "Athlete Name"
# Target specific project:
python mark_play.py --athlete "Athlete Name" --project "Fall 2025"
python mark_play.py --dir athletes/Athlete\ Name/projects/Fall\ 2025
# Note: Only marks unmarked clips by default (use --all to re-mark)
```

**4. Render final highlight video:**
```bash
# Target specific project:
python render_highlight.py --dir athletes/Athlete\ Name/projects/Fall\ 2025
# Or use athlete + project flags:
python render_highlight.py --athlete "Athlete Name" --project "Fall 2025"
# Options:
python render_highlight.py --dir <project_dir> --reset-intro  # Choose intro media again
python render_highlight.py --dir <project_dir> --keep-work    # Keep temp files
```

**5. Batch process multiple athletes:**
```bash
python batch_render.py
# Options:
python batch_render.py --names "Jane Smith" "John Doe" --force --jobs 2
# Note: For v2 athletes, all projects are processed
```

**6. Migration tools (v1 → v2):**
```bash
# Migrate a single legacy folder
python migrate_athlete.py "athletes/Phia Hull - Dec Highlight"
python migrate_athlete.py --dry-run "athletes/Phia Hull - Dec Highlight"
python migrate_athlete.py --all  # Migrate all legacy folders

# Merge multiple legacy folders into one v2 athlete
python merge_athletes.py "Phia Hull"
python merge_athletes.py --list  # Show merge candidates
```

**7. Sync clips (add/remove without losing marks):**
```bash
python clip_sync.py
python clip_sync.py --athlete "Athlete Name" --project "Fall 2025"
python clip_sync.py --dry-run  # Show what would change
```

## Project Architecture

**Directory Structure (v2 - Multi-Project):**

The default structure supports multiple projects per athlete, with shared profile and intro media:

```
athletes/
├── Athlete Name/
│   ├── athlete.json          # Shared player profile (name, position, contact, etc.)
│   ├── intro/                # Shared intro media (pictures, videos)
│   └── projects/
│       ├── Fall 2025/
│       │   ├── project.json  # Project-specific settings and clips
│       │   ├── clips_in/     # Source videos for this project
│       │   ├── work/proxies/ # Auto-generated proxies
│       │   └── output/       # Final rendered video (final.mp4)
│       └── Spring 2026/
│           └── ...
```

**Directory Structure (v1 - Legacy):**

Legacy single-project structure (still supported):

```
athletes/
├── athlete_name/
│   ├── clips_in/           # Drop source videos here
│   ├── intro/              # Player pictures or intro videos
│   ├── work/proxies/       # Auto-generated standardized proxies
│   ├── output/             # Final rendered video (final.mp4)
│   └── project.json        # Player metadata AND clip marking data
```

**Key Components:**

- **create_athlete.py**: Sets up v2 folder structure with default project (use `--legacy` for v1)
- **create_project.py**: Creates new projects under an existing athlete
- **mark_play.py**: Interactive video player for marking athlete positions (supports `--project` option)
- **reorder_clips.py**: Tkinter GUI for visual clip reordering (supports `--project` option)
- **render_highlight.py**: FFmpeg-based renderer (supports `--project` option)
- **batch_render.py**: Parallel processing of multiple athletes and projects
- **migrate_athlete.py**: Migrates legacy (v1) folders to v2 multi-project structure
- **merge_athletes.py**: Merges multiple legacy folders into a single v2 athlete
- **clip_sync.py**: Syncs clips_in/ folder with project.json (add/remove clips without losing marks)
- **utils/structure.py**: Centralized structure detection and path resolution utilities

**Data Model:**

*athlete.json (v2 only - shared profile):*
```json
{
  "schema_version": "2.0",
  "name": "Player Name",
  "title": "Optional title for slate",
  "position": "MF",
  "grad_year": "2026",
  "club_team": "Team Name",
  "high_school": "School Name",
  "height_weight": "5'8\" / 140 lbs",
  "gpa": "4.0",
  "email": "player@example.com",
  "phone": "555-1234"
}
```

*project.json (v2 - per project):*
```json
{
  "schema_version": "2.0",
  "project_name": "Fall 2025",
  "include_intro": true,
  "intro_media": "intro/player-photo.jpg",
  "clips": [...]
}
```

*project.json (v1 - legacy, includes player data):*
```json
{
  "player": { "name": "...", "position": "...", ... },
  "include_intro": true,
  "intro_media": "intro/player-photo.jpg",
  "clips": [...]
}
```

*Clip data fields:*
- `marker_x_std/marker_y_std`: Player position in 1920px-wide proxy
- `spot_time/spot_frame_std`: When to show the freeze-frame ring
- `radius_std`: Ring size in standardized pixels
- `start_trim/end_trim`: Clip timing adjustments

## Technical Details

**Video Processing:**
- All clips are converted to standardized 1920px-wide proxies at 30fps CFR
- Uses setsar=1 and -noautorotate for consistent playback
- Final output strips audio to avoid licensing issues
- Red ring overlay freezes for 1.25s at marked positions

**Marking Controls (in mark_play.py):**
- Space: Play/Pause
- Arrow keys: Frame stepping and seeking
- Mouse click: Set ring position
- Mouse wheel: Adjust ring radius
- 's' key: Set freeze frame timing
- 'a'/'b' keys: Set start/end trims

**Intro Media Customization:**
- Place player pictures (.jpg, .png, .bmp, .gif, .webp) or intro videos (.mp4, .mov, .avi, .mkv) in the `intro/` folder
- **First time**: When rendering, you'll be prompted to select media files if available
- **Subsequent renders**: Your selection is remembered in project.json
- Use `--reset-intro` to change your intro media selection
- Pictures are embedded on the left side of the slate with text on the right
- Videos are used as animated backgrounds with text overlays
- Choose "No intro media" for traditional text-only slates

**Slate Text Hierarchy:**
- `title` (optional): Largest text above name (84pt for images, 72pt for video)
- `name`: Player name (72pt for images, 64pt for video) 
- `position` + `grad_year`: Combined on one line (44pt for images, 40pt for video)
- Additional details: Club team, high school, height/weight, GPA, contact info (40pt/36pt)

**Performance:**
- Batch processing supports parallel execution (`--jobs N`)
- Uses CRF 18 for high-quality output
- Work files can be cleaned up with `--keep-work` option

**Security Features:**
- **Path Traversal Protection**: All file operations validate paths are within expected directories
- **Command Injection Prevention**: subprocess.run() used with shell=False and proper argument lists
- **Atomic File Operations**: Temp file + rename pattern prevents data corruption during writes
- **Input Validation**: Email regex validation, name length limits, profile ID sanitization
- **PII Protection**: Player database (players_database.json) excluded from version control

## Standalone Application Packaging

**Creating Standalone Executables:**

SoccerHype can be packaged as a standalone application for Windows and macOS distribution. See [PACKAGING.md](PACKAGING.md) for complete instructions.

**Quick Start:**

*Windows:*
```bash
python bundle_ffmpeg.py --platform windows  # Download FFmpeg
build_windows.bat                           # Build executable
```

*macOS:*
```bash
python3 bundle_ffmpeg.py --platform macos   # Download FFmpeg
./build_macos.sh                            # Build app bundle
```

**Key Files:**
- `soccerhype.spec` - PyInstaller configuration
- `build_windows.bat` - Windows build script
- `build_macos.sh` - macOS build script
- `bundle_ffmpeg.py` - FFmpeg bundling utility
- `ffmpeg_utils.py` - FFmpeg detection module
- `PACKAGING.md` - Complete packaging documentation

**FFmpeg Bundling:**
The standalone application can bundle FFmpeg or use system FFmpeg. The `ffmpeg_utils` module automatically detects and uses bundled FFmpeg when available, falling back to system FFmpeg if not.

## Testing and Development

**Testing:**
- pytest is included in requirements.txt for future test development
- Currently no formal test suite - this is a practical utility tool focused on video processing workflows

**Development workflow:**
- Direct execution of Python scripts without build steps
- Virtual environment activation required: `source .venv/bin/activate`
- Dependencies managed via requirements.txt and setup.sh

## Troubleshooting

**Common issues:**
- FFmpeg errors: Verify `ffmpeg -version` shows libx264 and libfreetype support
- Python import errors: Activate virtual environment and run `pip install -r requirements.txt`
- Performance issues: Use `--jobs 1` for batch processing on limited hardware
- Preview not working: Ensure system has default video player (VLC, Media Player, etc.)
- Large file warnings: Consider using Git LFS for video files >50MB

## Security Guidelines for Contributors

**🔒 Security Best Practices:**

1. **PII Handling:**
   - NEVER commit files containing personal information (emails, phone numbers)
   - Always check `players_database.json` is in `.gitignore`
   - Use placeholder data in tests and examples

2. **File Operations:**
   - Always validate file paths are within expected directories
   - Use `pathlib.Path.resolve()` to prevent directory traversal
   - Implement atomic writes with temp files for data integrity

3. **Input Validation:**
   - Sanitize all user inputs (profile IDs, file names, form data)
   - Use regex validation for emails and other structured data
   - Implement length limits and character restrictions

4. **Subprocess Security:**
   - Always use `subprocess.run(shell=False)`
   - Pass arguments as lists, not concatenated strings
   - Add timeout protection for external commands
   - Validate executable paths before calling

5. **Error Handling:**
   - Never expose sensitive paths in error messages
   - Log security events for audit purposes
   - Fail securely - prefer blocking over permissive behavior

**📋 Code Review Checklist:**
- [ ] No PII in committed files
- [ ] Path traversal protection implemented
- [ ] Input validation for user data
- [ ] Secure subprocess calls
- [ ] Atomic file operations for critical data
- [ ] Comprehensive error handling
- [ ] Security tests included