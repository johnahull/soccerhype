/* Dashboard — athlete/project card grid */

const Dashboard = {
  async render() {
    App.root.innerHTML = `
      <div class="page-header">
        <h1>Athletes</h1>
        <button class="btn btn-primary" id="new-athlete-btn">+ New Athlete</button>
      </div>
      <div id="athlete-list"></div>
    `;

    document.getElementById('new-athlete-btn').onclick = () => {
      showModal('New Athlete', 'Athlete name', async (name) => {
        try {
          await api('/api/athletes', { method: 'POST', body: JSON.stringify({ name }) });
          toast(`Created "${name}"`, 'success');
          this.render();
        } catch (e) {
          toast(e.message, 'error');
        }
      });
    };

    await this.loadAthletes();
  },

  async loadAthletes() {
    const container = document.getElementById('athlete-list');
    try {
      const athletes = await api('/api/athletes');

      if (athletes.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <h3>No athletes yet</h3>
            <p>Create an athlete to get started with your first highlight video.</p>
            <button class="btn btn-primary btn-large" id="empty-new-btn">+ Create Athlete</button>
          </div>
        `;
        document.getElementById('empty-new-btn').onclick = () => {
          showModal('New Athlete', 'Athlete name', async (name) => {
            try {
              await api('/api/athletes', { method: 'POST', body: JSON.stringify({ name }) });
              toast(`Created "${name}"`, 'success');
              this.render();
            } catch (e) {
              toast(e.message, 'error');
            }
          });
        };
        return;
      }

      container.innerHTML = '<div class="athlete-grid"></div>';
      const grid = container.querySelector('.athlete-grid');

      for (const athlete of athletes) {
        const card = document.createElement('div');
        card.className = 'card athlete-card';

        const structBadge = athlete.structure === 'v2'
          ? '<span class="structure-badge">v2</span>'
          : '<span class="structure-badge">v1</span>';

        let projectsHtml = '';
        if (athlete.projects.length === 0) {
          projectsHtml = '<div class="project-list"><p style="color:var(--text-muted);font-size:0.85rem;">No projects yet</p></div>';
        } else {
          projectsHtml = '<div class="project-list">' + athlete.projects.map(p => {
            const renderedBadge = p.rendered
              ? '<span class="stat-badge done">Rendered</span>'
              : '';
            return `
              <div class="project-item" data-athlete="${athlete.name}" data-project="${p.name}">
                <span class="name">${p.name}</span>
                <span class="stats">
                  <span class="stat-badge clips">${p.clip_count} clips</span>
                  <span class="stat-badge marked">${p.marked_count} marked</span>
                  ${renderedBadge}
                </span>
              </div>
            `;
          }).join('') + '</div>';
        }

        card.innerHTML = `
          <div class="athlete-card-header">
            <h3>${athlete.name} ${structBadge}</h3>
          </div>
          ${projectsHtml}
          ${athlete.structure === 'v2' ? `<div style="padding:0.5rem 1.25rem;border-top:1px solid var(--border);">
            <button class="btn btn-secondary" style="width:100%;font-size:0.8rem;" data-new-project="${athlete.name}">+ New Project</button>
          </div>` : ''}
        `;

        grid.appendChild(card);
      }

      // Click handlers for projects
      grid.querySelectorAll('.project-item').forEach(item => {
        item.onclick = () => {
          const a = item.dataset.athlete;
          const p = item.dataset.project;
          App.navigate(`/project/${encodeURIComponent(a)}/${encodeURIComponent(p)}`);
        };
      });

      // New project buttons
      grid.querySelectorAll('[data-new-project]').forEach(btn => {
        btn.onclick = (e) => {
          e.stopPropagation();
          const athleteName = btn.dataset.newProject;
          showModal('New Project', 'Project name (e.g., Fall 2026)', async (name) => {
            try {
              await api(`/api/athletes/${encodeURIComponent(athleteName)}/projects`, {
                method: 'POST',
                body: JSON.stringify({ name }),
              });
              toast(`Created project "${name}"`, 'success');
              this.render();
            } catch (e) {
              toast(e.message, 'error');
            }
          });
        };
      });

    } catch (e) {
      container.innerHTML = `<div class="empty-state"><p>Error loading athletes: ${e.message}</p></div>`;
    }
  },
};
