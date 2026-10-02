# Explanation — every file, and why it exists

A walkthrough of the Job Tracker codebase: what each file does, which
requirement it serves, and what would break if it were not there.

For the phase roadmap, see [plan.md](plan.md).

---

## 1. What the system does

You apply for jobs across a dozen different sites. Nothing tells you how many
applications you actually sent, which ones converted, or where they went. This
system records that automatically.

A Chrome extension notices when you click **Apply**, and ships a tiny record —
URL, page title, timestamp — to a FastAPI backend you run yourself. The backend
parses that URL into `{company, role, ATS, job id}`, deduplicates it against
everything you have already seen, and stores it in Postgres. You then query,
correct and export it.

---

## 2. The three decisions that explain every file

Almost every design choice in the repo follows from one of these three.

### Decision 1 — Record intent, not content

The extension reads exactly two things: `location.href` and `document.title`.
It never walks the DOM looking for a job description, never crawls, never
fetches in the background.

**Why:** DOM scraping breaks every time a job board changes its markup, which
is roughly monthly. A URL shape is far more stable. It also gives a clean
privacy story — the extension records what you were already looking at, and
nothing else.

**Consequence:** the extension is deliberately dumb. All intelligence is on the
server, which is the next decision.

### Decision 2 — Parse on the server, from rules stored in the database

Parsing lives in the backend, and the parsing *rules* are rows in a
`url_patterns` table, not Python code.

**Why:** fixing a broken Workday parser should be an `UPDATE` statement that
takes effect immediately. If parsers lived in the extension, every fix would
be a Chrome Web Store release and a multi-day review.

**Consequence:** we need [`url_patterns`](backend/app/models.py), a regex
engine fed from the database ([`engine.py`](backend/app/parsing/engine.py)),
pattern CRUD endpoints, and a dry-run test endpoint.

### Decision 3 — Never throw away a raw capture

`raw_events` is append-only. Nothing is ever updated or deleted. Every other
table is derived and can be rebuilt from it.

**Why:** this is what makes it safe to ship imperfect parsers on day one. Your
seed patterns will be wrong. When you fix them a month later, `POST
/api/admin/reprocess` rebuilds your entire history under the new rules. Without
the raw log, a bad parser silently destroys data forever.

**Consequence:** we need the reprocess endpoint, and we need
`manual_overrides` — because a rebuild would otherwise wipe every correction
you had made by hand.

---

## 3. Repository layout

```
job-tracker/
├── docker-compose.yml          postgres + api, one command to start
├── .env.example                config template
├── .gitignore
├── README.md                   how to run it
├── explaination.md             this file
├── plan.md                     phase roadmap
│
├── backend/                    FastAPI + SQLAlchemy + Alembic
└── extension/                  WXT + TypeScript, Manifest V3
```

---

## 4. Root files

| File | What it does | Why it is needed |
|---|---|---|
| [docker-compose.yml](docker-compose.yml) | Defines two services: `db` (Postgres 17-alpine) and `api` (built from `backend/`). Mounts a named volume `pgdata`, exposes 5432 and 8000. | One command — `docker compose up --build` — gives a working stack. Removes "install Postgres, create a user, create a database" from the setup path entirely. |
| [.env.example](.env.example) | Template for `POSTGRES_*`, `API_PORT`, `LOG_LEVEL`, `API_KEY`. | The API key is a shared secret between extension and backend. It must not be committed, so the real `.env` is gitignored and this file documents its shape. |
| [.gitignore](.gitignore) | Ignores `.env`, `__pycache__`, `node_modules`, `.output`, `.wxt`, `*.jsonl`. | `.env` holds your API key. `*.jsonl` is ignored because the raw-events export writes there — that file contains your full browsing history for job sites. |
| [README.md](README.md) | Setup, architecture diagram, the improvement loop, operational caveats. | The entry point for anyone (including future you) opening the repo. |

**Note on `db.healthcheck`:** the `api` service declares
`depends_on: db: condition: service_healthy`. Without this, the API starts
before Postgres accepts connections, Alembic fails, and the container
crash-loops on first boot. The healthcheck makes first-run deterministic.

---

## 5. Backend — infrastructure

### [backend/Dockerfile](backend/Dockerfile)

Multi-stage-ready image on `python:3.12-slim`. Copies `uv` from the official
image for fast installs, installs dependencies in their own layer *before*
copying source, creates a non-root `appuser`, and declares a `HEALTHCHECK` that
hits `/health`.

**Why each part matters:**
- Dependency layer before source → editing a Python file does not reinvalidate
  the dependency install. Rebuilds go from ~60s to ~3s.
- Non-root user → standard container hardening; a compromised process cannot
  write to system paths.
- `HEALTHCHECK` → Docker and Compose can tell "container running" apart from
  "application actually serving".

### [backend/entrypoint.sh](backend/entrypoint.sh)

Runs `alembic upgrade head` (unless `RUN_MIGRATIONS_ON_START=false`), then
`exec`s uvicorn.

**Why:** migrations must run after Postgres is reachable but before the app
serves traffic. Putting them in the entrypoint rather than the Dockerfile means
they run at container *start*, not at image *build*, which is correct — the
database does not exist at build time. `exec` matters so uvicorn becomes PID 1
and receives `SIGTERM` directly for clean shutdown.

### [backend/pyproject.toml](backend/pyproject.toml)

Dependencies, plus `ruff` and `mypy` config and a `dev` extra for pytest.

Runtime deps and why: `fastapi` + `uvicorn[standard]` (the API), `sqlalchemy
[asyncio]` + `asyncpg` (async DB access end-to-end — the API is I/O-bound, so
sync drivers would block the event loop), `alembic` (migrations), `pydantic` +
`pydantic-settings` (validation and config).

`[tool.pytest.ini_options] asyncio_mode = "auto"` removes the need to decorate
every async test.

### [backend/alembic.ini](backend/alembic.ini) and [backend/alembic/env.py](backend/alembic/env.py)

Migration configuration. `env.py` is non-standard in two ways that matter:

1. It overrides `sqlalchemy.url` from `app.config.settings` rather than reading
   the ini file, so there is exactly one source of truth for the database URL.
2. It runs migrations through `async_engine_from_config` with `NullPool`,
   because the project uses the async `asyncpg` driver throughout.

`compare_type=True` makes autogenerated migrations detect column type changes,
which Alembic misses by default.

### [backend/alembic/versions/0001_initial.py](backend/alembic/versions/0001_initial.py)

Creates all six tables, every index, and every CHECK constraint. First
statement is `CREATE EXTENSION IF NOT EXISTS pg_trgm`.

**Why `pg_trgm` is in the migration and not a manual setup step:** the
`companies` table has a GIN trigram index for fuzzy name matching ("Discord"
vs "Discord Inc."). Creating that index fails without the extension, so the
extension has to be created first, in the same transaction, automatically.

---

## 6. Backend — application core

### [backend/app/config.py](backend/app/config.py)

`pydantic-settings` class reading `DATABASE_URL`, `API_KEY`, `LOG_LEVEL`,
`SEED_PATTERNS_ON_START`, `EXTRA_CORS_ORIGINS`. Wrapped in `@lru_cache`.

**Why:** typed configuration validated at startup, rather than `os.environ`
lookups scattered through the codebase that fail at 3am on the one code path
nobody tested. `extra="ignore"` means unrelated environment variables (like
`RUN_MIGRATIONS_ON_START`, which the shell script reads) do not crash startup.

### [backend/app/constants.py](backend/app/constants.py)

The shared vocabulary: `Status`, `TriggerType`, `PatternKind`, `StatusSource`
as `StrEnum`s, plus `FUNNEL_ORDER`, `TERMINAL_STATUSES` and the confidence
numbers.

**Why `StrEnum` plus CHECK constraints instead of Postgres native enums:**
altering a native enum in a migration is genuinely painful — you cannot drop a
value, and adding one cannot run inside a transaction block in older versions.
A `VARCHAR` with a CHECK constraint gives the same integrity guarantee and
changing it is a one-line migration. The Python enum supplies type safety in
the app layer, so you get both.

**Why confidence is a number, not a boolean:**

| Signal | Confidence | Resulting status |
|---|---|---|
| `intent_click` | 10 | viewed |
| `ats_nav` | 30 | viewed |
| confirmation URL | 70 | applied |
| `form_submit` | 90 | applied |

`APPLIED_CONFIDENCE_THRESHOLD = 70` is the line between "you looked at this"
and "you applied to this". Keeping it a tunable integer means you can move the
threshold later without touching the resolver logic.

### [backend/app/db.py](backend/app/db.py)

Async engine, `async_sessionmaker`, and a `get_session` dependency.

`pool_pre_ping=True` matters in Docker: Postgres may restart independently of
the API, leaving dead connections in the pool. Pre-ping validates a connection
before handing it out, turning a hard crash into a transparent reconnect.

`expire_on_commit=False` means ORM objects stay usable after `commit()`, which
is what lets the routers return a model they just saved.

### [backend/app/deps.py](backend/app/deps.py)

`X-API-Key` header check using `secrets.compare_digest`.

**Why this and not OAuth:** single user, single client, self-hosted. A shared
secret is the proportionate answer. `compare_digest` rather than `==` because
`==` short-circuits on the first differing byte and leaks key content through
response timing.

### [backend/app/models.py](backend/app/models.py)

The six SQLAlchemy tables. Full detail in section 9.

### [backend/app/schemas.py](backend/app/schemas.py)

Pydantic request/response models — `EventIn`, `ApplicationOut`,
`StatsSummary`, `PatternIn`, and so on.

**Why a separate layer from the ORM models:** the wire format and the storage
format should be able to change independently. It also means you cannot
accidentally leak an internal column by returning an ORM object directly.
`EventIn` enforces `max_length` on every string and rejects non-`http(s)` URLs —
the extension is the only client today, but the endpoint is still a public
surface that accepts arbitrary input.

### [backend/app/main.py](backend/app/main.py)

Builds the FastAPI app: logging, CORS, router registration, `/health`,
`/health/db`, and a `lifespan` hook that seeds `url_patterns` if the table is
empty.

**Why seeding is conditional on `count == 0`:** restarting the container must
not re-insert or resurrect patterns you deliberately deleted. The seed is a
first-boot convenience, not a sync.

**Why the CORS config looks odd:** `allow_origin_regex=r"^(chrome|moz)-
extension://.*$"` — the extension's service worker calls the API from a
`chrome-extension://<id>` origin, and the id changes between developer loads,
so it cannot be listed explicitly. The Next.js dashboard (Phase 2) will proxy
server-side and therefore never appear here as a browser origin at all.

---

## 7. Backend — the parsing layer

This is the heart of the project.

### [backend/app/parsing/normalize.py](backend/app/parsing/normalize.py)

Pure string functions, no database or framework imports, so they are trivially
unit-testable.

| Function | Job | Why it is needed |
|---|---|---|
| `deslugify` | `Software-Engineer-II` → `Software Engineer II` | URL slugs are the only role source on several ATSs. Only lowercase words are capitalised, so `iOS`, `ML` and `II` survive. |
| `clean_title_fragment` | Trims noise from `<title>` captures | Title tags carry stray separators (`-`, `|`, `·`) that would end up inside company names. |
| `normalize_company_key` | `Discord, Inc.` → `discord` | The dedup key for companies. Strips punctuation and legal suffixes. The suffix list is deliberately conservative — stripping `Labs` or `Group` would over-merge genuinely distinct companies. |
| `normalize_url` | Canonical URL form | The fallback dedup key. Lowercases host, drops `www.`, forces https, strips the fragment, and removes every query parameter not in `_MEANINGFUL_QUERY_KEYS`. |

`normalize_url` is doing the heavy lifting for correctness. Without the query
parameter allowlist, the same job reached via two different `utm_source` values
would become two applications. With a *blocklist* instead of an allowlist you
would have to enumerate every tracking parameter in existence; the allowlist
only needs to know the handful of parameters that genuinely identify a posting
(`currentJobId`, `gh_jid`, `jk`, …).

### [backend/app/parsing/engine.py](backend/app/parsing/engine.py)

Compiles `url_patterns` rows into regexes and matches URLs against them.

Key behaviours and the reasoning:

- **Two pattern kinds, matched independently.** A `job_posting` pattern
  establishes identity (which company, which role, which id). A `confirmation`
  pattern establishes only that you submitted. A confirmation URL has no job id
  in it, so conflating the two would break dedup.
- **Priority ordering, lowest first.** Specific patterns must beat generic
  fallbacks. Real ATSs sit at priority 10–23, aggregators at 100+.
- **Title beats URL for company and role.** A `<title>` gives `Discord`; the
  URL slug gives `discordinc`. The `sources` dict records which won, which is
  what you read when debugging a bad parse.
- **A bad regex is logged and skipped, never fatal.** Patterns are
  user-editable data. One malformed regex must not take down parsing for every
  other site.
- **Process-local compiled cache**, dropped explicitly by `invalidate_engine()`
  on every pattern write. Patterns change a few times a week; recompiling
  twenty regexes on every captured event would be pure waste.

### [backend/app/parsing/resolver.py](backend/app/parsing/resolver.py)

Turns a `RawEvent` into — or folds it into — an `Application`. Every rule about
identity, deduplication and status progression lives here. It never commits, so
it is safe to call in a loop during a full reprocess.

The four problems it solves:

**1. Identity.** `_dedup_key()` prefers `"{ats}:{external_id}"` and falls back
to the normalised URL. The ATS key survives tracking parameters, locale
prefixes and you revisiting the posting from a different link.

**2. Navigation chains.** You click Apply on LinkedIn and land on Greenhouse.
That is *one* application, but it produces two events with different URLs and
different dedup keys. The extension tags both with a `nav_chain_id`; the
resolver uses `_authority()` to rank them — unrecognised `0`, aggregator `1`,
real ATS `2` — and upgrades the existing row in place when the higher-authority
leg arrives. Greenhouse wins, and you get one row instead of two.

**3. Company resolution.** `_get_or_create_company()` looks up by ATS slug
*before* by normalised name, because the two disagree: Greenhouse's
`discordinc` normalises to `discordinc`, while the page title gives `Discord` →
`discord`. Once a slug is associated with a company, every later sighting
resolves to the same row regardless of arrival order. A better-formatted name
may replace a slug-derived placeholder, but `normalized_key` is never rewritten
— it is the identity, and changing it risks colliding with another row's unique
key.

**4. Status progression.** `_is_forward()` enforces a one-way ratchet:
statuses only advance through `FUNNEL_ORDER`; terminal states (`rejected`,
`withdrawn`) can always be set but never automatically undone; and a row whose
`status_source` is `manual` is never touched by the parser again.

`_apply_manual_override()` runs **last**, after every automatic rule, which is
what makes a human decision always win.

`_update_existing()` fills gaps only — a later, worse parse must never
overwrite a good earlier one.

---

## 8. Backend — the API routers

### [backend/app/routers/events.py](backend/app/routers/events.py) — ingestion

One endpoint: `POST /api/events/batch`.

**Idempotency** is the whole story here. The extension retries from a local
queue, so the same event *will* arrive twice. The endpoint checks
`client_event_id` against both the database and the current batch, so
duplicates are counted and discarded rather than creating phantom
applications.

Events are processed **oldest first** (`sorted(..., key=captured_at)`) so that
navigation chains resolve in the order they actually happened — the LinkedIn
leg must be seen before the Greenhouse leg for the upgrade logic to fire.

### [backend/app/routers/applications.py](backend/app/routers/applications.py) — read and correct

- `GET /api/applications` — filter by status, ATS, company, free-text `q`, date
  range; sort and paginate. The sort column comes from a `SORTABLE` allowlist
  dict rather than string interpolation, so the parameter cannot be used for
  injection.
- `GET /api/applications/{id}`
- `PATCH /api/applications/{id}` — **writes to `manual_overrides` as well as
  the application row.** This is the critical detail: without the override
  write, the next reprocess would silently erase your correction. It also
  records an `ApplicationEvent` for manual status changes, so the funnel
  includes human-entered transitions.

### [backend/app/routers/stats.py](backend/app/routers/stats.py) — aggregates

`GET /api/stats/summary` returns status breakdown, funnel with per-stage
conversion, applications over time, response rate and interview rate.

**Why the funnel reads `application_events` rather than `applications.status`:**
a stage should count an application if it *ever reached* that stage. Someone who
interviewed and was then rejected still counts at the interview stage. Reading
current status would make every rejection vanish from the funnel and the
conversion rates would be nonsense.

`unattributed` counts applications with no ATS — surfacing parser gaps directly
in the stats payload.

### [backend/app/routers/exports.py](backend/app/routers/exports.py) — get your data out

`applications.csv`, `applications.json`, `companies.csv`, and
`raw-events.jsonl`.

The JSONL endpoint **streams from its own session** rather than a
dependency-injected one. FastAPI tears down a `Depends` session when the
handler returns, which is *before* a `StreamingResponse` finishes consuming its
generator — the stream would die partway through. This is the kind of bug that
only appears once the table is large enough for the response to not fit in one
buffer.

CSV exists because the realistic consumer of this data is a spreadsheet.

### [backend/app/routers/admin.py](backend/app/routers/admin.py) — the improvement loop

| Endpoint | Purpose |
|---|---|
| `POST /reprocess` | Truncate derived tables, replay every raw event under current rules. Chunked at 200 events. `manual_overrides` is untouched and replayed. |
| `GET /patterns` | List rules |
| `POST /patterns` | Add a rule — regex validated before insert |
| `PATCH /patterns/{id}` | Edit a rule |
| `DELETE /patterns/{id}` | Remove a rule |
| `POST /patterns/test` | **Dry run.** Parse a URL and show what would be extracted, storing nothing. |
| `POST /patterns/seed` | Insert starter patterns |
| `GET /unmatched` | URLs no pattern caught, ranked by hit count — your work queue |

`/patterns/test` and `/unmatched` together are what make the loop usable: see
what missed, try a fix without consequences, commit it, reprocess.

Every mutating pattern endpoint calls `invalidate_engine()` so the next request
recompiles.

### [backend/app/seed_patterns.py](backend/app/seed_patterns.py)

23 starter patterns: 14 real ATSs, 5 aggregators, 4 confirmation patterns.

**These are educated guesses, and the file says so in its own docstring.** ATS
URL shapes drift, and your traffic will not look like this list. The seeds
exist so the system does something useful on day one, not because they are
correct. `/api/admin/unmatched` is the mechanism for fixing them.

### [backend/tests/](backend/tests/)

`conftest.py` defines a `FakePatternRow` dataclass that duck-types
`models.UrlPattern`, so the engine can be constructed from `SEED_PATTERNS`
**with no database at all**.

**Why that matters:** you can run `pytest` and iterate on a regex in under a
second, with no Docker, no Postgres, no fixtures. The parsing logic is the part
that changes most often, so it is the part that most needs a fast feedback
loop.

`test_parsing.py` covers normalisation, each major ATS, confirmation detection,
and the dedup-key invariants — including the important negative cases: tracking
parameters must *not* split one application, and two different jobs must *not*
collapse into one.

---

## 9. The data model

| Table | Role | Lifecycle |
|---|---|---|
| `raw_events` | Append-only capture log | **Never** updated or deleted |
| `applications` | One row per job application | Fully derived; truncated and rebuilt on reprocess |
| `application_events` | Status transition log | Derived; powers the funnel |
| `companies` | Normalised companies with slug aliases | Derived |
| `url_patterns` | Parser rules as data | User-managed |
| `manual_overrides` | Your corrections | **Never** truncated; replayed after reprocess |

### Why `raw_events` has a `payload` JSONB column

An escape hatch. The extension can start sending a new field immediately
without a migration; promote it to a real column later if it proves useful.
Without it, every experiment on the client requires a schema change first.

### Why `applications.dedup_key` is `UNIQUE`

It is the natural key that collapses repeat visits into one row. Making it a
database constraint rather than an application-level check means a race between
two concurrent ingests cannot produce duplicates.

### Why `manual_overrides` is keyed by `dedup_key`, not `application_id`

Reprocess deletes every `applications` row and creates new ones with new UUIDs.
A foreign key to `application_id` would dangle. `dedup_key` is stable across
rebuilds, which is exactly the property an override needs.

### Why `application_events` exists at all

Current status is a single value; it cannot tell you that an application
reached `interview` before becoming `rejected`. Without the transition log the
funnel chart and every conversion rate would be wrong.

---

## 10. The extension

Manifest V3, built with [WXT](https://wxt.dev). WXT handles the manifest
generation, TypeScript build and hot reload so the repo contains logic rather
than build plumbing.

### [extension/lib/types.ts](extension/lib/types.ts)

Shared types. `CapturedEvent` mirrors the backend's `EventIn` field for field —
if the two drift, ingestion fails with a 422.

### [extension/lib/config.ts](extension/lib/config.ts)

Defaults, storage keys, tuning constants, and `ATS_HOST_PATTERNS` — 18 regexes
identifying real applicant tracking systems.

`CHAIN_TTL_MS = 30 min` is the window in which a navigation is still considered
part of the preceding Apply click. Too short and the LinkedIn → Greenhouse hop
is missed; too long and unrelated browsing gets stitched into the same chain.

### [extension/lib/queue.ts](extension/lib/queue.ts)

A storage-backed queue with retry and poison-message handling.

**Why a queue at all:** your backend is on `localhost`. It will be down — you
rebooted, Docker is not running, you are on a plane. Captures must survive
that, or the tool quietly loses the data it exists to collect.

Three details that matter:

- **`withLock`** serialises read-modify-write cycles. `chrome.storage` has no
  atomic update, so two concurrent enqueues can clobber each other. The lock
  spans one service-worker lifetime, which is sufficient for human-speed
  clicks.
- **422 handling drops the batch.** A malformed event that the backend will
  never accept would otherwise wedge the queue behind a poison message forever.
  It is counted in `totalDropped` and surfaced in the popup rather than hidden.
- **Removal is by `client_event_id`, not by slice.** Events may have been
  enqueued while the request was in flight; slicing by index would delete them
  unsent.

### [extension/entrypoints/background.ts](extension/entrypoints/background.ts)

The service worker. Owns navigation chains, the `ats_nav` trigger, the flush
alarm, and all popup messaging.

**The MV3 constraint drives the whole design:** Chrome tears the worker down
after ~30 seconds idle. Nothing may live in a module-level variable across
events. Durable state goes in `chrome.storage.local`; per-tab chains go in
`chrome.storage.session`, which clears when the browser closes — exactly the
lifetime a navigation chain should have.

A `chrome.alarms` tick flushes every minute as a safety net behind the
immediate send. The `lastUrlKey` check suppresses duplicate `ats_nav` captures
from reloads and in-page history pushes.

### [extension/entrypoints/content.ts](extension/entrypoints/content.ts)

Detects Apply clicks and form submits.

- `APPLY_LABEL_RE` matches a dozen button phrasings (`Apply`, `Easy Apply`,
  `Submit application`, `I'm interested`, …).
- `composedPath()` is used rather than `event.target` because several ATS
  widgets render inside shadow DOM, where `target` reports the host element.
- The listener runs in the **capture phase**, so it fires before the site's own
  handler can call `stopPropagation()` or tear the button out of the DOM.
- `findActionable` walks up to 5 ancestors, because the click usually lands on
  a `<span>` inside the real `<button>`.
- `allFrames: true` — Greenhouse and Lever are routinely embedded in an iframe
  on a company's own careers page.
- The `submit` listener is **gated on `isAtsHost()`**, so we do not log every
  search box on the internet.

### [extension/entrypoints/popup/](extension/entrypoints/popup/)

Connection settings, queue depth, sent/dropped counters, last error, and a live
list of recent captures. `index.html` carries its own scoped CSS with a dark
mode via `prefers-color-scheme`; `main.ts` renders via DOM methods rather than
`innerHTML`.

**Why the popup is more than a settings form:** the failure mode of a capture
tool is silence. If the backend is unreachable, nothing visibly breaks — you
just lose data. The health dot and queue counters make failure *visible*,
which is the difference between a tool you can trust and one you cannot.

---

## 11. End to end: one Apply click

1. You click **Apply** on a LinkedIn job posting.
2. `content.ts` matches the label, reads `location.href` and `document.title`,
   sends a `capture` message to the service worker.
3. `background.ts` starts a new `nav_chain_id` (an `intent_click` always begins
   a chain), builds a `CapturedEvent`, enqueues it, and triggers a flush.
4. `queue.ts` POSTs the batch to `/api/events/batch` with the API key.
5. `events.py` checks `client_event_id` for idempotency, writes a `RawEvent`,
   and calls `resolve_event`.
6. `engine.py` matches the LinkedIn pattern → `{ats: linkedin, external_id:
   3912345678}`, with the title giving company and role.
7. `resolver.py` builds `dedup_key = "linkedin:3912345678"`, finds no existing
   row, creates the `Application` at `viewed` (confidence 10), creates the
   `Company`, and logs an `ApplicationEvent`.
8. LinkedIn redirects you to Greenhouse. `webNavigation.onCommitted` fires,
   `isAtsHost` matches, and an `ats_nav` event is captured **with the same
   `nav_chain_id`**.
9. `resolver.py` finds no row for `greenhouse:7891234`, but finds the chained
   LinkedIn row. ATS authority (2) beats aggregator authority (1), so it
   **upgrades that row in place** — new dedup key, new ATS, new URL. Still one
   application.
10. You submit the form. `form_submit` fires at confidence 90, crossing the
    threshold, so the status advances to `applied` and `applied_at` is set.

One application, three events, correct attribution.

---

## 12. What is deliberately not built

| Thing | Status | Why |
|---|---|---|
| Dashboard UI | Not started | Phase 2. The API is complete and usable via `curl` and `/docs`. |
| GitHub Actions CI | **Missing** | Listed in Phase 1 and not yet built. The real gap in the current state. |
| Nightly re-resolution job | Not built | Phase 3 tail. Needs APScheduler; pure addition, no schema change. |
| Correction UI | Not built | Phase 4. The backend (`manual_overrides`, `PATCH`, `/unmatched`) is finished. |
| Multi-user auth | Not planned | Single-user self-hosted tool. A shared secret is proportionate. |
| JD text capture | Not planned for v1 | Contradicts "record intent, not content" and makes the privacy story much harder. |

One known inconsistency: `docker-compose.yml` mounts `./backend:/app` with a
comment about live reload, but `entrypoint.sh` only passes `--reload` when
`UVICORN_RELOAD` is set, and Compose does not set it. Code changes currently
need a container restart. Set `UVICORN_RELOAD=1` in the `api` environment to
get the documented behaviour.

See [plan.md](plan.md) for the full phase breakdown.
