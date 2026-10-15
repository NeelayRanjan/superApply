# Decisions

- The repository calls the application `firstlook`; retain that name despite the GitHub repository name.
- "One process/no server" means one loopback-only Python process serving the API and compiled UI, with no hosted service.
- Package installation and GitHub source acquisition are build prerequisites; the prohibition on live traffic applies to product data and provider requests. No live ATS or LLM requests are made during development.
- The repository contains no recorded fixtures. Author synthetic, explicitly labelled response cassettes matching documented platform shapes; do not claim they were captured live.
- The phase-two boundary and milestone table place Workday outside v1, resolving the earlier contradictory mention of a separate v1 milestone.
- Categorisation accuracy floor is unspecified; use 90% on the labelled synthetic corpus.
- Tests prohibit external network; loopback is permitted only for saved browser form fixtures and local app integration tests.
- ONNX weights and Playwright browsers are optional downloads, never fetched at runtime. Ship tested non-AI and manual apply paths.

# Deviations

- No live-recorded fixtures were supplied; synthetic cassettes are used throughout and labelled as such.

## Release decisions

- Python 3.12 is the reproducible development baseline for the committed transitive lock; the application language/features remain Python 3.11-compatible.
- Seed candidates total 524. Their platform/token/domain guesses are intentionally conservative and may fail; no claim of live adapter or registry verification is made.
- Source fixtures are synthetic platform-shaped responses; no production pages or ATS endpoints were accessed. Model weights were not downloaded; the optional runtime/vector path is tested with local deterministic vectors.
- The optional model download records source/revision/hash in an ignored manifest; users can pin `FIRSTLOOK_MODEL_REVISION` before download.
- Identity is an additional bank entry kind so contact headings also have explicit source provenance. Variants store bank snapshots; later source edits cannot mutate submitted resumes.
- Typst can be provided by a system executable or the pinned Python package's embedded Rust engine. Missing both leaves source and blocks readiness.
- Classic and compact are single-column templates with different type sizes; one-page layout is validated by the rendered PDF, not just a character estimate.
- The crawler runs sequentially under the stricter shared host/global caps. Frequency is prioritised using staleness and hit rate; autonomous recurring crawls remain phase two.
- Reranking uses lexical/requirement features plus 384 embedding features (zeros without a model), with daily retraining at indexing and feedback-count retraining every ten labels after the floor.
- Sensitive hidden site security tokens are not stored in receipts. Visible application answers and uploaded resume filenames are recorded; unsupported complex fields remain manual.
- The no-browser path is manual application plus explicit tracker entry. It never fabricates a submission receipt or claims browser confirmation.
- Kaplan–Meier charts report probability of still waiting and conditional response within observed follow-up, not an unidentifiable probability of ever hearing back. Follow-up thresholds are user-applied; the app does not silently mark a person rejected or ghosted.
- Sample-size tooltips are a normal-approximation planning estimate at the current observed gap, not a significance test or a causal claim.
- The bounded provider chat loop uses at most three job-specific, budgeted steps. Shared local tools handle search and aggregate analytics without AI; there is no submission tool.
- Frontend checks/build run before pytest so browser tests always use the current production bundle, including on a fresh clone.
- Registry verification retains the specification's `--all` command as explicit bulk intent; crawl and bulk tool operations over 25 items use `--yes` or the UI confirmation.
- All runtime provider configuration is supplied through environment variables; the UI edits budgets and reports degradation. Keys are never accepted by the settings API.
