/* Upload tab — drag-and-drop file upload + clip list */

const UploadView = {
  athlete: null,
  project: null,

  init(athlete, project) {
    this.athlete = athlete;
    this.project = project;
    const base = `/api/projects/${encodeURIComponent(athlete)}/${encodeURIComponent(project)}`;
    const container = document.getElementById('tab-upload');

    container.innerHTML = `
      <div class="upload-zone" id="upload-zone">
        <h3>Drop video files here</h3>
        <p>or click to browse — .mp4, .mov, .mkv, .avi, .m4v</p>
        <input type="file" id="file-input" multiple accept=".mp4,.mov,.mkv,.avi,.m4v">
      </div>
      <div style="margin-top:1rem;display:flex;gap:0.5rem;">
        <button class="btn btn-secondary" id="sync-btn">Sync clips_in/</button>
      </div>
      <div class="file-list" id="clip-file-list"></div>
    `;

    const zone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');

    zone.onclick = () => fileInput.click();

    zone.ondragover = (e) => { e.preventDefault(); zone.classList.add('dragover'); };
    zone.ondragleave = () => zone.classList.remove('dragover');
    zone.ondrop = (e) => {
      e.preventDefault();
      zone.classList.remove('dragover');
      this.uploadFiles(e.dataTransfer.files);
    };

    fileInput.onchange = () => {
      if (fileInput.files.length) this.uploadFiles(fileInput.files);
    };

    document.getElementById('sync-btn').onclick = async () => {
      try {
        const result = await api(`${base}/sync`, { method: 'POST' });
        const added = result.added?.length || 0;
        const removed = result.removed?.length || 0;
        if (added || removed) {
          toast(`Synced: +${added} added, -${removed} removed`, 'success');
        } else {
          toast('All clips up to date', 'info');
        }
        this.loadClipList();
        ProjectWorkflow.refreshStatus();
      } catch (e) {
        toast(e.message, 'error');
      }
    };

    this.loadClipList();
  },

  async uploadFiles(fileList) {
    const base = `/api/projects/${encodeURIComponent(this.athlete)}/${encodeURIComponent(this.project)}`;
    const formData = new FormData();
    for (const f of fileList) {
      formData.append('files', f);
    }

    const zone = document.getElementById('upload-zone');
    zone.innerHTML = '<div class="spinner"></div><p style="margin-top:0.5rem;">Uploading...</p>';

    try {
      const res = await fetch(`${base}/upload`, { method: 'POST', body: formData });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Upload failed');
      }
      const result = await res.json();
      toast(`Uploaded ${result.uploaded.length} file(s)`, 'success');
      this.loadClipList();
      ProjectWorkflow.refreshStatus();
    } catch (e) {
      toast(e.message, 'error');
    }

    zone.innerHTML = `
      <h3>Drop video files here</h3>
      <p>or click to browse — .mp4, .mov, .mkv, .avi, .m4v</p>
      <input type="file" id="file-input" multiple accept=".mp4,.mov,.mkv,.avi,.m4v">
    `;
    document.getElementById('file-input').onchange = () => {
      const fi = document.getElementById('file-input');
      if (fi.files.length) this.uploadFiles(fi.files);
    };
    document.getElementById('upload-zone').onclick = () => document.getElementById('file-input').click();
  },

  async loadClipList() {
    const base = `/api/projects/${encodeURIComponent(this.athlete)}/${encodeURIComponent(this.project)}`;
    const list = document.getElementById('clip-file-list');
    try {
      const clips = await api(`${base}/clips`);
      if (clips.length === 0) {
        list.innerHTML = '<div class="empty-state"><p>No clips uploaded yet.</p></div>';
        return;
      }
      list.innerHTML = clips.map(c => `
        <div class="file-item">
          <span class="name">${c.filename}</span>
          <span class="meta">
            ${c.marked ? '<span class="stat-badge marked">Marked</span>' : '<span class="stat-badge clips">Unmarked</span>'}
            ${c.missing ? '<span class="stat-badge rendered">Missing</span>' : ''}
          </span>
        </div>
      `).join('');
    } catch (e) {
      list.innerHTML = `<p>Error: ${e.message}</p>`;
    }
  },
};
