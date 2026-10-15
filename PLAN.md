Current task: M10 — fresh-clone verification and final release tag.

## M0 Scaffold
- [x] Package layout, pinned Python/frontend dependencies and lockfiles
- [x] Make targets, ignore rules, plan and decisions
- [x] Loopback API health, React shell, SQLite WAL migration runner
- [x] Offline tests, ruff, mypy, frontend typecheck/lint/build; commit

## M1 Registry
- [x] Full company schema, validated models and 300+ unverified seeds
- [x] ATS detection; discover/verify CLI; review registry
- [x] Fixture-only detection, seed validation tests; check and commit

## M2 Adapters and ingestion
- [x] Source protocol, Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Recruitee, JSON-LD
- [x] Conditional HTTP, concurrency, delay floors, retry/backoff, robots
- [x] Staleness/hit scheduler, dedupe, immutable first seen, two-miss closure/reopen, ghost flags
- [x] Crawl history/counts/bytes, every adapter's status/empty/500/malformed cassettes
- [x] Offline adapter and ingestion acceptance/property tests; check and commit

## M3 Extraction
- [x] Skills/aliases/negation, seniority/years/degree/compensation/remote/geo/visa/clearance/size
- [x] Category rules and editable company tags that survive recrawl
- [x] 60+ labelled golden fixtures and category accuracy tests; check and commit

## M4 Matching
- [x] Profile prerequisites, hard filters, overlap/cosine scores, bands and explanations
- [x] Optional ONNX encoder/vector cache, BM25 fallback, local dedupe/clustering
- [x] Feedback and logistic reranker with 50-label floor, scheduled retraining and exploration
- [x] Determinism, absent model, 1000-company/job zero-LLM tests; check and commit

## M5 UI shell
- [x] Three-region shell, jobs/detail, visible requirements/explanations/flags/gaps
- [x] Filters, saved searches, keyboard j/k/s/t/a/search, dark mode
- [x] Virtualised 20000-row table and all panels on fixture data
- [x] Frontend checks and local UI integration; check and commit

## M6 Bank and tailor
- [x] Structured bank/versioning, selection/order/templates, diff accept/reject
- [x] Provenance gate, immutable metrics, layout budgets, gap report
- [x] Typst PDF/parse-back/preview/readiness; immutable used variants
- [x] No-provider tailor cache and safety/degradation tests; check and commit

## M7 LLM and chat
- [x] Local-first/provider fallback, central ledger, atomic run/day ceilings, response cache
- [x] Job-interest gate, estimate command and bulk >25 confirmation
- [x] Structured chat context, complete shared tool set, no-provider commands and visible note
- [x] Ledger/cache/budget/no-provider tests; check and commit

## M8 Tracker and assisted apply
- [x] States/events/notes/contacts/reminders and effort capture
- [x] Visible Playwright mapped form fill, field/file diff, required/essay validation
- [x] Explicit individual/batch confirmation, sensitive answers, receipts/screenshots
- [x] Saved Greenhouse/Lever/Ashby forms, browser and missing-browser tests; check and commit

## M9 Analytics
- [x] Segment/variant/lead-time rates and Wilson intervals; minimum sample gate
- [x] Effort return, Kaplan-Meier curve, reminders, CSV export and UI
- [x] Deterministic history and hand/reference calculations, zero-LLM tests; check and commit

## M10 Ship
- [x] Complete RUNBOOK/COST/README/assumptions/review registry
- [x] Smoke: fixture ingest/index/match/PDF/form/analytics with zero LLM
- [x] Coverage floors, network isolation, missing optional tools, confirmation/provenance audit
- [ ] Distribution packaging and fresh-clone make check
- [ ] All completion checklist assertions verified; clean git and v0.1.0 tag
