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
4. **Slice 6:** Chrome extension capture and offline queue.
5. **Slice 7:** Admin correction loop and reprocessing.
6. **Phase 2:** Dashboard.

## Later phases

1. **Phase 1:** PostgreSQL raw-event, application, application-event, company, and URL-pattern tables; server-side parsing from database-backed rules; deduplication and REST API; Docker Compose.
2. **Phase 2:** Dashboard with distinct viewed/applied states, status breakdown, funnel, and application timeline.
3. **Phase 3:** Form-submit capture and confirmation-URL detection.
4. **Phase 4:** Manual corrections that improve stored URL-pattern rules.
5. **Phase 5+:** Networking, CV matching, and outreach features.

Raw events are the source of truth and remain append-only. Derived application records must be regenerable from them. Parser rules belong in PostgreSQL rows, not hardcoded regex, so fixes can be deployed without updating the extension.

## Explicitly out of scope for v1

The read-side API and exports are implemented. The browser extension, dashboard, and advanced correction/reprocessing endpoints are still deferred to later slices.

## Repository status

Slice 5 is implemented. The backend now exposes authenticated application listing, filtering, pagination, detail retrieval, summary statistics, and CSV/JSON/JSONL exports.
