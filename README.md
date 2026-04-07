# SoccerHype - Athlete Highlight Video Builder

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FFmpeg Required](https://img.shields.io/badge/FFmpeg-required-red.svg)](https://ffmpeg.org/)

Create professional athlete highlight videos with red spotlight player tracking. Built for parents, coaches, and athletes who need polished recruiting reels without expensive software.

## Quick Start

```bash
git clone https://github.com/johnahull/soccerhype.git
cd soccerhype
./setup.sh
source .venv/bin/activate
python soccerhype_gui.py
```

## How It Works

1. **Create athlete** → folder structure with profile info
2. **Add clips** → drop source videos into `clips_in/`
3. **Mark plays** → click to set red spotlight ring position on player
4. **Reorder clips** → drag and drop to arrange
5. **Render** → outputs professional `final.mp4` with intro slate

## Features

- **🎯 Red Spotlight Ring** — freezes on marked player for 1.25s
- **🎬 Professional Intro Slates** — 5 templates with player photos or video backgrounds
- **⚡ Batch Processing** — render multiple athletes in parallel
- **🔒 Privacy First** — all processing runs locally, no cloud uploads
- **🖥️ GUI + CLI** — graphical interface and command-line tools
- **📦 Multi-Project** — multiple highlight reels per athlete (v2 structure)

## CLI Usage

```bash
# Create athlete
python create_athlete.py "Jane Smith"

# Mark plays interactively
python mark_play.py --athlete "Jane Smith" --project "Fall 2025"

# Render highlight video
python render_highlight.py --athlete "Jane Smith" --project "Fall 2025"

# Batch render all athletes
python batch_render.py --jobs 2
```

## Requirements

- Python 3.10+
- FFmpeg with libx264
- 4GB+ RAM recommended

## Documentation

- **[CLAUDE.md](CLAUDE.md)** — developer guide & technical docs
- **[PACKAGING.md](PACKAGING.md)** — standalone executables for Windows/macOS
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — how to contribute
- **[CHANGELOG.md](CHANGELOG.md)** — version history
- **[docs/FULL_README.md](docs/FULL_README.md)** — detailed documentation

## Project Structure

```
athletes/
└── Athlete Name/
    ├── athlete.json          # Player profile
    ├── intro/                # Intro media (photos/videos)
    └── projects/
        └── Fall 2025/
            ├── clips_in/     # Source videos
            ├── project.json  # Clip data & marks
            └── output/       # final.mp4
```

## License

MIT — see [LICENSE](LICENSE)

---

**Made with ⚽ for athletes, parents, and coaches**

[Report Bug](https://github.com/johnahull/soccerhype/issues) · [Request Feature](https://github.com/johnahull/soccerhype/issues)
