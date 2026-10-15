Current task: M1.

## M0 Scaffold
- [x] Package layout, pinned Python/frontend dependencies and lockfiles
- [x] Make targets, ignore rules, plan and decisions
- [x] Loopback API health, React shell, SQLite WAL migration runner
- [x] Offline tests, ruff, mypy, frontend typecheck/lint/build; commit

## M1 Registry
- [ ] Full company schema, validated models and 300+ unverified seeds
- [ ] ATS detection; discover/verify CLI; review registry
- [ ] Fixture-only detection, seed validation tests; check and commit

## M2 Adapters and ingestion
- [ ] Source protocol, Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Recruitee, JSON-LD
- [ ] Conditional HTTP, concurrency, delay floors, retry/backoff, robots
- [ ] Staleness/hit scheduler, dedupe, immutable first seen, two-miss closure/reopen, ghost flags
- [ ] Crawl history/counts/bytes, every adapter's status/empty/500/malformed cassettes
- [ ] Offline adapter and ingestion acceptance/property tests; check and commit

## M3 Extraction
- [ ] Skills/aliases/negation, seniority/years/degree/compensation/remote/geo/visa/clearance/size
- [ ] Category rules and editable company tags that survive recrawl
- [ ] 60+ labelled golden fixtures and category accuracy tests; check and commit

## M4 Matching
- [ ] Profile prerequisites, hard filters, overlap/cosine scores, bands and explanations
- [ ] Optional ONNX encoder/vector cache, BM25 fallback, local dedupe/clustering
- [ ] Feedback and logistic reranker with 50-label floor, scheduled retraining and exploration
- [ ] Determinism, absent model, 1000-company/job zero-LLM tests; check and commit

## M5 UI shell
- [ ] Three-region shell, jobs/detail, visible requirements/explanations/flags/gaps
- [ ] Filters, saved searches, keyboard j/k/s/t/a/search, dark mode
- [ ] Virtualised 20000-row table and all panels on fixture data
- [ ] Frontend checks and local UI integration; check and commit

## M6 Bank and tailor
- [ ] Structured bank/versioning, selection/order/templates, diff accept/reject
- [ ] Provenance gate, immutable metrics, layout budgets, gap report
- [ ] Typst PDF/parse-back/preview/readiness; immutable used variants
- [ ] No-provider tailor cache and safety/degradation tests; check and commit

## M7 LLM and chat
- [ ] Local-first/provider fallback, central ledger, atomic run/day ceilings, response cache
- [ ] Job-interest gate, estimate command and bulk >25 confirmation
- [ ] Structured chat context, complete shared tool set, no-provider commands and visible note
- [ ] Ledger/cache/budget/no-provider tests; check and commit

## M8 Tracker and assisted apply
- [ ] States/events/notes/contacts/reminders and effort capture
- [ ] Visible Playwright mapped form fill, field/file diff, required/essay validation
- [ ] Explicit individual/batch confirmation, sensitive answers, receipts/screenshots
- [ ] Saved Greenhouse/Lever/Ashby forms, browser and missing-browser tests; check and commit

## M9 Analytics
- [ ] Segment/variant/lead-time rates and Wilson intervals; minimum sample gate
- [ ] Effort return, Kaplan-Meier curve, reminders, CSV export and UI
- [ ] Deterministic history and hand/reference calculations, zero-LLM tests; check and commit

## M10 Ship
- [ ] Complete RUNBOOK/COST/README/assumptions/review registry
- [ ] Smoke: fixture ingest/index/match/PDF/form/analytics with zero LLM
- [ ] Coverage floors, network isolation, missing optional tools, confirmation/provenance audit
- [ ] Distribution packaging and fresh-clone make check
- [ ] All completion checklist assertions verified; clean git and v0.1.0 tag
