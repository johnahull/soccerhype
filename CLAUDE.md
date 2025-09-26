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
python create_athlete.py "Athlete Name"
```

**2. Mark plays interactively:**
```bash
python mark_play.py
# Or target specific athlete:
python mark_play.py --athlete "Athlete Name"
python mark_play.py --dir athletes/athlete_name
```

**3. Reorder clips with GUI (optional):**
```bash
python reorder_clips.py
# Note: Uses system video player for preview (xdg-open/open/os.startfile)
# Provides better security and codec support than embedded player
```

**4. Render final highlight video:**
```bash
python render_highlight.py --dir athletes/athlete_name
# Options:
python render_highlight.py --dir athletes/athlete_name --reset-intro  # Choose intro media again
python render_highlight.py --dir athletes/athlete_name --keep-work    # Keep temp files
```

**5. Batch process multiple athletes:**
```bash
python batch_render.py
# Options:
python batch_render.py --names "Jane Smith" "John Doe" --force --jobs 2
```

## Project Architecture

**Directory Structure:**
```
athletes/
├── athlete_name/
│   ├── clips_in/           # Drop source videos here
│   ├── intro/              # Player pictures or intro videos for slate customization
│   ├── work/proxies/       # Auto-generated standardized proxies
│   ├── output/             # Final rendered video (final.mp4)
│   └── project.json        # Athlete metadata and clip marking data
```

**Key Components:**

- **create_athlete.py**: Sets up folder structure for new athletes (including intro directory)
- **mark_play.py**: Interactive video player for marking athlete positions with full transport controls (space/arrow keys/mouse)
- **reorder_clips.py**: Tkinter GUI for visual clip reordering with playback preview
- **render_highlight.py**: FFmpeg-based renderer that creates final highlight video with red ring overlays and customizable intro slates
- **batch_render.py**: Parallel processing of multiple athletes

**project.json Structure:**
Contains athlete metadata and clip data with standardized coordinates:

*Player metadata fields:*
- `name`: Player's full name
- `title`: Optional title displayed above name on slate (e.g., "Fall 2025 Highlight Video")
- `position`: Playing position
- `grad_year`: Graduation year
- `club_team`, `high_school`: Team affiliations
- `height_weight`, `gpa`: Physical/academic stats
- `email`, `phone`: Contact information

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