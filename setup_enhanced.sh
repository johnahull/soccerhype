#!/usr/bin/env bash
# setup_enhanced.sh — Enhanced setup script for SoccerHype GUI improvements
# Installs system packages, Python dependencies, and sets up the enhanced environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PY_MIN="3.9"
VENV_DIR=".venv"
ENHANCED_BRANCH="feature/gui-improvements"

# Enhanced package lists
APT_PACKAGES=(
  ffmpeg
  python3-venv
  python3-tk
  python3-dev
  fonts-dejavu-core
  libgl1
  libglib2.0-0
  libgtk-3-0
  libqt5gui5
  libxcb-xinerama0
  libfontconfig1-dev
  libfreetype6-dev
)

PIP_PACKAGES=(
  opencv-python
  pillow
  pyyaml
  pytest
  tkinter
  numpy
)

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

version_ge() {
    [ "$(printf '%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]
}

check_git_branch() {
    local current_branch
    current_branch=$(git branch --show-current 2>/dev/null || echo "main")

    if [ "$current_branch" != "$ENHANCED_BRANCH" ]; then
        log_warning "Not on enhanced branch ($ENHANCED_BRANCH). Current branch: $current_branch"
        echo "Would you like to switch to the enhanced branch? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            if git branch | grep -q "$ENHANCED_BRANCH"; then
                git checkout "$ENHANCED_BRANCH"
                log_success "Switched to $ENHANCED_BRANCH"
            else
                log_error "Branch $ENHANCED_BRANCH not found"
                exit 1
            fi
        fi
    else
        log_success "On enhanced branch: $current_branch"
    fi
}

check_python() {
    if ! command -v python3 >/dev/null 2>&1; then
        log_error "python3 not found. Install Python 3 first."
        exit 1
    fi

    local py_ver
    py_ver="$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
    if ! version_ge "$py_ver" "$PY_MIN"; then
        log_error "Python $PY_MIN+ required, found $py_ver"
        exit 1
    fi

    log_success "Python $py_ver detected"
}

install_system_packages() {
    log_info "Installing system packages..."

    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -y
        sudo apt-get install -y "${APT_PACKAGES[@]}"
        log_success "System packages installed"
    elif command -v yum >/dev/null 2>&1; then
        log_warning "YUM detected. Package names may differ. Installing core packages..."
        sudo yum install -y ffmpeg python3-tkinter python3-devel
    elif command -v brew >/dev/null 2>&1; then
        log_info "macOS detected. Installing with Homebrew..."
        brew install ffmpeg python-tk
    else
        log_error "Package manager not detected. Please install packages manually:"
        printf '%s\n' "${APT_PACKAGES[@]}"
        exit 1
    fi
}

verify_ffmpeg() {
    log_info "Verifying FFmpeg installation..."

    if ! command -v ffmpeg >/dev/null 2>&1; then
        log_error "FFmpeg not found in PATH"
        exit 1
    fi

    # Check for required features
    local ffmpeg_version
    ffmpeg_version=$(ffmpeg -version | head -n1)
    log_info "FFmpeg version: $ffmpeg_version"

    # Test basic functionality
    if ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=1 -y /tmp/test_ffmpeg.mp4 2>/dev/null; then
        rm -f /tmp/test_ffmpeg.mp4
        log_success "FFmpeg working correctly"
    else
        log_error "FFmpeg test failed"
        exit 1
    fi
}

setup_python_environment() {
    log_info "Setting up Python virtual environment..."

    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
        log_success "Created virtual environment at $VENV_DIR"
    else
        log_info "Using existing virtual environment at $VENV_DIR"
    fi

    # Activate virtual environment
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"

    # Upgrade pip and install packages
    python -m pip install --upgrade pip wheel setuptools

    if [ -f "requirements.txt" ]; then
        log_info "Installing packages from requirements.txt..."
        pip install -r requirements.txt
    else
        log_info "Installing core packages..."
        pip install "${PIP_PACKAGES[@]}"
    fi

    log_success "Python environment setup complete"
}

test_python_imports() {
    log_info "Testing Python imports..."

    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"

    local test_script="
import sys
print(f'Python: {sys.version}')

try:
    import cv2
    print(f'OpenCV: {cv2.__version__}')
except ImportError as e:
    print(f'OpenCV import failed: {e}')
    sys.exit(1)

try:
    import PIL
    print(f'Pillow: {PIL.__version__}')
except ImportError as e:
    print(f'Pillow import failed: {e}')
    sys.exit(1)

try:
    import tkinter
    root = tkinter.Tk()
    root.withdraw()  # Hide window
    root.destroy()
    print('Tkinter: Working')
except Exception as e:
    print(f'Tkinter test failed: {e}')
    sys.exit(1)

try:
    import numpy as np
    print(f'NumPy: {np.__version__}')
except ImportError as e:
    print(f'NumPy import failed: {e}')
    sys.exit(1)

print('All imports successful!')
"

    if python3 -c "$test_script"; then
        log_success "All Python dependencies working"
    else
        log_error "Python dependency test failed"
        exit 1
    fi
}

setup_directories() {
    log_info "Setting up directory structure..."

    # Create enhanced directories
    mkdir -p athletes
    mkdir -p logs
    mkdir -p templates
    mkdir -p utils

    # Set up sample templates
    if [ ! -f "templates/soccer_player.json" ]; then
        cat > "templates/soccer_player.json" << 'EOF'
{
  "name": "",
  "position": "Midfielder",
  "grad_year": "2025",
  "club_team": "",
  "high_school": "",
  "height_weight": "",
  "gpa": "",
  "email": "",
  "phone": ""
}
EOF
        log_success "Created sample soccer player template"
    fi

    log_success "Directory structure created"
}

test_enhanced_features() {
    log_info "Testing enhanced features..."

    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"

    # Test error handling import
    if python3 -c "from utils.error_handling import ErrorHandler; print('Error handling: OK')" 2>/dev/null; then
        log_success "Enhanced error handling available"
    else
        log_warning "Enhanced error handling not available (will use basic error handling)"
    fi

    # Test GUI import
    if python3 -c "import soccerhype_gui; print('Enhanced GUI: OK')" 2>/dev/null; then
        log_success "Enhanced GUI available"
    else
        log_warning "Enhanced GUI not available"
    fi

    # Test enhanced video player
    if python3 -c "import enhanced_video_player; print('Enhanced video player: OK')" 2>/dev/null; then
        log_success "Enhanced video player available"
    else
        log_warning "Enhanced video player not available"
    fi
}

create_launch_scripts() {
    log_info "Creating launch scripts..."

    # Create main launcher
    cat > "launch_soccerhype.sh" << 'EOF'
#!/bin/bash
# SoccerHype Enhanced Launcher

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Virtual environment not found. Run setup_enhanced.sh first."
    exit 1
fi

# Launch enhanced GUI
if [ -f "soccerhype_gui.py" ]; then
    echo "Launching SoccerHype Enhanced GUI..."
    python soccerhype_gui.py "$@"
else
    echo "Enhanced GUI not found. Falling back to command line tools."
    echo "Available commands:"
    echo "  python create_athlete.py 'Athlete Name'"
    echo "  python mark_play.py"
    echo "  python reorder_clips.py"
    echo "  python render_highlight.py"
    echo "  python batch_render.py"
fi
EOF

    chmod +x "launch_soccerhype.sh"

    # Create enhanced marking launcher
    cat > "launch_enhanced_marking.sh" << 'EOF'
#!/bin/bash
# Enhanced Marking Launcher

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

source .venv/bin/activate

if [ -f "mark_play_enhanced.py" ]; then
    python mark_play_enhanced.py "$@"
else
    echo "Enhanced marking not available, using standard version"
    python mark_play.py "$@"
fi
EOF

    chmod +x "launch_enhanced_marking.sh"

    log_success "Launch scripts created"
}

show_completion_message() {
    log_success "SoccerHype Enhanced setup completed successfully!"
    echo
    echo -e "${GREEN}🎉 Enhanced Features Available:${NC}"
    echo "  • Unified GUI Application"
    echo "  • Enhanced Video Marking with Smart Defaults"
    echo "  • Advanced Video Player with Zoom"
    echo "  • Improved Error Handling and Logging"
    echo "  • Template System for Player Profiles"
    echo "  • Batch Processing Capabilities"
    echo
    echo -e "${BLUE}🚀 Getting Started:${NC}"
    echo "  1. Launch the enhanced GUI:"
    echo "     ./launch_soccerhype.sh"
    echo
    echo "  2. Or use individual enhanced tools:"
    echo "     ./launch_enhanced_marking.sh"
    echo "     python reorder_clips_enhanced.py"
    echo
    echo "  3. Create your first athlete:"
    echo "     Click 'New Athlete' in the GUI"
    echo "     Or: python create_athlete.py 'Athlete Name'"
    echo
    echo -e "${YELLOW}📚 Documentation:${NC}"
    echo "  • Enhanced features: ENHANCEMENTS.md"
    echo "  • Original guide: README.md"
    echo "  • Logs directory: logs/"
    echo "  • Templates directory: templates/"
    echo
    echo -e "${GREEN}✅ Next Steps:${NC}"
    echo "  1. Create an athlete folder"
    echo "  2. Add video clips to clips_in/"
    echo "  3. Mark plays with enhanced tools"
    echo "  4. Render your highlight video"
    echo
    echo "Enjoy creating professional highlight videos! 🎬"
}

# Main execution
main() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                    SoccerHype Enhanced Setup                 ║${NC}"
    echo -e "${BLUE}║              Professional Highlight Video Creator            ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo

    # Check if we're in a git repository
    if git rev-parse --git-dir > /dev/null 2>&1; then
        check_git_branch
    else
        log_warning "Not in a git repository. Continuing with current files."
    fi

    # System checks
    check_python

    # Installation steps
    install_system_packages
    verify_ffmpeg
    setup_python_environment
    test_python_imports
    setup_directories
    test_enhanced_features
    create_launch_scripts

    # Completion
    show_completion_message
}

# Run main function
main "$@"