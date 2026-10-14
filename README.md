# Application Tracker

A local-first job-application tracker built around one rule: record user intent, not page content. The browser extension captures a small event from a page the user already has open; the backend stores the raw event before attempting any interpretation.

## Completed slices

### Slice 1: repository foundation

- FastAPI application with `/health` endpoint.
- Docker Compose setup for API and PostgreSQL.
- Environment template and backend package configuration.

### Slice 2: persistence foundation

- Async SQLAlchemy engine and database sessions.
- Alembic migration workflow.
- Initial schema for raw events, applications, application history, companies, parser rules, and manual overrides.
- `/health/db` database connectivity endpoint.
- Automatic migrations when the API container starts.

Detailed local implementation notes are kept in `readme-depth.md`, which is intentionally ignored by Git.

## Upcoming slices

1. **Slice 3:** Pure URL normalization and parser engine with unit tests. **Implemented.**
2. **Slice 4:** Event ingestion API with API-key authentication and idempotency. **Implemented.**
3. **Slice 5:** Application queries, statistics, and exports. **Implemented.**
4. **Slice 6:** Chrome extension capture and offline queue. **Implemented.**
5. **Slice 7:** Admin correction loop and reprocessing.
6. **Phase 2:** Dashboard. **Implemented; local API connection required.**

## Later phases

1. **Phase 1:** PostgreSQL raw-event, application, application-event, company, and URL-pattern tables; server-side parsing from database-backed rules; deduplication and REST API; Docker Compose.
2. **Phase 2:** Dashboard with distinct viewed/applied states, status breakdown, funnel, and application timeline.
3. **Phase 3:** Form-submit capture and confirmation-URL detection.
4. **Phase 4:** Manual corrections that improve stored URL-pattern rules.
5. **Phase 5+:** Networking, CV matching, and outreach features.

Raw events are the source of truth and remain append-only. Derived application records must be regenerable from them. Parser rules belong in PostgreSQL rows, not hardcoded regex, so fixes can be deployed without updating the extension.

## Explicitly out of scope for v1

The browser extension and Phase 2 dashboard are implemented locally. Admin corrections, pattern editing, and reprocessing UI remain deferred to later slices.

## Run the dashboard

Start the backend with Docker Compose after copying `.env.example` to `.env` and setting a local `API_KEY`. If port 8000 is already occupied, set `API_PORT=8001` in the root `.env` before starting it.

In another terminal, configure and start the dashboard:

```powershell
cd dashboard
Copy-Item .env.example .env.local
# Set API_BASE_URL to the backend's host port and API_KEY to the same local key.
npm ci
npm run dev -- --port 3002
```

Open `http://localhost:3002`. The API key stays in the Next.js server environment; do not prefix it with `NEXT_PUBLIC_`. The proxy checks the backend health response before forwarding the key.

## Repository status

Slice 6 and the Phase 2 dashboard are implemented. The repository includes a WXT-based Manifest V3 extension with Apply-click capture, ATS navigation and submit capture, a storage-backed queue, retry/flush behavior, and a popup for API settings and queue status. The dashboard provides application analytics and a filterable application table; verify it with a configured local backend.
