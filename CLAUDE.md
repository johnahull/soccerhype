# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **soccerhype** - a Python + FFmpeg tool for creating athlete highlight videos. It combines video clips into professional highlight reels with red spotlight rings to mark players, optional intro slates, and batch processing capabilities.

## Setup and Installation

**Environment Setup:**
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
- Python 3.9+ with OpenCV, Pillow, PyYAML, Tkinter
- FFmpeg with libx264, libfreetype support
- Ubuntu 24.04+ (should work on other Linux distros)

## Core Workflow Commands

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
Contains athlete metadata (name, position, grad year, etc.) and clip data with standardized coordinates:
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

**Performance:**
- Batch processing supports parallel execution (`--jobs N`)
- Uses CRF 18 for high-quality output
- Work files can be cleaned up with `--keep-work` option