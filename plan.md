# Plan — Phases 0 to 4

The roadmap, what each phase earns you, and exactly where the project stands.

For the file-by-file walkthrough, see [explaination.md](explaination.md).

---

## Status at a glance

| Phase | Name | State |
|---|---|---|
| **0** | Capture pipe | ✅ Complete (subsumed into Phase 1) |
| **1** | Parse, dedup, store, export | ✅ Complete **except CI** |
| **2** | Dashboard | ⬜ Not started |
| **3** | Submission detection | 🟡 Detection built; nightly job not built |
| **4** | Correction loop | 🟡 Backend built; UI not built |
| 5+ | Networking, JD parsing, CV matching | ⬜ Not started |

**The honest summary:** what exists is Phase 1, plus the *backend halves* of
Phases 3 and 4, minus CI.

---

## Why phases, and the rule used to split them

Phases are not arbitrary milestones. Each one is a point where the system is
**independently useful** — you could stop there and still have something that
works.

When Phases 3 and 4 were pulled partly forward, the rule applied was:

> **Build the data layer of a later phase now if deferring it would cost a
> migration later. Defer the UI, which costs nothing to add later.**

Concretely:

- `confidence`, `status_source` and the confirmation patterns are three columns
  and four rows. Adding them after you have six months of live data means a
  migration *plus* a full reprocess.
- `manual_overrides` is not optional once `/reprocess` exists. Without it, the
  first reprocess silently destroys every correction you ever made. It is
  load-bearing from the moment the endpoint ships, not from the moment the UI
  ships.

Everything genuinely deferred — the dashboard, the correction UI, the nightly
job — is a pure addition that touches no existing schema.

---

## Phase 0 — Capture pipe

**Goal:** prove you can reliably notice "the user is applying for a job" and
get that fact off the browser and into durable storage.

**Why it exists as a phase:** this is the only part of the system that can fail
*invisibly*. If parsing is wrong, you can see that it is wrong and fix it. If
capture never fires, there is nothing to look at — you just slowly accumulate
an empty database and conclude the idea does not work. Everything downstream is
worthless if this step is unreliable, so it gets validated first.

### Scope

- Extension detects Apply intent and ships it to an endpoint
- Backend accepts the payload and writes it somewhere durable
- Nothing is parsed, nothing is deduplicated

### Status: ✅ complete, folded into Phase 1

The capture pipe is `raw_events` plus `POST /api/events/batch`. It was built
together with Phase 1 rather than shipped separately, because the "append-only
log" design makes them the same table — there was no intermediate artifact to
build.

### What it bought

The append-only log is the foundation for everything else. Because no raw
capture is ever discarded:

- Parsers can be wrong on day one without permanent data loss
- `/api/admin/reprocess` can retroactively correct your entire history
- `/api/admin/unmatched` can show you what you are still missing

### Exit criteria (met)

- [x] Apply clicks captured across multiple job sites
- [x] Events survive the backend being offline (storage-backed queue + retry)
- [x] Duplicate delivery is harmless (idempotent on `client_event_id`)
- [x] Nothing is ever deleted from `raw_events`

---

## Phase 1 — Parse, dedup, store, export

**Goal:** turn the raw capture stream into a clean, queryable, deduplicated
table of job applications you can export.

**Why it exists:** this is the phase where the project stops being a log file
and becomes a *tracker*. It is also the phase that contains every genuinely
hard problem in the system — identity, deduplication, and company
normalisation. A dashboard on top of bad data is worse than no dashboard,
because it makes the bad data look authoritative.

### Scope

| Area | Deliverable |
|---|---|
| Schema | 6 tables + indexes + CHECK constraints, via Alembic |
| Parsing | Regex engine fed from a database table, not hardcoded |
| Identity | `dedup_key`, navigation chains, ATS-over-aggregator authority |
| Companies | Slug aliases, legal-suffix stripping, trigram index |
| Improvement loop | `/unmatched`, `/patterns/test`, `/patterns` CRUD, `/reprocess` |
| API | List/filter/sort/paginate, stats, CSV + JSON + JSONL export |
| Infra | Docker Compose, non-root image, healthchecks, migrations on boot |
| Extension | WXT + TypeScript, 3 triggers, queue, popup with health UI |
| Tests | Parser tests that need no database |
| **CI** | **GitHub Actions: ruff + mypy + pytest** |

### Status: ✅ complete; CI configured, **awaiting first Actions run**

Everything above is built and working. The CI workflow is now configured; its
first hosted run will verify the checks on GitHub.

### CI workflow

The workflow runs on pushes and pull requests. It installs the backend and its
development tools, then runs Ruff, mypy and pytest. The parser tests do not
need Postgres, so the workflow requires no service container:

```yaml
# .github/workflows/ci.yml
- ruff check app tests
- mypy app
- pytest
```

The implemented Ruff command scopes linting to `app` and `tests`.

### The hard problems, and how they were solved

**Identity across sites.** The same job reached from LinkedIn, from a Google
result, and from a direct link produces three different URLs.
`_dedup_key()` prefers `"{ats}:{external_id}"` over the URL, because the ATS
identity survives tracking parameters, locale prefixes and referral links.

**Navigation chains.** Clicking Apply on LinkedIn and landing on Greenhouse is
one application that generates two events with two different dedup keys. The
extension tags both with a `nav_chain_id`; the resolver ranks sources
(unrecognised `0` < aggregator `1` < real ATS `2`) and upgrades the existing row
in place when the higher-authority leg arrives.

**Company normalisation.** `Discord`, `discord`, `Discord, Inc.` and the
Greenhouse slug `discordinc` must all resolve to one company. Slug lookup runs
*before* name lookup, because the two genuinely disagree, and a slug that has
already been associated with a company is authoritative regardless of what
arrives later.

**Parser rules as data.** Patterns live in `url_patterns`, so fixing Workday is
an `UPDATE`, not a Chrome Web Store release.

### Exit criteria

- [x] One application per job, regardless of how you reached it
- [x] LinkedIn → Greenhouse collapses to one row
- [x] Company name variants resolve to one company
- [x] Adding a pattern and reprocessing fixes history retroactively
- [x] Full export to CSV and JSON
- [x] `docker compose up --build` works from a clean clone
- [ ] **CI green on every push** (workflow configured; first hosted run pending)

---

## Phase 2 — Dashboard

**Goal:** see your applications without `curl`.

**Why it exists:** the data is already correct and already exportable. This
phase is about making it *glanceable* — and, honestly, about having something
to show. An API with no UI is a hard thing to demo.

**Why it comes after Phase 1, not before:** a dashboard built on wrong data
teaches you to trust wrong data. Dedup and identity had to be right first.

### Scope

- Next.js App Router, TypeScript, Tailwind
- **Route Handlers as a server-side proxy to FastAPI** — the browser never sees
  the API key, and there is no CORS to configure. This is why
  `main.py` does not list the dashboard origin.
- Application table: filter by status, ATS, company, date; sort; paginate
- Funnel chart from `/api/stats/summary`
- Applications-over-time chart
- Response rate and interview rate as headline numbers
- Unattributed count with a direct filter for applications missing company attribution

### Status: 🟡 dashboard implemented; live-data verification pending

The dashboard is implemented in `dashboard/`. It uses Next.js Route Handlers
to keep the API key server-side, and adds an unattributed count/filter to the
backend API. The Phase 4 pattern editor and full unmatched-pattern work queue
remain out of scope for this slice.

Live verification still requires `dashboard/.env.local` with `API_BASE_URL`
and `API_KEY`. The development environment used for this implementation has
another service on port 8000, so the UI was verified in its API-unavailable
state rather than against application data.

### The one design constraint that must carry over

`viewed` and `applied` are **different statuses** and must stay visually
distinct. Capture is deliberately high-recall and low-precision — you will
catch jobs you browsed and abandoned. If the dashboard renders both as
"applications", every number it shows is inflated and the funnel lies.

### Exit criteria

- [x] Application table supports status, ATS, company, date and text filters, sorting, and pagination
- [x] Funnel and applications-over-time charts are connected to the stats API
- [x] API key is sent only by server-side Route Handlers
- [x] `viewed` and `applied` have distinct status treatments
- [ ] Verify the dashboard with a configured backend and real application data

---

## Phase 3 — Submission detection

**Goal:** distinguish "I looked at this job" from "I actually applied".

**Why it exists:** this is the difference between a browsing-history viewer and
an application tracker. Without it, every number is inflated by the jobs you
opened and closed, and the response-rate denominator is meaningless.

**Why it is genuinely hard:** there is no reliable universal signal. Some ATSs
redirect to a confirmation page, some show a modal and never navigate, some
change nothing at all. LinkedIn Easy Apply never navigates — there is no URL
change to detect, which is precisely why `intent_click` exists as a separate
trigger.

### The approach: confidence, not certainty

Rather than a boolean "applied", every signal carries a 0–100 confidence score,
and the status follows from a threshold.

| Signal | Confidence | Status | Reasoning |
|---|---|---|---|
| `intent_click` | 10 | viewed | You clicked Apply. You may have abandoned it. |
| `ats_nav` | 30 | viewed | You reached a real ATS. Still no proof of submission. |
| Confirmation URL | 70 | **applied** | A `/thank-you` or `?submitted=true` page is strong evidence. |
| `form_submit` | 90 | **applied** | A real submit event on an ATS domain. |

`APPLIED_CONFIDENCE_THRESHOLD = 70` is the line. Keeping it a tunable integer
means you can move it later without touching resolver logic.

**Why lean high-recall:** deleting a false positive is one click. A silently
missed application is invisible forever. Being wrong in the recall direction is
recoverable; being wrong in the precision direction is not.

### Status: 🟡 detection built, nightly job not built

**Built (pulled forward from Phase 3 into Phase 1):**

- [x] `form_submit` trigger in [content.ts](extension/entrypoints/content.ts),
      gated on `isAtsHost()` so it does not log every search box on the web
- [x] `PatternKind.CONFIRMATION` as a second, independently-matched pattern kind
- [x] 4 seed confirmation patterns (generic `/thank-you`, `?submitted=true`,
      Workday, Greenhouse)
- [x] `confidence` and `status_source` columns
- [x] Threshold logic in [resolver.py](backend/app/parsing/resolver.py)
- [x] Navigation chains, so a confirmation page resolves onto the right row

**Not built:**

- [ ] **Nightly re-resolution job (APScheduler).** Re-examines low-confidence
      applications on a schedule — for instance, promoting a `viewed` row that
      later acquired a confirmation event, or ageing out stale `viewed` rows.
      Pure addition; no schema change needed.
- [ ] **Confirmation patterns tuned against your real traffic.** The four seeds
      are guesses. The actual work of this phase is collecting real post-submit
      URLs and writing patterns that match them.

### What "finishing Phase 3" actually means

Not writing more code — running the system for a few weeks, looking at what
landed in `/api/admin/unmatched` after you submitted real applications, and
adding confirmation patterns that match what you observe. The machinery is
done; the knowledge is not.

### Exit criteria

- [ ] Post-submit URLs from your real applications are matched
- [ ] `applied_total` matches your own count for a known week
- [ ] False `applied` rate low enough that the funnel is trustworthy

---

## Phase 4 — Correction loop

**Goal:** make the system's mistakes fixable in seconds, and make those fixes
permanent.

**Why it exists:** every heuristic system is wrong sometimes. A tracker you
cannot correct is a tracker you stop trusting, and a tracker you stop trusting
is one you stop using. The correction loop is what converts an imperfect
automated system into a reliable one.

**The hard requirement:** a correction must survive `POST /api/admin/reprocess`.
Reprocess truncates `applications` and rebuilds every row from `raw_events`. A
correction stored only on the application row would be destroyed by the next
reprocess — which is exactly when you would run one, after improving a parser.

### The solution

`manual_overrides`, keyed by `dedup_key` rather than `application_id`.

Reprocess creates new rows with new UUIDs, so an `application_id` foreign key
would dangle. `dedup_key` is stable across rebuilds. The resolver calls
`_apply_manual_override()` **last**, after every automatic rule, so a human
decision always wins — and `status_source = 'manual'` locks that row against
future parser changes.

### Status: 🟡 backend complete, UI not built

**Built:**

- [x] `manual_overrides` table, never truncated
- [x] `PATCH /api/applications/{id}` — writes both the row and the override,
      and logs an `ApplicationEvent` for manual status changes
- [x] `_apply_manual_override()` replay on every resolve
- [x] `status_source` guard: `manual` rows are immune to the parser
- [x] `GET /api/admin/unmatched` — the work queue, ranked by hit count
- [x] `POST /api/admin/patterns/test` — dry-run a pattern, store nothing

**Not built:**

- [ ] **The UI.** Inline edit of company, role, status and notes. Bulk archive.
      A dedicated "needs review" view driven by `/unmatched` and by
      low-confidence rows.
- [ ] Pattern editor in the dashboard (currently `curl` only)
- [ ] One-click "reprocess now" with progress feedback

### The loop, end to end

```
   capture  →  see what missed  →  add a pattern  →  reprocess
      ▲                                                  │
      └──────────────────────────────────────────────────┘
```

1. `GET /api/admin/unmatched` — what no pattern caught
2. `POST /api/admin/patterns/test` — try a candidate, store nothing
3. `POST /api/admin/patterns` — commit it
4. `POST /api/admin/reprocess` — fix your entire history retroactively

This loop is the most interview-worthy part of the project. It is the concrete
answer to "how do you handle the fact that your parsers will be wrong?"

### Exit criteria

- [ ] Correct a wrong company in under 5 seconds from the dashboard
- [ ] Corrections demonstrably survive a reprocess
- [ ] Unmatched queue reachable in one click from the dashboard

---

## Phase 5 and beyond

Sketches, not commitments.

| Phase | Idea | Dependency |
|---|---|---|
| 5 | LinkedIn networking tracker — recruiter conversations alongside applications | Independent |
| 6 | JD parsing — capture and extract requirements from job descriptions | Contradicts "record intent, not content"; needs a privacy rethink |
| 7 | CV matching — score your CV against a stored JD | Needs Phase 6 |
| 8 | Email ingestion — parse rejection and interview emails to advance status automatically | Needs OAuth; the highest-value item on this list |

Phase 8 is worth calling out: most status transitions after `applied` arrive by
email. Automating that would close the funnel without any manual input at all.

---

## Dependency graph

```
Phase 0 (capture) ──► Phase 1 (parse + store)
                           │
                           ├──► Phase 2 (dashboard) ──► Phase 4 UI
                           │
                           ├──► Phase 3 (submission detection)
                           │
                           └──► Phase 4 backend  [done]
```

Phase 2 and Phase 3 are independent of each other. Phase 4's UI needs Phase 2's
shell to live in; Phase 4's backend did not.

---

## What to do next

In priority order:

1. **Connect the dashboard to the local backend** and verify filters, metrics,
   and exports against real application data.
2. **Run the tracker for two weeks.** Phase 3 needs real post-submit URLs from
   your applications to tune confirmation patterns.
3. **Add Phase 4's correction UI** to review unattributed records, edit parser
   patterns, and trigger reprocessing.

Item 2 runs in the background while you do 1 and 3.
