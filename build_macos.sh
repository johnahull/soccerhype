#!/bin/bash
# Build script for creating standalone SoccerHype macOS application
# Requires: Python 3.9+, PyInstaller, FFmpeg binary

set -e  # Exit on error

echo "========================================"
echo "SoccerHype macOS Build Script"
echo "========================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.9 or higher."
    exit 1
fi

echo "Python version: $(python3 --version)"

# Check if PyInstaller is installed
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    pip3 install pyinstaller
fi

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Download FFmpeg if not present
if [ ! -f "binaries/ffmpeg" ]; then
    echo ""
    echo "FFmpeg not found in binaries directory."
    echo "Please download FFmpeg and place the ffmpeg binary in the binaries/ folder."
    echo ""
    echo "You can download FFmpeg from: https://ffmpeg.org/download.html"
    echo "Or run: python3 bundle_ffmpeg.py --platform macos"
    echo ""
    read -p "Continue without FFmpeg bundling? (y/N): " continue
    if [[ ! "$continue" =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "FFmpeg found: binaries/ffmpeg"
    # Ensure ffmpeg is executable
    chmod +x binaries/ffmpeg
fi

# Clean previous builds
echo ""
echo "Cleaning previous builds..."
rm -rf build dist

# Run PyInstaller
echo ""
echo "Building SoccerHype application..."
pyinstaller soccerhype.spec

# Copy fonts if available
if [ -d "/System/Library/Fonts" ]; then
    echo ""
    echo "Checking for DejaVu fonts..."

    # Create fonts directory in the app bundle
    mkdir -p "dist/SoccerHype.app/Contents/Resources/fonts"

    # Try to find and copy DejaVu fonts from common locations
    if [ -f "/Library/Fonts/DejaVuSans.ttf" ]; then
        cp /Library/Fonts/DejaVuSans*.ttf "dist/SoccerHype.app/Contents/Resources/fonts/" 2>/dev/null || true
    elif [ -f "/System/Library/Fonts/Supplemental/DejaVuSans.ttf" ]; then
        cp /System/Library/Fonts/Supplemental/DejaVuSans*.ttf "dist/SoccerHype.app/Contents/Resources/fonts/" 2>/dev/null || true
    else
        echo "Warning: DejaVu fonts not found. The app will use system default fonts."
    fi
fi

# Create README in dist
echo ""
echo "Creating distribution README..."
cat > "dist/README.txt" << 'EOF'
SoccerHype - Standalone macOS Application
==========================================

Installation:
1. Drag SoccerHype.app to your Applications folder
2. Double-click to launch

Requirements:
- macOS 10.13 (High Sierra) or later
- FFmpeg must be bundled or installed system-wide
- Approximately 500MB free disk space for video processing

First Launch:
- You may need to right-click and select "Open" the first time
  to bypass Gatekeeper if the app is not code-signed

Usage:
- Launch SoccerHype.app to open the main application
- Create athlete folders and add video clips
- Mark plays interactively
- Render professional highlight videos

For support and documentation, visit the project repository.
EOF

echo ""
echo "========================================"
echo "Build completed successfully!"
echo "========================================"
echo ""
echo "Output location: dist/SoccerHype.app"
echo ""
echo "To test the application:"
echo "  open dist/SoccerHype.app"
echo ""
echo "To create a DMG installer:"
echo "  hdiutil create -volname SoccerHype -srcfolder dist/SoccerHype.app -ov -format UDZO dist/SoccerHype.dmg"
echo ""
echo "For code signing (required for distribution):"
echo "  codesign --deep --force --verify --verbose --sign 'Developer ID Application: Your Name' dist/SoccerHype.app"
echo ""
