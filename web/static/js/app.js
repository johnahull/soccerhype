/* SoccerHype SPA Router and Shared Utilities */

const App = {
  root: document.getElementById('app'),
  breadcrumb: document.getElementById('breadcrumb'),

  routes: {},
  currentCleanup: null,

  init() {
    window.addEventListener('popstate', () => this.route());
    document.addEventListener('click', (e) => {
      const link = e.target.closest('[data-link]');
      if (link) {
        e.preventDefault();
        this.navigate(link.getAttribute('href') || '/');
      }
    });
    this.route();
  },

  navigate(path) {
    history.pushState(null, '', path);
    this.route();
  },

  route() {
    if (this.currentCleanup) {
      this.currentCleanup();
      this.currentCleanup = null;
    }

    const path = location.pathname;

    // Match /project/:athlete/:project
    const projectMatch = path.match(/^\/project\/([^/]+)\/([^/]+)\/?$/);
    if (projectMatch) {
      const athlete = decodeURIComponent(projectMatch[1]);
      const project = decodeURIComponent(projectMatch[2]);
      this.setBreadcrumb([
        { label: 'Dashboard', href: '/' },
        { label: athlete },
        { label: project },
      ]);
      ProjectWorkflow.render(athlete, project);
      return;
    }

    // Default: dashboard
    this.setBreadcrumb([]);
    Dashboard.render();
  },

  setBreadcrumb(items) {
    this.breadcrumb.innerHTML = '';
    items.forEach((item, i) => {
      if (i > 0) {
        const sep = document.createElement('span');
        sep.className = 'sep';
        sep.textContent = '/';
        this.breadcrumb.appendChild(sep);
      }
      if (item.href) {
        const a = document.createElement('a');
        a.href = item.href;
        a.textContent = item.label;
        a.setAttribute('data-link', '');
        this.breadcrumb.appendChild(a);
      } else {
        const span = document.createElement('span');
        span.textContent = item.label;
        this.breadcrumb.appendChild(span);
      }
    });
  },
};

/* Shared fetch helpers */
async function api(url, opts = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text();
    let msg;
    try { msg = JSON.parse(text).detail; } catch { msg = text; }
    throw new Error(msg || `HTTP ${res.status}`);
  }
  return res.json();
}

function toast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function showModal(title, placeholder, onSubmit) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal">
      <h2>${title}</h2>
      <input type="text" placeholder="${placeholder}" autofocus>
      <div class="modal-actions">
        <button class="btn btn-secondary" data-cancel>Cancel</button>
        <button class="btn btn-primary" data-submit>Create</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  const input = overlay.querySelector('input');
  const submit = () => {
    const val = input.value.trim();
    if (val) {
      overlay.remove();
      onSubmit(val);
    }
  };

  overlay.querySelector('[data-cancel]').onclick = () => overlay.remove();
  overlay.querySelector('[data-submit]').onclick = submit;
  input.onkeydown = (e) => { if (e.key === 'Enter') submit(); };
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
  input.focus();
}

function formatTime(seconds) {
  if (!seconds || isNaN(seconds)) return '0:00.00';
  const m = Math.floor(seconds / 60);
  const s = (seconds % 60).toFixed(2);
  return `${m}:${s.padStart(5, '0')}`;
}

/* Project Workflow page (tabbed view) */
const ProjectWorkflow = {
  athlete: null,
  project: null,

  async render(athlete, project) {
    this.athlete = athlete;
    this.project = project;
    const base = `/api/projects/${encodeURIComponent(athlete)}/${encodeURIComponent(project)}`;

    App.root.innerHTML = `
      <div class="status-bar" id="project-status"></div>
      <div class="tabs">
        <button class="tab active" data-tab="upload">Upload</button>
        <button class="tab" data-tab="mark">Mark</button>
        <button class="tab" data-tab="reorder">Reorder</button>
        <button class="tab" data-tab="render">Render</button>
      </div>
      <div id="tab-upload" class="tab-content active"></div>
      <div id="tab-mark" class="tab-content"></div>
      <div id="tab-reorder" class="tab-content"></div>
      <div id="tab-render" class="tab-content"></div>
    `;

    // Tab switching
    App.root.querySelectorAll('.tab').forEach(tab => {
      tab.onclick = () => {
        App.root.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        App.root.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const target = document.getElementById(`tab-${tab.dataset.tab}`);
        target.classList.add('active');

        // Initialize tab content on first view
        if (tab.dataset.tab === 'mark') MarkView.init(athlete, project);
        if (tab.dataset.tab === 'reorder') ReorderView.init(athlete, project);
        if (tab.dataset.tab === 'render') RenderView.init(athlete, project);
      };
    });

    // Load status and initialize upload tab
    this.refreshStatus();
    UploadView.init(athlete, project);
  },

  async refreshStatus() {
    const base = `/api/projects/${encodeURIComponent(this.athlete)}/${encodeURIComponent(this.project)}`;
    try {
      const clips = await api(`${base}/clips`);
      const total = clips.length;
      const marked = clips.filter(c => c.marked).length;
      const renderStatus = await api(`${base}/render/status`);

      document.getElementById('project-status').innerHTML = `
        <div class="status-item"><span class="label">Clips:</span> <span class="value">${total}</span></div>
        <div class="status-item"><span class="label">Marked:</span> <span class="value">${marked} / ${total}</span></div>
        <div class="status-item"><span class="label">Render:</span> <span class="value">${renderStatus.status === 'done' ? 'Done' : renderStatus.status === 'running' ? 'In Progress' : 'Not Started'}</span></div>
      `;
    } catch (e) {
      // Status bar update failed silently
    }
  },
};
