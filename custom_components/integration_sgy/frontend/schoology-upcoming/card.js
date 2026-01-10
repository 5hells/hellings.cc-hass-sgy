class SchoologyUpcomingEventsCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error('Missing required property: entity');
    if (!config.entity.startsWith('sensor.') || !config.entity.includes('schoology') || !config.entity.includes('upcoming_events')) {
      throw new Error('Entity must be a Schoology upcoming events sensor');
    }
    this._config = config;
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
  }
  set hass(hass) {
    const entityId = this._config.entity;
    const stateObj = hass.states[entityId];
    const title = this._config.title || 'Upcoming Events';
    const icon = this._config.icon || 'mdi:calendar';
    if (!stateObj) {
      this.shadowRoot.innerHTML = `<ha-card><div class="card-header"><ha-icon icon="${icon}"></ha-icon> ${title}</div><div class="empty">Entity not found: ${entityId}</div></ha-card>`;
      return;
    }
    const items = Array.isArray(stateObj.attributes.items) ? stateObj.attributes.items : [];
    const style = `
      <style>
        .card-header { display: flex; align-items: center; gap: 8px; font-weight: 500; padding: 16px 16px 0 16px; }
        .container { padding: 16px; height: 100px; max-height: 100px; overflow-y: auto; }
        .item { border-bottom: 1px solid var(--divider-color); padding: 12px 0; }
        .title { font-weight:600; }
        .meta { color: var(--secondary-text-color); font-size: 12px; }
        a { color: inherit; text-decoration: none; }
      </style>
    `;
    const list = items.map(i => `
      <div class="item">
        <div class="title"><a href="${i.link || ''}" target="_blank">${i.title || ''}</a></div>
        <div class="meta">${i.group ? i.group + ' • ' : ''}${i.date || ''}${i.time ? ' • ' + i.time : ''}</div>
      </div>
    `).join('');
    this.shadowRoot.innerHTML = `
      <ha-card>
        <div class="card-header"><ha-icon icon="${icon}"></ha-icon> ${title}</div>
        ${style}
        <div class="container">${items.length ? list : '<div class="empty">No upcoming events</div>'}</div>
      </ha-card>
    `;
  }
  getCardSize() { return 100 / 50; }

  getGridOptions() {
    return {
      rows: 3,
      columns: 6,
      min_rows: 2,
      max_rows: 6,
    };
  }

  static getStubConfig() {
    return {
      entity: "sensor.schoology_upcoming_events",
      icon: "mdi:calendar"
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

customElements.define('schoology-upcoming-card', SchoologyUpcomingEventsCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "custom:schoology-upcoming-card",
  name: "Schoology Upcoming Events",
  description: "Display upcoming Schoology events",
  icon: "mdi:calendar",
  preview: true,
  documentationURL: "https://github.com/5hells/hellings.cc-hass-sgy",
});
