/* Mark tab — HTML5 video + canvas overlay for ring placement */

const MarkView = {
  athlete: null,
  project: null,
  clips: [],
  currentIndex: -1,
  video: null,
  canvas: null,
  ctx: null,
  isPlaying: false,
  animFrameId: null,

  // Mark state for current clip
  markerX: null,
  markerY: null,
  radius: 72,
  spotTime: null,
  spotFrame: null,
  startTrim: 0,
  endTrim: 0,
  zoom: 1.0,
  section: null,
  hoverX: null,
  hoverY: null,

  FPS: 30,
  PROXY_W: 1920,

  async init(athlete, project) {
    this.athlete = athlete;
    this.project = project;
    this.currentIndex = -1;

    const container = document.getElementById('tab-mark');
    container.innerHTML = `
      <div class="mark-container">
        <div class="mark-nav" id="mark-nav">
          <span class="clip-info" id="clip-info">Loading...</span>
          <div class="nav-buttons">
            <button class="btn btn-secondary" id="mark-prev">Previous</button>
            <button class="btn btn-secondary" id="mark-skip">Skip</button>
            <button class="btn btn-primary" id="mark-accept">Accept & Next</button>
          </div>
        </div>

        <div class="video-wrapper" id="video-wrapper">
          <video id="mark-video" preload="auto" playsinline></video>
          <canvas id="mark-canvas"></canvas>
          <div class="click-layer" id="click-layer"></div>
        </div>

        <div class="mark-controls">
          <div class="control-group">
            <h4>Playback</h4>
            <input type="range" class="seek-bar" id="seek-bar" min="0" max="1000" value="0">
            <div class="playback-controls">
              <button id="play-btn">Play</button>
              <button id="step-back">&lt; Frame</button>
              <button id="step-fwd">Frame &gt;</button>
              <span class="time-display" id="time-display">0:00.00</span>
            </div>
          </div>

          <div class="control-group">
            <h4>Ring</h4>
            <div class="control-row">
              <label>Radius</label>
              <input type="range" id="radius-slider" min="10" max="300" value="72">
              <span class="value-display" id="radius-display">72px</span>
            </div>
            <div class="control-row">
              <label>Position</label>
              <span class="value-display" id="pos-display">Click on video</span>
            </div>
          </div>

          <div class="control-group">
            <h4>Spotlight Frame</h4>
            <div class="control-row">
              <button class="btn btn-secondary" id="set-spot-btn">Set Current Frame as Spotlight</button>
              <span class="value-display" id="spot-display">Not set</span>
            </div>
          </div>

          <div class="control-group">
            <h4>Trim</h4>
            <div class="control-row">
              <label>Start trim</label>
              <input type="range" id="start-trim-slider" min="0" max="1000" value="0">
              <span class="value-display trim-val" id="start-trim-display">0.00s</span>
            </div>
            <div class="control-row">
              <label>End trim</label>
              <input type="range" id="end-trim-slider" min="0" max="1000" value="0">
              <span class="value-display trim-val" id="end-trim-display">0.00s</span>
            </div>
          </div>

          <div class="control-group">
            <h4>Section</h4>
            <div class="control-row">
              <select id="section-select" style="padding:0.4rem;border-radius:4px;border:1px solid var(--border);">
                <option value="">None</option>
                <option value="Goals">Goals</option>
                <option value="Assists">Assists</option>
                <option value="Dribbling">Dribbling</option>
                <option value="Defense">Defense</option>
                <option value="Saves">Saves</option>
                <option value="Headers">Headers</option>
                <option value="Free Kicks">Free Kicks</option>
                <option value="Penalties">Penalties</option>
                <option value="Set Pieces">Set Pieces</option>
                <option value="Passing">Passing</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    `;

    this.video = document.getElementById('mark-video');
    this.canvas = document.getElementById('mark-canvas');
    this.ctx = this.canvas.getContext('2d');

    this.bindEvents();
    await this.loadClips();

    // Go to first unmarked clip, or first clip
    const firstUnmarked = this.clips.findIndex(c => !c.marked);
    this.goToClip(firstUnmarked >= 0 ? firstUnmarked : 0);
  },

  bindEvents() {
    const clickLayer = document.getElementById('click-layer');
    const video = this.video;

    // Click to set ring position
    clickLayer.onclick = (e) => {
      const rect = clickLayer.getBoundingClientRect();
      const scaleX = this.PROXY_W / rect.width;
      const videoHeight = video.videoHeight || 1080;
      const scaleY = videoHeight / rect.height;
      this.markerX = Math.round((e.clientX - rect.left) * scaleX);
      this.markerY = Math.round((e.clientY - rect.top) * scaleY);
      document.getElementById('pos-display').textContent = `${this.markerX}, ${this.markerY}`;
      this.drawOverlay();
    };

    // Hover for ring preview
    clickLayer.onmousemove = (e) => {
      const rect = clickLayer.getBoundingClientRect();
      const scaleX = this.PROXY_W / rect.width;
      const videoHeight = video.videoHeight || 1080;
      const scaleY = videoHeight / rect.height;
      this.hoverX = (e.clientX - rect.left) * scaleX;
      this.hoverY = (e.clientY - rect.top) * scaleY;
      this.drawOverlay();
    };
    clickLayer.onmouseleave = () => {
      this.hoverX = null;
      this.hoverY = null;
      this.drawOverlay();
    };

    // Playback controls
    document.getElementById('play-btn').onclick = () => this.togglePlay();
    document.getElementById('step-back').onclick = () => this.stepFrame(-1);
    document.getElementById('step-fwd').onclick = () => this.stepFrame(1);

    // Seek bar
    const seekBar = document.getElementById('seek-bar');
    seekBar.oninput = () => {
      if (video.duration) {
        video.currentTime = (seekBar.value / 1000) * video.duration;
      }
    };

    // Video time update
    video.ontimeupdate = () => {
      if (video.duration) {
        seekBar.value = (video.currentTime / video.duration) * 1000;
        document.getElementById('time-display').textContent = formatTime(video.currentTime);
      }
    };
    video.onplay = () => {
      this.isPlaying = true;
      document.getElementById('play-btn').textContent = 'Pause';
      this.startOverlayLoop();
    };
    video.onpause = () => {
      this.isPlaying = false;
      document.getElementById('play-btn').textContent = 'Play';
      if (this.animFrameId) {
        cancelAnimationFrame(this.animFrameId);
        this.animFrameId = null;
      }
    };
    video.onloadedmetadata = () => {
      this.syncCanvasSize();
      this.setupTrimSliders();
    };

    // Radius slider
    const radiusSlider = document.getElementById('radius-slider');
    radiusSlider.oninput = () => {
      this.radius = parseInt(radiusSlider.value);
      document.getElementById('radius-display').textContent = `${this.radius}px`;
      this.drawOverlay();
    };

    // Trim sliders
    document.getElementById('start-trim-slider').oninput = (e) => {
      if (video.duration) {
        this.startTrim = (e.target.value / 1000) * video.duration;
        document.getElementById('start-trim-display').textContent = `${this.startTrim.toFixed(2)}s`;
      }
    };
    document.getElementById('end-trim-slider').oninput = (e) => {
      if (video.duration) {
        this.endTrim = (e.target.value / 1000) * video.duration;
        document.getElementById('end-trim-display').textContent = `${this.endTrim.toFixed(2)}s`;
      }
    };

    // Spotlight frame
    document.getElementById('set-spot-btn').onclick = () => {
      this.spotTime = video.currentTime;
      this.spotFrame = Math.round(video.currentTime * this.FPS);
      document.getElementById('spot-display').textContent =
        `${formatTime(this.spotTime)} (frame ${this.spotFrame})`;
    };

    // Navigation
    document.getElementById('mark-prev').onclick = () => this.goToClip(this.currentIndex - 1);
    document.getElementById('mark-skip').onclick = () => this.goToClip(this.currentIndex + 1);
    document.getElementById('mark-accept').onclick = () => this.acceptAndNext();

    // Keyboard shortcuts
    this._keyHandler = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
      switch (e.key) {
        case ' ':
          e.preventDefault();
          this.togglePlay();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          if (e.shiftKey) { video.currentTime = Math.max(0, video.currentTime - 5); }
          else { this.stepFrame(-1); }
          break;
        case 'ArrowRight':
          e.preventDefault();
          if (e.shiftKey) { video.currentTime += 5; }
          else { this.stepFrame(1); }
          break;
        case 's':
          document.getElementById('set-spot-btn').click();
          break;
        case 'Enter':
          e.preventDefault();
          this.acceptAndNext();
          break;
      }
    };
    document.addEventListener('keydown', this._keyHandler);

    // Cleanup on tab switch
    App.currentCleanup = () => {
      document.removeEventListener('keydown', this._keyHandler);
      if (this.animFrameId) cancelAnimationFrame(this.animFrameId);
      this.video?.pause();
    };
  },

  syncCanvasSize() {
    const wrapper = document.getElementById('video-wrapper');
    const rect = this.video.getBoundingClientRect();
    this.canvas.width = this.video.videoWidth || this.PROXY_W;
    this.canvas.height = this.video.videoHeight || 1080;
  },

  setupTrimSliders() {
    // Reset trim sliders based on loaded values
    const dur = this.video.duration || 1;
    const startSlider = document.getElementById('start-trim-slider');
    const endSlider = document.getElementById('end-trim-slider');
    startSlider.value = (this.startTrim / dur) * 1000;
    endSlider.value = (this.endTrim / dur) * 1000;
    document.getElementById('start-trim-display').textContent = `${this.startTrim.toFixed(2)}s`;
    document.getElementById('end-trim-display').textContent = `${this.endTrim.toFixed(2)}s`;
  },

  async loadClips() {
    const base = `/api/projects/${encodeURIComponent(this.athlete)}/${encodeURIComponent(this.project)}`;
    this.clips = await api(`${base}/clips`);
  },

  goToClip(index) {
    if (index < 0 || index >= this.clips.length) {
      if (this.clips.length === 0) {
        document.getElementById('clip-info').textContent = 'No clips. Upload some first.';
      }
      return;
    }
    this.currentIndex = index;
    const clip = this.clips[index];
    const base = `/api/projects/${encodeURIComponent(this.athlete)}/${encodeURIComponent(this.project)}`;

    // Load existing mark data if present
    this.markerX = clip.marker_x_std;
    this.markerY = clip.marker_y_std;
    this.radius = clip.radius_std || 72;
    this.spotTime = clip.spot_time;
    this.spotFrame = clip.spot_frame_std;
    this.startTrim = clip.start_trim || 0;
    this.endTrim = clip.end_trim || 0;
    this.zoom = clip.zoom_std || 1.0;
    this.section = clip.section || null;

    // Update UI
    const markedCount = this.clips.filter(c => c.marked).length;
    document.getElementById('clip-info').textContent =
      `Clip ${index + 1} of ${this.clips.length} (${markedCount} marked) — ${clip.filename}`;

    // Update controls
    document.getElementById('radius-slider').value = this.radius;
    document.getElementById('radius-display').textContent = `${this.radius}px`;
    document.getElementById('pos-display').textContent =
      this.markerX != null ? `${this.markerX}, ${this.markerY}` : 'Click on video';
    document.getElementById('spot-display').textContent =
      this.spotTime != null ? `${formatTime(this.spotTime)} (frame ${this.spotFrame})` : 'Not set';

    // Section
    const sectionSelect = document.getElementById('section-select');
    sectionSelect.value = this.section || '';

    // Load video
    this.video.pause();
    this.video.src = `${base}/clip/${index}/video`;
    this.video.load();

    this.video.onloadedmetadata = () => {
      this.syncCanvasSize();
      this.setupTrimSliders();
      this.drawOverlay();
    };
  },

  togglePlay() {
    if (this.video.paused) {
      this.video.play();
    } else {
      this.video.pause();
    }
  },

  stepFrame(direction) {
    this.video.pause();
    this.video.currentTime = Math.max(0, this.video.currentTime + direction / this.FPS);
    this.drawOverlay();
  },

  startOverlayLoop() {
    const loop = () => {
      this.drawOverlay();
      if (this.isPlaying) {
        this.animFrameId = requestAnimationFrame(loop);
      }
    };
    this.animFrameId = requestAnimationFrame(loop);
  },

  drawOverlay() {
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Draw ring at marker position
    if (this.markerX != null && this.markerY != null) {
      this.drawRing(ctx, this.markerX, this.markerY, this.radius, 1.0);
    }

    // Draw hover preview ring (fainter)
    if (this.hoverX != null && this.hoverY != null) {
      if (this.markerX == null) {
        this.drawRing(ctx, this.hoverX, this.hoverY, this.radius, 0.4);
      }
    }

    // Draw trim regions
    if (this.video.duration) {
      const vidW = w;
      if (this.startTrim > 0) {
        const trimW = (this.startTrim / this.video.duration) * vidW;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
        ctx.fillRect(0, 0, trimW, h);
      }
      if (this.endTrim > 0) {
        const trimW = (this.endTrim / this.video.duration) * vidW;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
        ctx.fillRect(vidW - trimW, 0, trimW, h);
      }
    }
  },

  drawRing(ctx, x, y, radius, alpha) {
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.strokeStyle = '#ff0000';
    ctx.lineWidth = 3;
    ctx.shadowColor = '#ff0000';
    ctx.shadowBlur = 8;
    ctx.stroke();
    ctx.restore();
  },

  async acceptAndNext() {
    if (this.currentIndex < 0 || this.currentIndex >= this.clips.length) return;

    if (this.markerX == null || this.markerY == null) {
      toast('Click on the video to set ring position first', 'error');
      return;
    }
    if (this.spotTime == null) {
      toast('Set a spotlight frame first (press S or click the button)', 'error');
      return;
    }

    const base = `/api/projects/${encodeURIComponent(this.athlete)}/${encodeURIComponent(this.project)}`;
    const section = document.getElementById('section-select').value || null;

    try {
      await api(`${base}/clip/${this.currentIndex}/mark`, {
        method: 'PUT',
        body: JSON.stringify({
          marker_x_std: this.markerX,
          marker_y_std: this.markerY,
          radius_std: this.radius,
          spot_time: this.spotTime,
          spot_frame_std: this.spotFrame,
          start_trim: this.startTrim,
          end_trim: this.endTrim,
          zoom_std: this.zoom,
          section: section,
        }),
      });

      this.clips[this.currentIndex].marked = true;
      toast('Mark saved', 'success');
      ProjectWorkflow.refreshStatus();

      // Go to next unmarked, or next clip
      const nextUnmarked = this.clips.findIndex((c, i) => i > this.currentIndex && !c.marked);
      if (nextUnmarked >= 0) {
        this.goToClip(nextUnmarked);
      } else if (this.currentIndex + 1 < this.clips.length) {
        this.goToClip(this.currentIndex + 1);
      } else {
        toast('All clips marked!', 'success');
      }
    } catch (e) {
      toast(e.message, 'error');
    }
  },
};
