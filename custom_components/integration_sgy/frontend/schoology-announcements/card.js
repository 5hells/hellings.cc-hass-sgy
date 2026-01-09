class SchoologyAnnouncementsCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) {
      throw new Error('Missing required property: entity');
    }
    this._config = config;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: 'open' });
    }
  }

  set hass(hass) {
    const entityId = this._config.entity;
    const stateObj = hass.states[entityId];
    const title = this._config.title || 'Announcements';

    if (!stateObj) {
      this.shadowRoot.innerHTML = `<ha-card header="${title}"><div class="empty">Entity not found: ${entityId}</div></ha-card>`;
      return;
    }

    const items = Array.isArray(stateObj.attributes.items) ? stateObj.attributes.items : [];

    const style = `
      <style>
        .container { padding: 16px; }
        .item { border-bottom: 1px solid var(--divider-color); padding: 12px 0; }
        .header { display:flex; align-items:center; gap:10px; }
        .pfp { width:32px; height:32px; border-radius:50%; object-fit:cover; }
        .title { font-weight:600; }
        .meta { color: var(--secondary-text-color); font-size: 12px; }
        .comments { margin-top: 8px; padding-left: 8px; border-left: 2px solid var(--divider-color); }
        .comment { margin: 6px 0; }
      </style>
    `;

    const list = items.map((i) => {
      const pfp = i.profile_picture ? `<img class="pfp" src="${i.profile_picture}" alt="pfp" />` : '';
      const group = i.group ? `<span>${i.group}</span>` : '';
      const likes = typeof i.likes === 'number' ? `<span> • ${i.likes} likes</span>` : '';
      const created = i.created ? ` <div class="meta">${i.created}</div>` : '';
      const comments = Array.isArray(i.comments) && i.comments.length
        ? `<div class="comments">${i.comments.map(c => `<div class="comment"><strong>${c.author}</strong>: ${c.content}${typeof c.likes === 'number' ? ` (${c.likes})` : ''}</div>`).join('')}</div>`
        : '';
      return `
        <div class="item">
          <div class="header">${pfp}<div class="title">${i.title || ''}</div></div>
          <div class="meta">${i.date || ''} ${group}${likes}</div>
          ${created}
          ${comments}
        </div>
      `;
    }).join('');

    this.shadowRoot.innerHTML = `
      <ha-card header="${title}">
        ${style}
        <div class="container">
          ${items.length ? list : '<div class="empty">No announcements</div>'}
        </div>
      </ha-card>
    `;
  }

  getCardSize() {
    return 3;
  }

  getGridOptions() {
    return {
      rows: 4,
      columns: 6,
      min_rows: 2,
      max_rows: 8,
    };
  }

  static getStubConfig() {
    return {
      entity: "sensor.schoology_announcements"
    };
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "entity", required: true, selector: { entity: {} } },
        { name: "title", selector: { text: {} } },
      ],
    };
  }
}

customElements.define('schoology-announcements-card', SchoologyAnnouncementsCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "custom:schoology-announcements-card",
  name: "Schoology Announcements",
  description: "Display Schoology announcements with details",
  icon: "mdi:bullhorn",
  preview: true,
  documentationURL: "https://github.com/5hells/hellings.cc-hass-sgy",
});
