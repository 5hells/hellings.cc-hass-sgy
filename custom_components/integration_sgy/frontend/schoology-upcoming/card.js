class SchoologyUpcomingEventsCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error('Missing required property: entity');
    this._config = config;
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
  }
  set hass(hass) {
    const entityId = this._config.entity;
    const stateObj = hass.states[entityId];
    const title = this._config.title || 'Upcoming Events';
    if (!stateObj) {
      this.shadowRoot.innerHTML = `<ha-card header="${title}"><div class="empty">Entity not found: ${entityId}</div></ha-card>`;
      return;
    }
    const items = Array.isArray(stateObj.attributes.items) ? stateObj.attributes.items : [];
    const style = `
      <style>
        .container { padding: 16px; }
        .item { border-bottom: 1px solid var(--divider-color); padding: 12px 0; }
        .title { font-weight:600; }
        .meta { color: var(--secondary-text-color); font-size: 12px; }
      </style>
    `;
    const list = items.map(i => `
      <div class="item">
        <div class="title">${i.title || ''}</div>
        <div class="meta">${i.group ? i.group + ' • ' : ''}${i.date || ''}${i.time ? ' • ' + i.time : ''}</div>
      </div>
    `).join('');
    this.shadowRoot.innerHTML = `
      <ha-card header="${title}">
        ${style}
        <div class="container">${items.length ? list : '<div class="empty">No upcoming events</div>'}</div>
      </ha-card>
    `;
  }
  getCardSize() { return 2; }

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
      entity: "sensor.schoology_upcoming_events"
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
