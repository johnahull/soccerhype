/* Reorder tab — drag-and-drop clip ordering */

const ReorderView = {
  athlete: null,
  project: null,
  clips: [],

  async init(athlete, project) {
    this.athlete = athlete;
    this.project = project;
    const container = document.getElementById('tab-reorder');

    container.innerHTML = `
      <div class="page-header">
        <h4>Drag clips to reorder</h4>
        <button class="btn btn-primary" id="save-order-btn">Save Order</button>
      </div>
      <ul class="reorder-list" id="reorder-list"></ul>
    `;

    document.getElementById('save-order-btn').onclick = () => this.saveOrder();
    await this.loadClips();
  },

  async loadClips() {
    const base = `/api/projects/${encodeURIComponent(this.athlete)}/${encodeURIComponent(this.project)}`;
    this.clips = await api(`${base}/clips`);
    this.renderList();
  },

  renderList() {
    const list = document.getElementById('reorder-list');
    const base = `/api/projects/${encodeURIComponent(this.athlete)}/${encodeURIComponent(this.project)}`;

    if (this.clips.length === 0) {
      list.innerHTML = '<div class="empty-state"><p>No clips to reorder.</p></div>';
      return;
    }

    list.innerHTML = this.clips.map((c, i) => `
      <li class="reorder-item" draggable="true" data-index="${i}" data-filename="${c.filename}">
        <span class="drag-handle">&#x2630;</span>
        <img class="thumb" src="${base}/clip/${c.index}/thumb" alt="" loading="lazy"
             onerror="this.style.display='none'">
        <span class="clip-name">${c.filename}</span>
        <span class="clip-status ${c.marked ? 'marked' : 'unmarked'}">${c.marked ? 'Marked' : 'Unmarked'}</span>
      </li>
    `).join('');

    this.bindDragEvents();
  },

  bindDragEvents() {
    const list = document.getElementById('reorder-list');
    let dragItem = null;

    list.querySelectorAll('.reorder-item').forEach(item => {
      item.ondragstart = (e) => {
        dragItem = item;
        item.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', item.dataset.index);
      };

      item.ondragend = () => {
        item.classList.remove('dragging');
        dragItem = null;
        list.querySelectorAll('.reorder-item').forEach(el => el.style.borderTop = '');
      };

      item.ondragover = (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        if (item !== dragItem) {
          item.style.borderTop = '2px solid var(--accent)';
        }
      };

      item.ondragleave = () => {
        item.style.borderTop = '';
      };

      item.ondrop = (e) => {
        e.preventDefault();
        item.style.borderTop = '';
        if (!dragItem || item === dragItem) return;

        // Reorder in DOM
        const allItems = [...list.querySelectorAll('.reorder-item')];
        const fromIdx = allItems.indexOf(dragItem);
        const toIdx = allItems.indexOf(item);

        if (fromIdx < toIdx) {
          item.parentNode.insertBefore(dragItem, item.nextSibling);
        } else {
          item.parentNode.insertBefore(dragItem, item);
        }
      };
    });
  },

  async saveOrder() {
    const list = document.getElementById('reorder-list');
    const items = [...list.querySelectorAll('.reorder-item')];
    const filenames = items.map(el => el.dataset.filename);

    const base = `/api/projects/${encodeURIComponent(this.athlete)}/${encodeURIComponent(this.project)}`;
    try {
      await api(`${base}/order`, {
        method: 'PUT',
        body: JSON.stringify({ filenames }),
      });
      toast('Clip order saved', 'success');
      ProjectWorkflow.refreshStatus();
    } catch (e) {
      toast(e.message, 'error');
    }
  },
};
