class SchoologyAssignmentsCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error('Missing required property: entity');
    this._config = config;
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
  }
  set hass(hass) {
    const entityId = this._config.entity;
    const stateObj = hass.states[entityId];
    const title = this._config.title || 'Upcoming Assignments';
    if (!stateObj) {
      this.shadowRoot.innerHTML = `<ha-card header="${title}"><div class="empty">Entity not found: ${entityId}</div></ha-card>`;
      return;
    }
    const items = Array.isArray(stateObj.attributes.items) ? stateObj.attributes.items : [];
    const style = `
      <style>
        .container { padding: 16px; max-height: 100px; overflow-y: auto; }
        .item { border-bottom: 1px solid var(--divider-color); padding: 12px 0; }
        .title { font-weight:600; }
        .meta { color: var(--secondary-text-color); font-size: 12px; }
      </style>
    `;
    const list = items.map(i => `
      <div class="item">
        <div class="title">${i.title || ''}</div>
        <div class="meta">${i.group ? i.group + ' • ' : ''}${i.due ? 'Due ' + i.due : ''}</div>
      </div>
    `).join('');
    this.shadowRoot.innerHTML = `
      <ha-card header="${title}">
        ${style}
        <div class="container">${items.length ? list : '<div class="empty">No upcoming assignments</div>'}</div>
      </ha-card>
    `;
  }
  getCardSize() { return (this.shadowRoot.children[0].getBoundingClientRect().height / 50) || 2; }

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
      entity: "sensor.schoology_upcoming_assignments"
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

customElements.define('schoology-assignments-card', SchoologyAssignmentsCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "custom:schoology-assignments-card",
  name: "Schoology Upcoming Assignments",
  description: "Display upcoming Schoology assignments",
  icon: "mdi:clipboard-text",
  preview: true,
  documentationURL: "https://github.com/5hells/hellings.cc-hass-sgy",
});
