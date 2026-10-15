# firstlook — specification

Read `AGENTS.md` for the operating rules before building anything from this file.

## Mission

Build `firstlook`, a local-first job search workbench, end to end, with no human
in the loop. The run ends when every item in the Completion checklist is true and
`make check` passes on a fresh clone.

It finds openings at their source, on the company's own applicant tracking system,
typically days before they reach any aggregator; matches them against the user's
profile including a deliberate band of maybes; tailors a resume per job from a
structured experience bank with every line traceable to something the user
actually did; fills and previews the application form for one-click assisted
submission; and tracks what happened, so that after fifty applications the user
can see which resume variants, categories, and timings actually produce replies.

Everything runs locally against a SQLite file. There is no server, no account, no
telemetry. The app must be useful with no API key and no local model, and must
never spend meaningful money on jobs the user has not expressed interest in.

Reference point for the UI is Jobright: dense, scannable, immediate. The layout
is a main panel with a persistent side chat that can see the current view and act
through the app's own tools, in the manner of an agentic coding client.

## Product scope

In scope for v1:

- A company registry and adapters for the major ATS platforms, ingesting
  structured job data directly from company boards.
- Incremental, polite crawling with ETag and If-Modified-Since, first-seen
  timestamps, dead-job detection, and ghost-job flagging.
- Deterministic and local extraction of skills, seniority, compensation, remote
  policy, and work-authorization language.
- Company-level categorisation (startup, B2B, SaaS, enterprise, agency, non-profit,
  public sector) with user-editable tags.
- Local embedding match with a lexical fallback, a strong band and a "might match"
  band, per-job explanations, and a locally trained reranker over user feedback.
- An experience bank and a live tailor: structured resume data, per-job selection
  and rephrasing with provenance on every line, locked metrics, layout budget,
  Typst rendering, and an ATS parse-back check.
- Application tracker with pipeline states, follow-up reminders, and receipts.
- Assisted one-click apply: form fill, diff preview, explicit confirm, batch
  confirm for simple forms.
- Analytics: response rate by segment with intervals, resume-variant A/B,
  lead-time effect, effort-weighted return, ghosting survival curve.
- A side chat with tool access to the app's own API, local-provider-first with
  budget enforcement.
- CLI for every operation the UI performs.

Out of scope for v1 (do not build, do not stub beyond an interface):

- Scraping LinkedIn, Indeed, Glassdoor, or any site whose terms prohibit it, and
  any paid data API. The architecture must not assume them.
- Automatic submission without user confirmation, in any mode.
- Automatic answering of EEO, veteran status, disability, or work-authorization
  questions. These default to decline-to-answer or to a value the user set
  explicitly in their profile, and they appear in the diff every time.
- Multi-user accounts, hosted deployment, email or calendar integration, browser
  extensions, mobile apps.
- Cover-letter generation as a document. The tailor produces bullet points to work
  from; writing prose for the user is phase two.
- Interview preparation, salary negotiation tooling, networking features.

## Cost model

The central engineering constraint. The user exports this repo to other machines
and must not burn their subscriptions. **AI spend scales with jobs the user
touches, never with jobs ingested.**

Four tiers. Work never escalates to a higher tier than it needs.

- **Tier 0, free and deterministic.** Everything the ATS already returns as
  structured JSON: title, location, department, employment type, posting date,
  description body, and often compensation and remote policy. Most of the product
  runs here.
- **Tier 1, free and local.** Rule-based extraction over the description: skills
  and tools from a shipped dictionary with alias handling, seniority from title
  patterns, years-of-experience, compensation ranges by regex, remote and hybrid
  language, visa and clearance language, and degree requirements. Runs over every
  job on every crawl.
- **Tier 2, local embeddings.** A MiniLM-class ONNX sentence encoder, CPU, under
  100 MB, embedding each job once at ingest and caching the vector. Used for
  matching, the maybe band, near-duplicate detection, and clustering. If the model
  is absent, fall back to BM25 over the same text; the app must work, with a
  visible note that matching is in lexical mode.
- **Tier 3, LLM.** Only ever on a specific job the user has starred, opened in the
  tailor, or asked about in the chat. Used for keyword gap analysis, bullet
  rephrasing, essay-question bullet points, and the side chat.

Enforcement, all required:

- A `budget` ledger table recording every LLM call: feature, model, input and
  output tokens, estimated cost, and the job it related to. Every call goes
  through one client that writes this row; a call that bypasses it is a bug.
- Per-run and per-day token ceilings in config, enforced by that client, with a
  clear error and graceful degradation when hit.
- A response cache keyed by (feature, model, content hash). Re-running a tailor on
  an unchanged job and unchanged bank costs nothing.
- `firstlook estimate <command>` prints predicted token spend before any bulk
  operation, and bulk operations over more than 25 jobs require `--yes`.
- Provider resolution order: local OpenAI-compatible server if reachable, then a
  user-supplied key, then degrade to tier 2 with the feature disabled and a note
  in the UI rather than an error.
- An acceptance test asserts that a full crawl and index of the 1,000-company
  fixture corpus issues exactly zero LLM calls.

## Architecture and stack

Python backend owning all logic and data, thin React frontend, SQLite file, one
process.

- Python 3.11+, FastAPI, uvicorn, pydantic v2, httpx with HTTP/2 and connection
  pooling, `selectolax` for the little HTML parsing needed, `onnxruntime` for
  embeddings, `playwright` for assisted apply, `rapidfuzz` for dedupe,
  `scikit-learn` for the reranker, `numpy`, `rusqlite`-equivalent is not needed:
  use the stdlib `sqlite3` with WAL plus a small migration runner.
- Frontend: Vite, React, TypeScript, Tailwind. Dense table-first UI, keyboard
  navigable, dark mode. No component library beyond headless primitives.
- Resume rendering: Typst, invoked as a vendored or user-installed binary, with a
  graceful message if absent. Not LaTeX.
- A `typer` CLI exposing every backend operation.

```
backend/firstlook/
  registry/     company registry, ATS detection, seed data, verification
  adapters/     one module per ATS, all behind a single Source protocol
  ingest/       crawl scheduler, conditional requests, dedupe, first-seen, decay
  extract/      tier 1 rules, dictionaries, normalisers
  embed/        ONNX encoder, BM25 fallback, vector store
  match/        scoring, bands, explanations, reranker, exploration budget
  bank/         experience bank model, validation
  tailor/       selection, rephrasing, provenance, layout budget, Typst render
  apply/        Playwright drivers, form maps, profile fill, diff, receipts
  track/        applications, states, reminders
  analytics/    segments, intervals, A/B, survival, effort-weighted return
  llm/          provider resolution, budget ledger, cache, prompts
  chat/         tool definitions and the agent loop
  api/          FastAPI routers
  cli.py
data/
  registry.seed.jsonl   companies shipped with the repo
  skills.yaml           skill dictionary with aliases
  categories.yaml       category rules and heuristics
  formmaps/             per-ATS form field mappings
frontend/
fixtures/
  cassettes/    recorded ATS HTTP responses, one dir per adapter
  forms/        saved application form HTML for apply tests
  history/      synthetic application history for analytics tests
```

Make targets: `setup`, `check` (ruff, mypy, pytest, frontend typecheck and build),
`test`, `run`, `crawl`, `model` (download the embedding model; optional and
documented as such), `smoke`, `dist`.

## Company registry and ATS adapters

**The registry is the product's advantage and its maintenance burden.** One row
per company: name, domain, ATS platform, board token, category tags, size bucket,
`verified`, `last_crawled`, `last_success`, `consecutive_failures`, and notes.

Adapters implement one protocol: `fetch(company) -> list[RawPosting]`, plus
`detect(careers_url) -> Optional[tuple[platform, token]]`.

v1 adapters, in build order: **Greenhouse**, **Lever**, **Ashby**,
**SmartRecruiters**, **Workable**, **Recruitee**, then a **JSON-LD** adapter that
reads `schema.org/JobPosting` markup from a company's own careers page, respecting
`robots.txt`. **Workday** lands in its own milestone because it needs a POST
against a tenant-specific endpoint with pagination. iCIMS and Taleo are explicitly
out of v1.

Each adapter normalises into a common `RawPosting`: external id, title, absolute
apply URL, location strings, remote flag, department, employment type, posted
timestamp when given, description HTML and plain text, and compensation fields
when present.

**Discovery.** `firstlook registry discover <careers-url>` sniffs which ATS a
company uses from its careers page and extracts the board token, then adds the
company unverified. `firstlook registry verify [--all]` makes one live request per
company, marks successes verified, and prunes or flags dead tokens. Both are run
by the user, never during the build.

**Seeding.** Ship at least 300 companies in `registry.seed.jsonl`, weighted toward
software, AI, aviation, defence, health tech, and quantitative finance, each with
your best guess of platform and token and `verified: false`. Generate
`REVIEW_REGISTRY.md` listing them with a blank verified column and the one command
that checks them all. Never mark a seeded entry verified yourself.

**Politeness, binding.** Global and per-host concurrency caps, a minimum delay per
host, exponential backoff with jitter on 429 and 5xx, a descriptive User-Agent
with a contact placeholder the user fills in, ETag and If-Modified-Since on every
request, and `robots.txt` respected by the JSON-LD adapter. A crawl of unchanged
boards must transfer almost nothing.

## Ingestion

Scheduler picks companies by staleness and by hit rate, so boards that post often
are polled more. Incremental by default, full re-crawl on demand.

- **Identity and dedupe.** A posting's identity is (company, ATS external id).
  Near-duplicates across locations or reposts are grouped by fuzzy title match
  plus description similarity, shown as one row with multiple locations.
- **first_seen** is set the first time firstlook sees a posting and never changes.
  This is what powers the lead-time badge and the lead-time analysis, so it is
  written before anything else and is immutable.
- **Dead-job detection.** A posting absent from its board for two consecutive
  successful crawls is marked closed, with `closed_detected_at`. Distinguish this
  from a crawl failure; never mark jobs closed off a failed fetch.
- **Ghost-job flagging.** Flag postings open beyond a configurable age, and
  postings whose external id churns while title and description stay constant
  (repost behaviour). Show the flag; do not hide the job.
- Full history: every crawl writes a `crawl_run` row with counts, bytes, duration,
  and per-company outcomes, so the user can see the system working.

## Extraction and enrichment

Tier 1 only, no LLM. Over each description: skills and tools against
`skills.yaml` with alias and acronym handling and negation awareness ("nice to
have" versus required), seniority, years of experience, degree requirement,
compensation range with currency and period, remote or hybrid or onsite with any
geographic restriction, visa sponsorship and clearance language, and company size
cues.

**Categories are company attributes, enriched once per company, not per posting.**
Rules in `categories.yaml` combining: ATS platform as a weak signal (Ashby and
Lever skew startup, Workday and iCIMS skew enterprise), open-role count, the
company's own site text when the JSON-LD adapter has it, and a shipped seed
classification. Tags are editable in the UI and user edits always win and are
never overwritten by a later crawl.

## Matching

A profile is the user's titles of interest, locations, remote preference,
seniority range, must-have and nice-to-have skills, dealbreakers, and compensation
floor. Job titles and areas are chosen by the user before any crawl, as the spec
requires.

Scoring combines: hard filters (dealbreakers, location, authorization), a lexical
requirement overlap score, and cosine similarity between the job embedding and the
profile embedding. Two thresholds produce three groups: **strong**, **possible**
(the deliberate maybe band), and **filtered out but visible on request**.

Every job shows **why**: which requirements matched, which are missing, and which
dealbreaker fired. No opaque scores.

**Reranker.** Thumbs up and down, stars, and application outcomes train a logistic
regression over embedding plus feature vectors, locally, with a floor of 50
labelled examples before it influences ranking. Retrain on demand and on a
schedule.

**Exploration budget.** A configurable share of recommendations, default one in
ten, is drawn from outside the model's current preference and labelled as such in
the UI. Without this the reranker silently narrows the search and the user never
learns whether a neglected segment would have worked.

## Experience bank and live tailor

**The resume is structured data. It is never a document the model edits.**

The bank holds entries: roles, projects, publications, education, skills. Each
entry has an id, dates, organisation, one or more bullets in the user's own
phrasing, immutable `metrics` fields, tags, and a default inclusion weight.

A **tailored variant** is a selection of bank entry ids, an ordering, per-bullet
rephrasings, and a template choice. Three rules are enforced mechanically:

1. **Provenance.** Every rendered line carries the bank entry id it derives from.
   A line without one cannot be exported; the UI blocks it and names it.
2. **Locked metrics.** Numbers in `metrics` are substituted verbatim at render
   time. The model may choose whether a bullet appears and how the words around
   the number read, and may not alter the number. A rephrasing whose rendered
   numbers differ from the source entry's is rejected automatically.
3. **Layout budget.** The renderer reports remaining lines per page, and the
   tailor is given that budget. Suggestions that overflow are flagged before
   rendering.

Every suggestion is a diff the user accepts or rejects individually. Nothing is
applied silently.

**Gap report**, the main output alongside the resume: two columns, things the user
has in the bank that this variant did not surface, and requirements the bank does
not cover at all. The first column is the valuable one.

**Rendering.** Typst templates to PDF, single-column by default. After rendering,
re-extract the text from the PDF and assert that name, contact details, every job
title, every organisation, and every date range round-trip correctly. A variant
that fails the parse-back check cannot be marked ready.

**Versioning.** Every variant is immutable once used on an application and is
stapled to that application. This is what makes the A/B analysis possible, so it
is a storage requirement, not a convenience.

Cost: tailoring only runs on a starred or opened job, and caches on (job hash,
bank version, template).

## Assisted apply

Playwright, per-ATS form maps in `data/formmaps/`, driven from a structured
application profile (contact details, work authorization answers the user set
explicitly, links, default answers to common questions).

Flow: open the real form in a visible browser context, fill from the profile and
the chosen resume variant, then show a **diff panel** listing every field and the
exact value to be submitted, including file attachments, with unanswered required
fields highlighted. The user confirms. Only then does the driver submit.

- **No auto-submit exists.** Not behind a flag, not in the CLI, not in the chat
  tools.
- **EEO, veteran, disability, and work-authorization fields** are never
  auto-answered from inference. They come from explicit profile settings, default
  to decline-to-answer, and always appear in the diff.
- **Batch confirm**: queue several simple-form applications, review them as a
  list, confirm them in one action. Each still renders its own diff.
- **Essay questions** are detected and routed to the tailor, which returns three
  to five bullet points drawn from the bank with provenance. The user writes the
  prose. The app does not submit a form containing an essay the user has not
  edited.
- **Receipts**: on submission, store the submitted field values, the resume
  variant id, a screenshot, a timestamp, and the detected confirmation state.
- **Effort capture**: record form field count, whether essays were present, and
  wallclock minutes spent. This feeds the effort-weighted analytics.

Testing: all apply tests run Playwright against saved form HTML in
`fixtures/forms/`, served locally. No live submissions during the build, ever.

## Tracker and analytics

**Tracker.** States: saved, applied, acknowledged, screen, interview, offer,
rejected, ghosted, withdrawn. Manual state entry plus a reminder when an
application has been silent past a threshold. Notes and contacts per application.

**Analytics, local SQL and numpy, no AI, with uncertainty carried everywhere.**

- Response rate by segment: category, company size, ATS, seniority, remote policy,
  referral or not, resume variant, lead time bucket. Wilson score intervals on
  every rate.
- **Minimum sample gate**: a segment with fewer than a configurable n (default 12)
  shows its raw counts and no rate, no interval, and no claim. Nothing in the UI
  may call a difference significant; the language is "worth noticing", and a
  tooltip says how many more applications would be needed to distinguish the
  segments at the current gap.
- **Resume variant A/B**: response rate by variant, overall and within segment,
  with the same gate. This is the headline feature of the analytics page.
- **Lead-time effect**: response rate as a function of days between `first_seen`
  and application, bucketed. This tests the premise the whole product is built on,
  and the UI presents the result either way.
- **Effort-weighted return**: responses per hour invested by segment, from the
  captured effort data. The "not worth the hassle" ranking.
- **Ghosting survival curve**: Kaplan-Meier estimate of the probability of ever
  hearing back given N days of silence, from the user's own history, used to set
  the follow-up reminder threshold and to mark applications as effectively dead.
- Export every analytics table to CSV.

## UI

Three regions: a left rail for saved searches, filters, and pipeline states; a
main panel; and a persistent right-hand chat that can be collapsed.

Main panel views: **Jobs** (dense virtualised table: title, company, category
tags, location, compensation, match band, lead-time badge, flags, age), **Job
detail** (description, extracted requirements, match explanation, gap report,
tailor launcher, apply button), **Tailor** (bank on one side, variant on the
other, diffs inline, live PDF preview, parse-back status), **Pipeline** (kanban or
table of applications with reminders), **Analytics**, **Bank**, **Registry**, and
**Settings** (profile, providers, budgets, thresholds).

Keyboard first: j and k to move, s to star, t to tailor, a to apply, / to search.

**Side chat.** The agent receives the structured state of the current view, never
scraped DOM text, and acts through the same tools the UI uses:
`search_jobs(filters)`, `open_job(id)`, `explain_match(id)`, `tailor(job_id,
instructions)`, `diff_variant(id)`, `draft_answer(job_id, question)`,
`star(id)`, `queue_apply(id)`, `track(id, state)`, `analytics(query)`,
`registry_add(url)`. Tools that spend tokens report their estimated cost back into
the ledger; tools that would submit an application can only queue it.

## Database model

SQLite, WAL, numbered migrations. Tables: `company`, `job`, `job_extract`,
`job_embedding`, `crawl_run`, `crawl_result`, `profile`, `match_feedback`,
`bank_entry`, `resume_variant`, `variant_line` (with `bank_entry_id` for
provenance), `application`, `application_field` (the receipt), `application_event`,
`llm_call` (the budget ledger), `cache`, `setting`. Money in integer cents, dates
in ISO strings, every table with `created_at`.

## Milestones

A milestone is done when its tests pass, `make check` is green, the commit is
made, and its boxes in `PLAN.md` are ticked. The order puts the aggregator first
so an interrupted run still leaves something useful.

| Milestone | Build | Done when |
| --- | --- | --- |
| M0 Scaffold | Repo layout, Makefile, pinned deps, `PLAN.md` with every task in this spec, `ASSUMPTIONS.md`, `.gitignore`, FastAPI app with `/api/health`, empty Vite app, migration runner | `make check` passes on an empty app; first commit |
| M1 Registry | Schema, registry model, seed file of 300+ companies, ATS detection, `registry discover` and `verify` commands, `REVIEW_REGISTRY.md` | Seed loads and validates; detection returns the right platform for every cassette; no seeded row is marked verified |
| M2 Adapters and ingestion | Six adapters plus JSON-LD, Source protocol, conditional requests, scheduler, dedupe, first_seen, dead-job and ghost flags, cassettes for every adapter | Each adapter parses its cassette with zero unmatched fields; re-ingest is a no-op; a posting removed from a cassette board is marked closed after two runs; a 304 response costs no parse |
| M3 Extraction | Skill dictionary, all tier 1 extractors, company categorisation, user tag overrides | Golden extraction fixtures pass; categorisation matches the labelled fixture set to the stated accuracy floor; a user tag survives a re-crawl |
| M4 Matching | Profile model, ONNX encoder with BM25 fallback, scoring, bands, explanations, feedback capture, reranker, exploration budget | Ranking is deterministic for a fixed corpus and profile; the app works with the model file absent; reranker refuses to influence ranking below 50 labels; a full index of the 1,000-job fixture corpus issues zero LLM calls |
| M5 UI shell | Layout, Jobs table, Job detail, filters, saved searches, keyboard navigation | Typecheck, lint, build green; every panel renders from the fixture corpus; virtualised table handles 20,000 rows |
| M6 Bank and tailor | Bank model, variant model, provenance gate, locked metrics, layout budget, Typst render, parse-back check, gap report | A rephrasing that alters a metric is rejected; a line without provenance blocks export; parse-back recovers all identity fields from the rendered PDF; tailoring the same job twice costs zero tokens |
| M7 LLM layer and chat | Provider resolution, budget ledger, cache, prompts, tool definitions, side chat, `estimate` command | Every LLM path writes a ledger row; exceeding the ceiling degrades rather than errors; with no provider configured, chat and tailor degrade with a visible note and the rest of the app is unaffected |
| M8 Tracker and assisted apply | Pipeline states, reminders, Playwright drivers, form maps, profile fill, diff panel, confirm, batch confirm, receipts, effort capture | Apply tests pass against saved form fixtures; no code path submits without an explicit confirm call; EEO and work-authorization fields are never filled from inference; a receipt is written for every simulated submission |
| M9 Analytics | Segments, Wilson intervals, minimum-sample gate, variant A/B, lead-time analysis, effort-weighted return, Kaplan-Meier survival, CSV export | Every metric matches a hand-computed value on the synthetic history fixture; a segment under the gate displays counts only; the survival curve matches the reference implementation to tolerance |
| M10 Ship | `make dist`, `RUNBOOK.md`, `COST.md`, final `ASSUMPTIONS.md` and `REVIEW_REGISTRY.md` pass, fresh-clone test | Completion checklist fully true; final commit tagged `v0.1.0` |

## Testing requirements

- **No network in tests.** A fixture HTTP transport is installed globally in the
  test suite; any real request fails the run.
- **Cassettes** per adapter under `fixtures/cassettes/`, including a 304, a 429, a
  500, an empty board, a board with 500 postings, and a malformed payload.
- **Golden extraction**: a labelled set of at least 60 job descriptions covering
  compensation formats, remote language, visa and clearance language, and
  seniority, with expected extractions.
- **Synthetic history**: a deterministic generator producing a plausible
  application history with known ground-truth rates, used to test every analytics
  figure against hand-computed values.
- **Form fixtures**: saved HTML for Greenhouse, Lever, and Ashby application
  forms, served locally for the apply tests.
- **Cost assertions**: zero LLM calls during crawl, index, match, and analytics;
  ledger rows written for every call that does happen; cache hit on a repeated
  tailor.
- **Degradation tests**: no embedding model, no LLM provider, no Typst binary, no
  Playwright browsers. Each produces a working app with a clear message.
- **Property tests**: dedupe is idempotent; `first_seen` never changes; a closed
  job that reappears is reopened rather than duplicated.
- `make check` runs ruff, mypy, pytest with coverage (80% floor for `adapters/`,
  `ingest/`, `extract/`, `match/`, `tailor/`, `analytics/`), then the frontend
  typecheck, lint, and build.

## Legal and safety constraints

Binding, and stated in `RUNBOOK.md` for the user as well.

- Only sources that publish job data for programmatic consumption, or a company's
  own page under `robots.txt`. No LinkedIn, Indeed, Glassdoor, or any site whose
  terms prohibit automated access, and no circumvention of anti-bot measures.
- Rate limits and backoff are not optional and are not user-configurable below the
  shipped floor.
- The user is the applicant. Every submission is reviewed and confirmed by them,
  under their own identity, with their own answers to legal questions.
- Resume content is selected from what the user wrote, never invented. The
  provenance gate enforces it.
- No credentials in the database. No telemetry. No outbound traffic except ATS
  endpoints and the user's chosen LLM provider.

## Phase two (specify the boundaries in v1, build later)

- Workday adapter, then iCIMS and Taleo.
- Cover letter drafting as prose, built on the same provenance gate.
- Referral tracking and warm-intro surfacing from a user-supplied contact list.
- Scheduled background crawls with desktop notifications for high-match postings.
- A shared, importable registry format so users can exchange company lists.

## Completion checklist

The run ends only when every line is true. Check them yourself; do not report done
on the strength of the milestone commits alone.

- [x] `SPEC.md`, `AGENTS.md`, `PLAN.md` (all boxes ticked), `ASSUMPTIONS.md`,
      `RUNBOOK.md`, `COST.md`, `REVIEW_REGISTRY.md` exist and are current.
- [x] `make check` passes on a fresh clone in a temp directory.
- [x] The full test suite runs with no network access available.
- [x] `make smoke` ingests the fixture corpus, indexes it, matches it against a
      sample profile, renders a tailored resume, simulates an application against
      a form fixture, and prints the analytics tables, with zero LLM calls.
- [x] Zero-cost assertion: crawl, index, match, and analytics over the
      1,000-company fixture corpus issue no LLM calls, proven by an empty
      `llm_call` table in that test.
- [x] No code path submits an application without an explicit user confirmation,
      and no code path auto-answers EEO, veteran, disability, or work-authorization
      questions. Both are asserted by tests whose names say so.
- [x] A resume line without a `bank_entry_id` cannot be exported, and a rephrasing
      that changes a locked metric is rejected. Both asserted by tests.
- [x] The app starts and is useful with no API key, no embedding model, no Typst
      binary, and no Playwright browsers installed, each degradation tested.
- [x] No seeded registry entry is marked verified, and `REVIEW_REGISTRY.md` lists
      every unverified company with the command that checks them.
- [x] `git status` is clean, the final commit is tagged `v0.1.0`, and the database,
      exports, downloaded models, and any `.env` are gitignored.
- [x] `RUNBOOK.md` covers: install, choosing target titles and areas, seeding and
      verifying the registry, the first crawl, reading match explanations, filling
      the experience bank, tailoring, applying, logging outcomes, reading the
      analytics with their sample-size caveats, configuring a local or hosted
      model, and what the app costs to run.
