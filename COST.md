# What firstlook costs

Crawling, extraction, indexing, matching, feedback training, deterministic tailoring, PDF rendering, application assistance and analytics make **zero LLM calls**. Their cost is your machine's CPU/storage and ordinary ATS traffic. Model weights are optional and downloaded once only when you run `make model`.

AI runs only for a specific starred or opened job when you request it. Provider resolution is configured local OpenAI-compatible endpoint, configured hosted provider, then useful local degradation. Credentials come exclusively from environment variables (which may be populated by an OS keyring).

Every inference request uses `firstlook.llm.Client`. It checks eligibility, hashes feature/model/source content for the response cache, opens an immediate SQLite transaction and reserves conservative input bytes plus protocol overhead and maximum output tokens. Both per-run and per-day limits must allow the reservation before any inference request is sent. Daily limits use UTC dates consistently with the SQLite ledger. Requests in one agent/tool run share a run ID. Cache hits cost zero. Failed responses keep a reservation because a provider may have processed them.

Successful ledger rows record feature, model, related job, run ID, input/output tokens, status and integer estimated cost cents. Local calls are zero monetary cost but still obey token ceilings. Hosted estimates use `FIRSTLOOK_INPUT_CENTS_PER_MILLION` and `FIRSTLOOK_OUTPUT_CENTS_PER_MILLION` (defaults 1000/3000). Configure these for your selected provider; the app does not fetch prices or promise an exact invoice. Rounding is upward to a whole cent per call.

```sh
firstlook estimate crawl --count 1000  # 0 predicted tokens
firstlook estimate tailor --count 10 # conservative planning estimate; local tailor itself is free
```

AI estimates are approximate; enforcement uses the actual source's conservative reservation. Bulk CLI operations over 25 items require `--yes`, and bulk UI crawls require confirmation. This flag cannot confirm an application. Every application has its own reviewed diff and an explicit, single-use confirmation token.

Tests assert an empty `llm_call` ledger after a full 1,000-company fixture crawl/index/match/analytics run; provider tests verify reservations before request dispatch, cache hits, ceilings, unknown-usage failures and no-provider behavior.
