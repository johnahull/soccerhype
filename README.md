# SoccerHype - Athlete Highlight Video Builder

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FFmpeg Required](https://img.shields.io/badge/FFmpeg-required-red.svg)](https://ffmpeg.org/)

A Python + FFmpeg tool for quickly creating professional athlete highlight videos. Designed for parents and coaches who need to produce consistent, high-quality highlight reels with red spotlight tracking to mark players.

**Perfect for soccer, basketball, football, lacrosse, and other team sports highlight videos.**

---

## 📺 Demo & Screenshots

> **Coming Soon**: Screenshots and demo video will be added here

---

## ✨ Features

### Core Capabilities

- **🎯 Interactive Player Marking**: Mark athletes in video clips with precise positioning controls
- **🔴 Red Spotlight Ring**: Automatically freezes on marked player for 1.25s with customizable ring size
- **🎬 Professional Intro Slates**: Customizable intro with player pictures or video backgrounds
- **🔧 Complete Workflow**: Order clips → Mark plays → Render → Export
- **⚡ Batch Processing**: Process multiple athletes in parallel with automated rendering
- **🖥️ GUI & CLI**: Both graphical interface and command-line tools available

### Player Information Management

- Name, Position, Graduation Year
- Club Team, High School affiliations
- Height/Weight, GPA, Contact Information
- Secure profile management with PII protection

### Technical Features

- **Runs Locally**: No cloud upload required, all processing on your machine
- **High Quality Output**: CRF 18 encoding for professional-grade video
- **No Audio**: Strips audio to ensure music licensing compliance
- **Cross-Platform**: Linux, Windows (via standalone app), macOS (via standalone app)
- **Standardized Processing**: Automatic proxy generation at 1920px width, 30fps CFR

---

## 🎯 Why SoccerHype?

### Perfect For

- **Parents** creating recruiting highlight videos for student athletes
- **Coaches** producing team highlight reels
- **Athletes** building their sports portfolio
- **Clubs** creating promotional content

### Advantages

✅ **Free & Open Source** - No subscription fees or watermarks
✅ **Privacy First** - All processing happens locally on your computer
✅ **Consistent Quality** - Standardized output for professional appearance
✅ **Easy Workflow** - Simple step-by-step process for non-technical users
✅ **Batch Processing** - Create multiple highlight videos efficiently
✅ **Customizable** - Full control over intro slates, ring appearance, and timing

### Use Cases

- **College Recruiting Videos**: Create polished highlight reels for athletic recruitment
- **Year-End Compilations**: Combine season footage into memorable videos
- **Skills Showcases**: Highlight specific plays and techniques
- **Team Highlights**: Batch process videos for entire teams

---

## 🚀 Quick Start

### Installation

**Option 1: Automated Setup (Recommended)**
```bash
git clone https://github.com/johnahull/highlight_tool.git
cd highlight_tool
./setup.sh
source .venv/bin/activate
```

**Option 2: Manual Setup**
```bash
# Install system dependencies
sudo apt update
sudo apt install ffmpeg python3-opencv python3-pil python3-tk fonts-dejavu-core

# Clone repository
git clone https://github.com/johnahull/highlight_tool.git
cd highlight_tool

# Setup Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Option 3: Standalone Application**

See [PACKAGING.md](PACKAGING.md) for instructions on building or downloading standalone executables for Windows and macOS.

### Basic Workflow

#### 1️⃣ Create Athlete Folder
```bash
python create_athlete.py "Jane Smith"
```

This creates:
```
athletes/jane_smith/
├── clips_in/           # Place your source videos here
├── intro/              # Optional: player pictures or intro videos
├── work/proxies/       # Auto-generated standardized proxies
├── output/             # Final rendered video (final.mp4)
└── project.json        # Athlete metadata and clip data
```

#### 2️⃣ Add Video Clips

Place your source videos (`.mp4`, `.mov`, `.avi`, etc.) in:
```
athletes/jane_smith/clips_in/
```

#### 3️⃣ Mark Player Positions
```bash
python mark_play.py
```

Or use the enhanced GUI:
```bash
python soccerhype_gui.py
```

- Navigate through video with keyboard controls
- Click to set ring position on player
- Press 's' to set freeze frame timing
- Adjust ring size with mouse wheel or +/-
- Set start/end trims with 'a'/'b' keys

#### 4️⃣ (Optional) Reorder Clips
```bash
python reorder_clips.py
```

Drag and drop clips to reorder them visually.

#### 5️⃣ Render Highlight Video
```bash
python render_highlight.py --dir athletes/jane_smith
```

Final video will be created at:
```
athletes/jane_smith/output/final.mp4
```

---

## 🎮 Keyboard Controls (mark_play.py)

| Key | Action |
|-----|--------|
| **Space** | Play / Pause |
| **,** / **.** | Step backward / forward 1 frame (when paused) |
| **←** / **→** | Seek backward / forward 0.5 seconds |
| **↑** / **↓** | Seek backward / forward 5 seconds |
| **[** / **]** | Decrease / increase playback speed |
| **g** | Go to specific time (enter seconds) |
| **s** | Set freeze frame start time (when ring appears) |
| **a** | Set start trim (clip begins here) |
| **b** | Set end trim (clip ends here) |
| **+** / **-** | Increase / decrease ring radius |
| **Left Click** | Set ring center at cursor position |
| **Mouse Wheel** | Adjust ring radius |
| **r** | Reset all markers and trims |
| **Enter** | Accept current clip and move to next |
| **q** / **Esc** | Quit marking session |

---

## ⚡ Batch Processing

Process multiple athletes efficiently:

```bash
# Render all athletes in athletes/ directory
python batch_render.py

# Render specific athletes
python batch_render.py --names "Jane Smith" "John Doe"

# Force re-render existing videos
python batch_render.py --force

# Parallel processing (use with caution - FFmpeg is CPU-intensive)
python batch_render.py --jobs 2

# Dry run to see what would be processed
python batch_render.py --dry-run

# Keep intermediate work files
python batch_render.py --keep-work
```

---

## 🛠 Requirements

### System Requirements

- **OS**: Ubuntu 24.04+ (or similar Linux distribution)
- **Python**: 3.9 or higher
- **FFmpeg**: With libx264 and libfreetype support
- **RAM**: 4GB minimum, 8GB+ recommended for HD video
- **Disk Space**: ~500MB per athlete (depends on video length)

### Python Dependencies

- `opencv-python` - Video frame manipulation and display
- `Pillow` - Image processing for intro slates
- `PyYAML` - Configuration management
- `pytest` - Testing framework (development)
- `pyinstaller` - Standalone application packaging (optional)

### Verifying Installation

```bash
# Check FFmpeg
ffmpeg -version | grep libx264

# Check Python packages
source .venv/bin/activate
python -c "import cv2, PIL, yaml; print('All dependencies OK')"
```

---

## 📚 Documentation

- **[CLAUDE.md](CLAUDE.md)** - Comprehensive developer guide and technical documentation
- **[PACKAGING.md](PACKAGING.md)** - Instructions for creating standalone executables
- **[ENHANCEMENTS.md](ENHANCEMENTS.md)** - Enhanced features and GUI documentation
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute to the project
- **[SECURITY.md](SECURITY.md)** - Security policy and vulnerability reporting
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes
- **[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)** - Third-party software licenses

---

## 🔧 Troubleshooting

### Common Issues

**FFmpeg not found or missing codecs**
```bash
# Verify FFmpeg installation
ffmpeg -version | grep libx264
ffmpeg -version | grep libfreetype

# Reinstall if needed
sudo apt install ffmpeg
```

**Python import errors**
```bash
# Activate virtual environment
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Video preview not working (reorder_clips.py)**
- Ensure you have a system video player installed (VLC, mpv, etc.)
- The tool uses your default video player for preview

**Performance issues with large videos**
- Use `--jobs 1` for batch processing on limited hardware
- Close other applications during rendering
- Consider reducing source video resolution before processing

**GUI not launching**
```bash
# Check Tkinter installation
python -c "import tkinter; print('Tkinter OK')"

# On Ubuntu, install if missing
sudo apt install python3-tk
```

**"players_database.json permission denied"**
```bash
# Fix file permissions
chmod 600 players_database.json
```

### Getting Help

- **Issues**: [GitHub Issues](https://github.com/johnahull/highlight_tool/issues)
- **Discussions**: Open a GitHub Discussion for questions
- **Email**: john@johnahull.com

---

## 🔒 Security & Privacy

SoccerHype takes security and privacy seriously:

- **PII Protection**: Player database (`players_database.json`) is excluded from version control
- **Local Processing**: All video processing happens on your machine
- **No Telemetry**: No data collection or phone-home functionality
- **Input Validation**: All user inputs are sanitized to prevent injection attacks
- **Secure Subprocess Calls**: FFmpeg is invoked safely without shell injection risks

**Report security vulnerabilities**: See [SECURITY.md](SECURITY.md) for our security policy.

---

## 📌 Project Notes

### Important Behaviors

- **Audio Stripping**: All output videos have audio removed to avoid music licensing issues
- **Resolution**: Works best with 1080p or higher source footage
- **Freeze Duration**: Default 1.25s ring freeze (configurable in `render_highlight.py`)
- **Coordinate System**: Uses standardized 1920px-wide proxies for consistent positioning
- **Intro Media**: Place player pictures or intro videos in the `intro/` folder for custom slates

### Limitations

- Currently optimized for Linux (Ubuntu 24.04+)
- Windows/macOS users should use standalone app packages (see [PACKAGING.md](PACKAGING.md))
- No built-in video editing (clips should be pre-trimmed for content)
- Single player tracking per clip (future: multi-player support)

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

### Third-Party Licenses

SoccerHype uses several open-source libraries. See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for complete license information, including:

- FFmpeg (LGPL/GPL)
- OpenCV (Apache 2.0)
- Pillow (HPND)
- PyYAML (MIT)

---

## 🤝 Contributing

We welcome contributions! Whether it's bug fixes, new features, documentation improvements, or translations.

**Before contributing**, please:
1. Read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines
2. Check existing [issues](https://github.com/johnahull/highlight_tool/issues) and [pull requests](https://github.com/johnahull/highlight_tool/pulls)
3. Follow our [Code of Conduct](CODE_OF_CONDUCT.md)

**Ways to contribute**:
- 🐛 Report bugs
- 💡 Suggest features
- 📝 Improve documentation
- 🧪 Add tests
- ⚡ Optimize performance
- 🌍 Add translations

---

## 🙏 Acknowledgments

- FFmpeg team for the powerful video processing framework
- OpenCV community for computer vision tools
- Python Pillow maintainers for image processing capabilities
- All contributors and users of SoccerHype

---

## 📧 Contact

**Project Maintainer**: John Hull
**Email**: john@johnahull.com
**GitHub**: [@johnahull](https://github.com/johnahull)
**Repository**: https://github.com/johnahull/highlight_tool

---

<div align="center">

**Made with ⚽ for athletes, parents, and coaches**

[Report Bug](https://github.com/johnahull/highlight_tool/issues) · [Request Feature](https://github.com/johnahull/highlight_tool/issues) · [View Releases](https://github.com/johnahull/highlight_tool/releases)

</div>
