/* Render tab — render trigger + WebSocket progress */

const RenderView = {
  athlete: null,
  project: null,
  ws: null,

  async init(athlete, project) {
    this.athlete = athlete;
    this.project = project;
    if (this.ws) { this.ws.close(); this.ws = null; }

    const container = document.getElementById('tab-render');
    container.innerHTML = `
      <div class="render-panel card" style="padding:2rem;">
        <div id="render-content"></div>
      </div>
    `;

    // Check current status
    const base = `/api/projects/${encodeURIComponent(athlete)}/${encodeURIComponent(project)}`;
    try {
      const status = await api(`${base}/render/status`);
      if (status.status === 'running') {
        this.showProgress(status);
        this.connectWS();
      } else if (status.status === 'done') {
        this.showDone();
      } else {
        this.showStartButton();
      }
    } catch {
      this.showStartButton();
    }
  },

  showStartButton() {
    const base = `/api/projects/${encodeURIComponent(this.athlete)}/${encodeURIComponent(this.project)}`;
    document.getElementById('render-content').innerHTML = `
      <h3>Render Highlight Video</h3>
      <p style="color:var(--text-muted);margin:1rem 0;">
        This will process all marked clips into a final highlight reel.
      </p>
      <button class="btn btn-primary btn-large" id="start-render-btn">Render</button>
    `;

    document.getElementById('start-render-btn').onclick = async () => {
      try {
        await api(`${base}/render`, { method: 'POST' });
        this.showProgress({ progress: 0, status: 'starting' });
        this.connectWS();
      } catch (e) {
        toast(e.message, 'error');
      }
    };
  },

  showProgress(data) {
    document.getElementById('render-content').innerHTML = `
      <h3>Rendering...</h3>
      <div class="progress-container">
        <div class="progress-bar-outer">
          <div class="progress-bar-inner" id="render-progress-bar" style="width:${data.progress || 0}%"></div>
        </div>
        <div class="progress-text" id="render-progress-text">${data.progress || 0}%</div>
      </div>
      <div class="render-output" id="render-output"></div>
    `;
  },

  showDone() {
    const base = `/api/projects/${encodeURIComponent(this.athlete)}/${encodeURIComponent(this.project)}`;
    document.getElementById('render-content').innerHTML = `
      <h3>Render Complete</h3>
      <div class="render-done">
        <video controls preload="metadata" style="max-width:100%;border-radius:8px;">
          <source src="${base}/output" type="video/mp4">
        </video>
        <div style="margin-top:1rem;display:flex;gap:0.5rem;justify-content:center;">
          <a href="${base}/output" class="btn btn-primary" download>Download</a>
          <button class="btn btn-secondary" id="re-render-btn">Re-Render</button>
        </div>
      </div>
    `;
    document.getElementById('re-render-btn').onclick = () => {
      this.showStartButton();
    };
    ProjectWorkflow.refreshStatus();
  },

  showError(message) {
    document.getElementById('render-content').innerHTML = `
      <h3 style="color:var(--danger);">Render Failed</h3>
      <p style="margin:1rem 0;">${message}</p>
      <button class="btn btn-primary" id="retry-render-btn">Try Again</button>
    `;
    document.getElementById('retry-render-btn').onclick = () => this.showStartButton();
  },

  connectWS() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${location.host}/api/projects/${encodeURIComponent(this.athlete)}/${encodeURIComponent(this.project)}/render/ws`;

    this.ws = new WebSocket(url);

    this.ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      const bar = document.getElementById('render-progress-bar');
      const text = document.getElementById('render-progress-text');
      const output = document.getElementById('render-output');

      if (bar) bar.style.width = `${data.progress}%`;
      if (text) text.textContent = `${data.progress}%`;
      if (output && data.output) {
        output.textContent = data.output.join('\n');
        output.scrollTop = output.scrollHeight;
      }

      if (data.status === 'done') {
        this.showDone();
        this.ws.close();
      } else if (data.status === 'error') {
        this.showError(data.error || 'Unknown error');
        this.ws.close();
      }
    };

    this.ws.onerror = () => {
      // Fall back to polling
      this.pollStatus();
    };

    this.ws.onclose = () => {
      this.ws = null;
    };
  },

  async pollStatus() {
    const base = `/api/projects/${encodeURIComponent(this.athlete)}/${encodeURIComponent(this.project)}`;
    const poll = async () => {
      try {
        const data = await api(`${base}/render/status`);
        const bar = document.getElementById('render-progress-bar');
        const text = document.getElementById('render-progress-text');
        if (bar) bar.style.width = `${data.progress}%`;
        if (text) text.textContent = `${data.progress}%`;

        if (data.status === 'done') {
          this.showDone();
          return;
        }
        if (data.status === 'error') {
          this.showError(data.error || 'Unknown error');
          return;
        }
        if (data.status === 'running' || data.status === 'starting') {
          setTimeout(poll, 1000);
        }
      } catch {
        setTimeout(poll, 2000);
      }
    };
    poll();
  },
};
