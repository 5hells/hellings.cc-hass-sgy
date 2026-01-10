// Removes broken, garbage-looking formatting that my teachers so very love.
function removeObsceneFormatting(input) {
  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = input;
  const obsceneTags = ['script', 'style', 'iframe', 'object', 'embed', 'link', 'meta'];
  obsceneTags.forEach(tag => {
    const elements = tempDiv.getElementsByTagName(tag);
    while (elements[0]) {
      elements[0].parentNode.removeChild(elements[0]);
    }
  });
  const allElements = tempDiv.getElementsByTagName('*');
  for (let i = 0; i < allElements.length; i++) {
    allElements[i].style.color = '';
    allElements[i].style.backgroundColor = '';
  }
  return tempDiv.innerHTML;
}

class SchoologyAnnouncementsCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) {
      throw new Error('Missing required property: entity');
    }
    if (!config.entity.startsWith('sensor.') || !config.entity.includes('schoology') || !config.entity.includes('announcements')) {
      throw new Error('Entity must be a Schoology announcements sensor');
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
    const icon = this._config.icon || 'mdi:bullhorn';

    if (!stateObj) {
      this.shadowRoot.innerHTML = `<ha-card><div class="card-header"><ha-icon icon="${icon}"></ha-icon> ${title}</div><div class="empty">Entity not found: ${entityId}</div></ha-card>`;
      return;
    }

    const items = Array.isArray(stateObj.attributes.items) ? stateObj.attributes.items : [];

    const style = `
      <style>
        .card-header { display: flex; align-items: center; gap: 8px; font-weight: 500; padding: 16px 16px 0 16px; }
        .container { padding: 16px; min-height: 200px; max-height: 200px; overflow-y: auto; }
        .item { border-bottom: 1px solid var(--divider-color); padding: 12px 0; }
        .header { display:flex; align-items:center; gap:10px; }
        .pfp { width:32px; height:32px; border-radius:50%; object-fit:cover; }
        .pfp-comment-inline { width:24px; height:24px; border-radius:50%; object-fit:cover; vertical-align:middle; margin-right:6px; }
        .title { font-weight:600; }
        .meta { color: var(--secondary-text-color); font-size: 12px; }
        .comments { margin-top: 8px; padding-left: 8px; border-left: 2px solid var(--divider-color); }
        .comment { margin: 6px 0; }
        a { color: inherit; text-decoration: none; }
      </style>
    `;

    const list = items.map((i) => {
      const pfp = i.profile_picture ? `<img class="pfp" src="${i.profile_picture}" alt="pfp" />` : '';
      const group = i.group ? `<span>${i.group}</span>` : '';
      const likes = typeof i.likes === 'number' ? `<span> • <ha-icon icon="mdi:heart"></ha-icon> ${i.likes}</span>` : '';
      const created = i.created ? ` <div class="meta">${i.created}</div>` : '';
      const comments = Array.isArray(i.comments) && i.comments.length
        ? `<div class="comments">${i.comments.map(c => `<div class="comment">
            ${c.profile_picture ? `<img class="pfp-comment-inline" src="${c.profile_picture}" alt="pfp" />` : ''}
            <strong>${c.author}</strong>: ${c.content}${typeof c.likes === 'number' ? ` • <ha-icon icon="mdi:heart"></ha-icon> ${c.likes}` : ''}</div>`).join('')}
          </div>`
        : '';
      return `
        <div class="item">
          <div class="header">${pfp}<div class="title">${i.title || ''}</div></div>
          <div>${removeObsceneFormatting(i.content || '')}</div>
          <div class="meta">${group}${likes}</div>
          ${created}
          ${comments}
        </div>
      `;
    }).join('');

    this.shadowRoot.innerHTML = `
      <ha-card>
        <div class="card-header"><ha-icon icon="${icon}"></ha-icon> ${title}</div>
        ${style}
        <div class="container">
          ${items.length ? list : '<div class="empty">No announcements</div>'}
        </div>
      </ha-card>
    `;
  }
  getCardSize() { return 250 / 50; }

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
      entity: "sensor.schoology_announcements",
      icon: "mdi:bullhorn"
    };
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "entity", required: true, selector: { entity: { domain: "sensor" } } },
        { name: "title", selector: { text: {} } },
        { name: "icon", selector: { icon: {} } },
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
  documentationURL: "https://github.com/5hells/hellings.cc-hass-sgy",
});
