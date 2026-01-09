# Schoology for Home Assistant

A Home Assistant integration for Schoology (LMS) that provides sensors to monitor various aspects of your Schoology account, such as upcoming assignments, grades, and course information.

## Setup

- Add this as a custom repository via HACS.
- Install the "Schoology for Home Assistant" integration from HACS.
- Configure the integration through the Home Assistant UI, providing your Schoology credentials and the fetch interval.
- Restart Home Assistant to apply the changes.
- Configure resources via the UI, or add the following to your `configuration.yaml`:

```yaml
lovelace:
  mode: yaml
  resources:
    - url: /frontend/integration_sgy/schoology-announcements/card.js
      type: module
    - url: /frontend/integration_sgy/schoology-assignments/card.js
      type: module
    - url: /frontend/integration_sgy/schoology-overdue/card.js
      type: module
    - url: /frontend/integration_sgy/schoology-upcoming/card.js
      type: module
```