# Job Tracker — Phase 1

Records which job applications you actually start, parses them server-side into
a deduplicated database, and exports the lot.

**Design thesis:** record intent, not content. Parse on the server. Never throw
away a raw capture.

The extension reads only `location.href` and `document.title`, and only at the
moment you click Apply. There is no DOM scraping, no crawling and no background
fetching — which is why it does not break when a job board redesigns.

---

## Architecture

```
┌──────────────────┐   X-API-Key    ┌──────────────┐        ┌────────────┐
│ Chrome extension │ ─────────────► │   FastAPI    │ ─────► │ PostgreSQL │
│  (dumb capture)  │  POST /events  │ (all parsing)│        │            │
└──────────────────┘     /batch     └──────────────┘        └────────────┘
     3 triggers                      url_patterns table
     ├ intent_click  — Apply clicked (catches LinkedIn Easy Apply)
     ├ ats_nav       — landed on a known ATS domain
     └ form_submit   — application actually submitted
```

Parsers live in the **database**, not the extension. Fixing a broken Workday
pattern is an `UPDATE`; shipping a new extension version is a multi-day Chrome
Web Store review.

---

## File structure

```
job-tracker/
├── docker-compose.yml           postgres + api
├── .env.example                 copy to .env
│
├── backend/
│   ├── Dockerfile               multi-stage, non-root, healthcheck
│   ├── entrypoint.sh            runs migrations then uvicorn
│   ├── pyproject.toml           deps via uv
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py               async migration runner
│   │   └── versions/0001_initial.py
│   ├── app/
│   │   ├── main.py              FastAPI app, CORS, lifespan seeding
│   │   ├── config.py            pydantic-settings
│   │   ├── constants.py         statuses, triggers, confidence thresholds
│   │   ├── db.py                async engine + session
│   │   ├── models.py            6 tables (see below)
│   │   ├── schemas.py           request/response models
│   │   ├── deps.py              X-API-Key auth
│   │   ├── seed_patterns.py     23 starter ATS patterns
│   │   ├── parsing/
│   │   │   ├── normalize.py     URL/company/slug normalisation
│   │   │   ├── engine.py        regex engine fed from url_patterns
│   │   │   └── resolver.py      event → application: dedup, chains, status
│   │   └── routers/
│   │       ├── events.py        POST /api/events/batch   (idempotent)
│   │       ├── applications.py  list / get / patch
│   │       ├── stats.py         funnel, rates, over-time
│   │       ├── exports.py       CSV / JSON / JSONL
│   │       └── admin.py         reprocess, patterns CRUD, unmatched
│   └── tests/
│       ├── conftest.py
│       └── test_parsing.py      no database needed
│
└── extension/
    ├── wxt.config.ts            MV3 manifest
    ├── package.json
    ├── lib/
    │   ├── types.ts             payload shape, mirrors the Pydantic model
    │   ├── config.ts            settings + ATS host list
    │   └── queue.ts             storage-backed queue, retry, poison handling
    └── entrypoints/
        ├── background.ts        service worker: nav chains, flush alarm
        ├── content.ts           Apply-click + submit listeners
        └── popup/               connection settings, queue status
```

### Tables

| Table | Role |
|---|---|
| `raw_events` | **Append-only.** Never deleted. The source of truth. |
| `applications` | Derived. Fully regenerable from `raw_events`. |
| `application_events` | Status transition log — powers the funnel. |
| `companies` | Normalised, with slug aliases and trigram matching. |
| `url_patterns` | The parser rules, as data. |
| `manual_overrides` | Your corrections. Never truncated, replayed after reprocess. |

---

## Running it

### 1. Configure

```bash
cd job-tracker
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Paste that value into `API_KEY=` in `.env`. You will need it again in step 3.

### 2. Start the backend

```bash
docker compose up --build
```

On first boot this creates the database, runs the Alembic migration and seeds
the 23 starter URL patterns. Verify:

```bash
curl http://localhost:8000/health/db
open http://localhost:8000/docs      # interactive API reference
```

### 3. Load the extension

```bash
cd extension
npm install
npm run dev          # writes .output/chrome-mv3-dev/ and watches for changes
```

Then in Chrome: `chrome://extensions` → enable **Developer mode** → **Load
unpacked** → select `extension/.output/chrome-mv3-dev`.

Open the extension popup, paste the same `API_KEY` from `.env`, click **Save**,
then **Test**. You should see `Connected. 23 patterns loaded.`

For a one-off build instead of watch mode, use `npm run build`.

### 4. Use it

Go apply for a job. Click Apply on LinkedIn, Greenhouse, wherever. The popup
shows captures within a second or two.

```bash
curl -H "X-API-Key: $API_KEY" localhost:8000/api/applications | jq
curl -H "X-API-Key: $API_KEY" localhost:8000/api/stats/summary | jq
curl -H "X-API-Key: $API_KEY" -O localhost:8000/api/export/applications.csv
```

---

## The improvement loop

This is the part that makes the project work, and the part worth describing in
an interview.

```
   capture  →  see what missed  →  add a pattern  →  reprocess
      ▲                                                  │
      └──────────────────────────────────────────────────┘
```

**1. Find what no pattern caught:**

```bash
curl -H "X-API-Key: $API_KEY" localhost:8000/api/admin/unmatched | jq
```

**2. Try a candidate pattern without storing anything:**

```bash
curl -X POST localhost:8000/api/admin/patterns/test \
  -H "X-API-Key: $API_KEY" -H 'Content-Type: application/json' \
  -d '{"url":"https://jobs.example.com/acme/postings/42","page_title":"Acme - SRE"}'
```

**3. Add it:**

```bash
curl -X POST localhost:8000/api/admin/patterns \
  -H "X-API-Key: $API_KEY" -H 'Content-Type: application/json' \
  -d '{
        "ats": "exampleats",
        "url_regex": "^https?://jobs\\.example\\.com/(?P<company>[^/]+)/postings/(?P<external_id>\\d+)",
        "title_regex": "^(?P<company>.+?) - (?P<role>.+)$",
        "priority": 30
      }'
```

**4. Retroactively fix your entire history:**

```bash
curl -X POST -H "X-API-Key: $API_KEY" localhost:8000/api/admin/reprocess
```

Every application is rebuilt from `raw_events` using the new rules. Your manual
corrections are replayed automatically — `manual_overrides` is never truncated.

Named groups the engine understands: `company`, `role`, `external_id`.

---

## Tests

The parser tests need no database:

```bash
cd backend
uv pip install -r pyproject.toml --extra dev   # or: pip install -e ".[dev]"
pytest
```

When a real URL from your own traffic parses wrongly, add it to
`tests/test_parsing.py` first, then fix the pattern.

---

## Things worth knowing

**Confidence, not certainty.** Capture is high-recall and low-precision by
design: you will catch jobs you browsed and abandoned. That is the right way to
be wrong — deleting a false positive takes one click, while a silently missed
application is invisible forever. `viewed` and `applied` are distinct statuses
and must stay visually distinct in the Phase 2 dashboard, or the funnel lies.

| Signal | Confidence | Resulting status |
|---|---|---|
| `intent_click` | 10 | viewed |
| `ats_nav` | 30 | viewed |
| confirmation URL | 70 | applied |
| `form_submit` | 90 | applied |

**Navigation chains.** Clicking Apply on LinkedIn and landing on Greenhouse is
*one* application. The extension tags both events with a `nav_chain_id`, and the
resolver collapses them — with the real ATS winning over the aggregator.

**LinkedIn Easy Apply never navigates.** It is a modal, so there is no URL
change to detect. `intent_click` is the only signal that catches it. This is why
the extension does not rely on navigation alone.

**`<all_urls>` is intentional, for now.** Company career pages live on arbitrary
domains, so narrowing the content script would miss them. The script stays inert
until a click matches an Apply label. Narrow this to an explicit domain list
before any Chrome Web Store submission — `<all_urls>` triggers heavy review.

**MV3 service workers die after ~30s idle.** Nothing is kept in module-level
variables; durable state is in `chrome.storage.local`, per-tab navigation chains
in `chrome.storage.session`. A `chrome.alarms` tick flushes the queue every
minute as a safety net behind the immediate send.

**The seed patterns are educated guesses.** They are not ground truth, and your
traffic will not look like the list. That is what `/api/admin/unmatched` and
reprocessing are for.

---

## Phase 2 and beyond

- **Phase 2** — Next.js dashboard. Use Route Handlers as a proxy to FastAPI so
  the browser never sees the API key and there is no CORS to configure.
- **Phase 3** — confirmation detection is already wired; tune the patterns
  against real post-submit URLs.
- **Phase 4** — correction UI on top of `manual_overrides` and
  `/api/admin/unmatched`.
- **Phase 5+** — LinkedIn networking tracker, JD parsing, CV matching.
