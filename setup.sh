#!/bin/bash
set -e

echo "=== Installing system dependencies ==="
sudo apt update
sudo apt install -y ffmpeg python3 python3-venv python3-pip \
    libgl1 libsm6 libxext6 fonts-dejavu-core

echo "=== Creating Python virtual environment ==="
python3 -m venv .venv
source .venv/bin/activate

echo "=== Installing Python packages ==="
pip install --upgrade pip
pip install opencv-python ffmpeg-python pydub

echo "=== Creating folders ==="
mkdir -p clips_in work out

echo "Setup complete."
echo "Next steps:"
echo "1) Put .mp4 or .mov files into clips_in/"
echo "2) Run: source .venv/bin/activate && python mark_clips.py"
echo "3) Run: python render_highlight.py"

