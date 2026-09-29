# Application Tracker

A local-first job-application tracker built around one rule: record user intent, not page content. The browser extension captures a small event from a page the user already has open; the backend stores the raw event before attempting any interpretation.

## Phase 0: capture pipe

The first milestone is to collect real URL and page-title examples during a week of job hunting. It includes only:

- A user click on text matching `apply`, `easy apply`, or `submit application`.
- A committed navigation to a known ATS domain.
- A FastAPI endpoint that appends each received event to a local JSONL file.
- Durable local queuing in `chrome.storage.local` and retrying delivery until the backend accepts the event.

The extension does not parse jobs, inspect page DOM content, scrape fields, crawl, or open pages. Its capture payload is:

```json
{
  "url": "https://example.com/jobs/123",
  "page_title": "Example role - Example company",
  "referrer": "https://example.com/",
  "trigger_type": "intent_click",
  "tab_id": 42,
  "nav_chain_id": "uuid",
  "captured_at": "2026-09-29T12:00:00Z"
}
```

`page_title` is required. `trigger_type` is one of `intent_click`, `ats_nav`, or `form_submit`; `form_submit` is planned for Phase 3, not Phase 0.

## Later phases

1. **Phase 1:** PostgreSQL raw-event, application, application-event, company, and URL-pattern tables; server-side parsing from database-backed rules; deduplication and REST API; Docker Compose.
2. **Phase 2:** Dashboard with distinct viewed/applied states, status breakdown, funnel, and application timeline.
3. **Phase 3:** Form-submit capture and confirmation-URL detection.
4. **Phase 4:** Manual corrections that improve stored URL-pattern rules.
5. **Phase 5+:** Networking, CV matching, and outreach features.

Raw events are the source of truth and remain append-only. Derived application records must be regenerable from them. Parser rules belong in PostgreSQL rows, not hardcoded regex, so fixes can be deployed without updating the extension.

## Explicitly out of scope for v1

Authentication, deployment, job-description/salary/location scraping, crawling, automated page visits, and LinkedIn networking tracking. Phase 0 uses a local backend and JSONL; PostgreSQL and the dashboard come later.

## Repository status

This repository is initialized for Phase 0. The extension and backend implementation have not been added yet.
