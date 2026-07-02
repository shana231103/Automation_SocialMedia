# Module: frontend

## Purpose
The `frontend` module is a single-page web application built with Vue 3, Vite, and TailwindCSS v4. It provides user controls to register social media accounts, trigger auto-login workflows, monitor logs in real-time, and audit historical status records.

## Public Interfaces
None (acts as the UI consumer).

## Services
- **API Client**: Service layer using standard `fetch` APIs to query backend REST endpoints and listen to EventSource SSE channels.

## Components
- **`App.vue`**: Root component.
- **Account Management Dashboard**: Form inputs to add, edit, and delete social accounts.
- **Automation Status Panel**: Triggers login and shows active status badges (e.g. green for logged in, yellow for checkpoint, red for dead).
- **Log Feed Streamer**: Console view subscribing to Server-Sent Events to show browser operations line-by-line.

## Internal Dependencies
None.

## External Dependencies
- **Vue 3**: Reactive framework.
- **TailwindCSS v4**: Dynamic styles.
- **Vite**: Packaging tool.

## Callers
Web browsers of end users.

## Related Tests
None.

## What MUST NOT Change
- Endpoints paths mapped to the backend service (`http://127.0.0.1:8000/api/...`).
