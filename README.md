# soccerhype - Athlete Highlight Video Builder
This is a simple socer highlight video creation tool. It's purpose is to combined existing clips into a single video, provide a method for marking the player in the clips, and then add an intro page if desired. Clips will generaly come from Veo, Trace, or other video, and should already be edited for content. Tt is a Python + FFmpeg tool for quickly creating professional-looking highlight videos for athletes. Designed for parents and coaches who need to produce consistent, good-quality highlight videos

---

## ✨ Features

- **Mark plays interactively** with full playback controls
- **Red spotlight ring** freezes on the marked player for 1.25s before resuming play
- **Optional intro slate** with:
  - Name, Position, Graduation Year
  - Club Team, High School, Height/Weight, GPA
  - Email and/or Phone Number
- **Automatic stitching** of clips into a single video
- **Multi-athlete folder structure** for organized batch processing
- **Batch rendering** for many athletes at once
- **Runs locally** on Ubuntu 24.04 (or similar) — no cloud upload required
- **No audio** in final output (ensures compliance with music licensing)

---

## 📂 Folder Structure
athletes/
<athlete_name>/
clips_in/ # Drop source clips here
work/ # Temporary working files (auto-cleared unless --keep-work)
proxies/
output/ # Final video output (final.mp4)


---

## 🚀 Quick Start

### 1️⃣ Install requirements
```bash
sudo apt update
sudo apt install ffmpeg python3-opencv python3-pil
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

### 2️⃣ **Create athlete folder**
python create_athlete.py "Jane Smith"

This will create:
athletes/Jane Smith/clips_in/
athletes/Jane Smith/work/proxies/
athletes/Jane Smith/output/

3️⃣ Add clips

Place your .mp4, .mov, etc. files in:
athletes/<athlete_name>/clips_in/

4️⃣ Mark plays
python mark_play.py

* Choose the athlete from the menu
* Use controls to navigate, set marker location, freeze-frame start, trims, and ring size
* Press Enter to save each clip’s data

5️⃣ Render the highlight video
python render_highlight.py --dir athletes/<athlete_name>

This produces:
athletes/<athlete_name>/output/final.mp4

🎮 Marking Controls
Key	Action
Space	Play / Pause
, / .	Step -1 / +1 frame (paused)
← / →	Seek ±0.5s
↑ / ↓	Seek ±5s
[ / ]	Playback speed down / up
g	Go to specific time (seconds)
s	Set freeze start (spot_time)
a	Set start trim
b	Set end trim
+ / -	Increase / decrease ring radius
Left Click	Set ring center at cursor
r	Reset marker & trims
Enter	Accept current clip
q / Esc	Quit clip marking

⚡ Batch Processing

To render all athletes in athletes/:

python batch_render.py


Options:

--names NAME1 NAME2    # Only process these athletes
--force                # Re-render even if final.mp4 exists
--keep-work            # Keep intermediate files
--jobs N               # Run N renders in parallel (careful: ffmpeg is CPU-heavy)
--dry-run              # Show what would be rendered without running


Example:

python batch_render.py --names "Jane Smith" "Phia Hull" --force

🛠 Requirements

OS: Ubuntu 24.04+ (should also work on other Linux distros)

Python: 3.9+

Dependencies:

ffmpeg (with libx264, libfreetype)

opencv-python

Pillow

📌 Notes

Audio is stripped from all outputs to avoid licensing issues.

Works best with 1080p or higher footage.

Freeze frame duration is fixed at 1.25s, but can be changed in render_highlight.py.

The red ring overlay is generated dynamically from the marking data.

For exact ring placement, the system uses pixel coordinates from the marking session — ensure your mark_play.py and render_highlight.py use the same scaled resolution.

📄 License

This project is released under the MIT License.
You are free to use, modify, and distribute it as long as the license file is included.

🤝 Contributing

PRs welcome! If you have bug fixes, new features, or performance improvements, open a pull request.
