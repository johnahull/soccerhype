#!/usr/bin/env bash
# setup.sh — one-shot setup for Ubuntu 24.04
# - Installs system packages (ffmpeg, tk, fonts, GL libs)
# - Creates/updates a Python venv at .venv
# - Installs Python deps (opencv-python, pillow, etc.)

set -euo pipefail

# ---- config ----
PY_MIN="3.9"
VENV_DIR=".venv"
APT_PACKAGES=(
  ffmpeg
  python3-venv
  python3-tk
  fonts-dejavu-core
  libgl1
  libglib2.0-0
)

PIP_PACKAGES=(
  opencv-python
  pillow
  pyyaml
  pytest
)

# ---- helpers ----
version_ge() {
  # compare dotted versions: version_ge "$1" "$2" -> 0 (true) if $1 >= $2
  # usage: if version_ge "3.10" "3.9"; then ...
  [ "$(printf '%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]
}

# ---- checks ----
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3 first." >&2
  exit 1
fi

PY_VER="$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
if ! version_ge "$PY_VER" "$PY_MIN"; then
  echo "Python $PY_MIN+ required, found $PY_VER" >&2
  exit 1
fi

# ---- apt packages ----
echo "==> Installing system packages (sudo required)…"
sudo apt-get update -y
sudo apt-get install -y "${APT_PACKAGES[@]}"

# Show ffmpeg version for sanity
echo "==> ffmpeg version:"
ffmpeg -version | head -n1 || true

# ---- venv ----
if [ ! -d "$VENV_DIR" ]; then
  echo "==> Creating virtualenv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
else
  echo "==> Using existing virtualenv at $VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip wheel

# If a requirements.txt exists, prefer that; otherwise install the minimal set.
if [ -f "requirements.txt" ]; then
  echo "==> Installing Python deps from requirements.txt"
  pip install -r requirements.txt
else
  echo "==> Installing Python deps (baseline set)"
  pip install "${PIP_PACKAGES[@]}"
fi

# ---- create base folders if missing ----
mkdir -p athletes

cat <<'EOF'

✅ Setup complete.

Next steps:
  1) Create an athlete:
       python create_athlete.py "Jane Smith"
  2) Drop clips into:
       athletes/Jane Smith/clips_in/
  3) Mark plays:
       python mark_play.py
  4) (Optional) Reorder clips visually:
       python reorder_clips.py
  5) Render:
       python render_highlight.py --dir "athletes/Jane Smith"

Tip:
  - If OpenCV windows don't show, ensure you're running in a desktop session (not SSH without X).
EOF

