# Run firstlook

firstlook is a local Python/React application. One process binds to `127.0.0.1:8765` and serves the API and compiled UI. Your database is `.firstlook/firstlook.db`; no account or hosted service is used.

## Install and start

Use Python 3.12+ and Node 22+ (tested with Python 3.12 and Node 24). From this repository:

```sh
make setup PYTHON=python3.12
.venv/bin/playwright install chromium
make check
make run
```

Open http://127.0.0.1:8765. `make check` builds the frontend before exercising it in Chromium. Python packages and npm packages have exact lockfiles. `make setup` requires package-registry access; tests themselves block live HTTP and external sockets. The optional browser installation is needed for the full browser test suite and assisted apply. The default setup includes the pinned embedded Typst compiler so PDF export works without installing a separate command-line binary.

To try synthetic jobs without live requests, click **Explore synthetic demo** in an empty workspace, or use a separate database:

```sh
FIRSTLOOK_DB=.firstlook/demo.db .venv/bin/firstlook demo
FIRSTLOOK_DB=.firstlook/demo.db .venv/bin/firstlook serve
```

Demo companies use `example.test` and are clearly labelled. They are not real opportunities. Do not crawl demo boards. Use your ordinary database for real searches. Database paths may also be absolute. Keep a copy of the SQLite file and `exports/` as your backup; stop the app before copying SQLite or use SQLite's backup API to include WAL changes.

## Choose targets, seed, verify, crawl

1. In **Settings**, set target job titles, target areas, skills, compensation floor and remote preference. Both titles and areas must be set before crawling. Use `Anywhere` for no location restriction.
2. In **Registry**, load seed candidates. Every seed is unverified. `REVIEW_REGISTRY.md` lists all 524 guesses, including domains and tokens that may be wrong or outdated.
3. Live requests begin only when you run these commands or click **Find new jobs**:

```sh
export FIRSTLOOK_CONTACT='your-contact-address'
.venv/bin/firstlook registry verify --all
.venv/bin/firstlook registry discover https://company.example/careers
.venv/bin/firstlook estimate crawl --count 524
.venv/bin/firstlook crawl --yes
```

Verification checks a supported response shape, not just HTTP status. Correct failed candidates through discovery, the Registry API, or `firstlook api PUT registry/COMPANY_ID '{"token":"correct-token","tags":["SaaS"]}'`. Successful crawling does not silently mark seeded companies verified. `--full` ignores conditional response validators. `--yes` acknowledges bulk crawling of more than 25 boards; it never permits application submission.

Adapters cover Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Recruitee and JSON-LD career pages. Fixtures are synthetic, not recordings from current production endpoints. Verification and the first real crawl are therefore required before relying on a board. Workday, iCIMS and Taleo are phase two. Unsupported forms or sites remain manual.

Requests have a global cap of four, one per host, a fixed minimum 0.5-second host delay, conditional headers and bounded jittered retries for 429/5xx. The shipped crawler is sequential (stricter than those caps); boards are ordered by staleness, posting hit rate and failures. JSON-LD crawling respects robots.txt and fails closed when permission cannot be established. No anti-bot bypass is provided. `GET /api/crawls` shows run counts, transferred bytes and duration; SQLite `crawl_result` has per-company outcomes.

## Read matches

**Jobs** shows strong matches and a deliberate might-match band. Filtered-out jobs remain available through the toolbar. Open a role to see skill overlap, missing profile skills, hard-filter reasons, extracted pay, seniority, remote policy, sponsorship and clearance language. These are deterministic extractions, not guarantees about a posting. `first_seen` is immutable. A board must omit a job on two successful crawls to close it; failures never count. Old/reposted jobs are flagged, not hidden.

Use `j`/`k` to move, Enter to open, `s` to star, `t` to tailor, `a` to review an application and `/` to search. Save search text using the plus beside Saved searches. Company category edits survive later crawls. Star/feedback/outcome labels train a local logistic regression after at least 50 distinct labelled jobs with both classes; retraining occurs as feedback grows, during indexing when a daily retrain is due, or with `firstlook retrain`. Ten percent of eligible recommendations are exploration picks by default.

Without an embedding model, the UI explicitly reports lexical matching. To opt into the under-100-MB quantized MiniLM download:

```sh
make model
.venv/bin/firstlook index
```

This explicit download contacts Hugging Face; application startup never downloads weights. `models/manifest.json` records hashes and resolved download sources. Set `FIRSTLOOK_MODEL_REVISION` to a repository revision if you need a fixed model release. If weights or runtime packages are absent, BM25 remains functional. `firstlook api GET clusters` returns local topic groups.

## Build your bank and tailor

In **Bank**, add an **identity** entry: your name as title, email/phone as organisation and contact links/location as bullets. Add roles, projects, publications, education and skills in your own wording. This identity entry lets every printed line have a bank source.

Metrics are a JSON dictionary, such as `{"latency":"35%"}`; refer to them with `{latency}` in a bullet. Metrics cannot be changed on an existing entry. To correct one, create a new source entry. Every numeric token in a rephrasing must match its source. The app does not invent experience for you.

Open **Tailor**, select a job and a classic or compact template, and build a free local variant. You can reorder/remove selected source bullets, preview manual rephrasings and accept or reject each diff. The gap report distinguishes bank skills not surfaced from requirements absent from the bank. Optional AI rephrasing also arrives as a pending diff and passes the same numerical/provenance gate.

**Render & verify PDF** compiles with an installed Typst executable or the pinned embedded Typst engine. Parse-back checks your name, contacts, titles, organisations and date ranges, and verifies one-page layout. A missing compiler leaves a `.typ` source and a visible message, never a falsely ready variant. Pending diffs, missing source IDs, altered numbers or page overflow block export. Once used on an application, the variant and its source snapshot are immutable. Create another variant to change it.

## Apply and track

1. From Job detail, choose **Review application**. Select a verified resume variant and add it to the queue.
2. **Preview form** opens a visible browser, fills supported fields and displays exact field values and attachments. Sensitive fields use only explicit profile values or `Decline to answer`. They are always highlighted. If the site has no compatible decline/empty option, set your explicit answer or apply manually.
3. Edit unanswered fields and write your own essay prose, then regenerate the preview. The local draft-answer tool returns sourced bullets, never a finished essay.
4. Review the whole diff and click **Confirm & submit**. Simple forms may be batch-confirmed after each diff is displayed. Form changes invalidate the preview. Confirmation expires after 30 minutes, is single-use and cannot be bypassed by CLI flags or chat.
5. The receipt stores field values, variant, screenshot, timestamp, confirmation state, field count, essay presence and effort minutes. If confirmation cannot be detected, the receipt says the outcome is unknown. Inspect the real page before retrying; do not blindly resubmit.

Application form fixtures cover Greenhouse, Lever and Ashby. Other visible forms use conservative generic controls; complex radio groups, custom widgets, logins and anti-bot flows may need manual completion. Hidden security tokens are not copied into receipts because credentials must not be stored. Sensitive answers are never inferred from search preferences.

Without Chromium, preview reports the manual path: open the original listing and apply using your verified resume. Update Pipeline manually afterward. Pipeline supports saved, applied, acknowledged, screen, interview, offer, rejected, ghosted and withdrawn, with notes and contacts. Logging an outcome is not a browser submission. Follow-up reminders appear for silent applications after 14 days by default; the analytics view can apply a history-derived threshold. No email or calendar access is used.

## Read analytics

Analytics includes category, size, ATS, seniority, work style, referral, resume variant (overall and within category), and lead-time buckets. Every displayed rate carries a 95% Wilson interval. Segments under the default 12-application gate show raw counts only. Comparisons are observational and described as worth noticing, with approximate extra-sample estimates in tooltips. No causal or significance claim is made. Effort return is responses per recorded hour, hidden if effort is absent or the sample is too small.

Kaplan–Meier curves estimate still waiting for a response, right-censor unanswered applications at analysis time, and never extrapolate an “ever responds” probability. Acknowledgements count as responses; record that state only when it is meaningful for your own tracking. Every analytics table has a CSV API export, including `overall` and `survival`. To record referral/effort for manual applications, use the application metadata endpoint documented in `/docs`.

## Optional providers and budgets

No API key is required. Configure a local OpenAI-compatible server first:

```sh
export FIRSTLOOK_LOCAL_URL=http://127.0.0.1:11434/v1
export FIRSTLOOK_LOCAL_MODEL=your-installed-model
```

If the configured local server is unavailable, the client can fall back to a provider you explicitly configure with `FIRSTLOOK_PROVIDER_URL` (HTTPS URL ending in `/v1`), `FIRSTLOOK_MODEL` and `FIRSTLOOK_API_KEY`. Supply keys in your shell environment or a keyring-to-environment launcher; never save them in this repository, database or `.env` files. No provider is probed until you explicitly request an AI feature.

Set daily and per-run token ceilings in Settings (defaults 20,000 and 4,000). Every inference request reserves its conservative input/output maximum in `llm_call` before sending. Cache hits spend nothing. Failed calls retain their reservation when usage is unknown. Cost cents use configured `FIRSTLOOK_INPUT_CENTS_PER_MILLION` and `FIRSTLOOK_OUTPUT_CENTS_PER_MILLION`, conservative defaults 1,000/3,000; set these to your provider's rate. They are estimates, not invoices. See `COST.md`.

The side chat supports local search, explanations, saving, tailoring and other shared tools. Prefix a question with `ask` to use an optional provider for the selected job. Chat receives structured view/job state; there is no DOM scraping and no submit tool.

## CLI and diagnostics

`firstlook --help` lists commands. The UI and CLI share the same backend. The generic `firstlook api METHOD PATH JSON` command provides API parity; `/docs` documents endpoints while the local app runs. Browser apply uses `firstlook apply APPLICATION_ID` so the preview and interactive confirmation share one session; `--answers-file` can supply your own edited prose and ordinary field values. There is deliberately no `--yes` for submission.

Examples:

```sh
.venv/bin/firstlook api GET jobs
.venv/bin/firstlook api PUT profile '{"titles":["Software Engineer"],"locations":["United States"],"must_skills":["Python"]}'
.venv/bin/firstlook bank-save my-entry.json
.venv/bin/firstlook tool tailor '{"job_id":1}'
.venv/bin/firstlook render 1
.venv/bin/firstlook tool queue_apply '{"id":1,"variant_id":1}'
.venv/bin/firstlook apply 1
.venv/bin/firstlook tool track '{"id":1,"state":"screen","notes":"Recruiter call"}'
.venv/bin/firstlook tool analytics '{}'
```

`make smoke` uses 1,000 synthetic companies, real Typst rendering and a local saved form, simulates explicit confirmation and prints analytics with an empty LLM ledger. It requires the development Typst package and Chromium, never an API key. `make dist` produces an sdist and a wheel with the compiled frontend and registry data. The full test suite rejects live HTTP transports; browsers intercept all requests with local fixtures. A fresh clone needs `make setup` before `make check`.

Only programmatic ATS endpoints and company pages permitted by robots.txt are supported. LinkedIn, Indeed, Glassdoor, prohibited scraping, telemetry, hosted deployment, accounts, autonomous submissions and inference of legal answers are excluded. Workday/iCIMS/Taleo, prose cover letters, email/calendar integrations and background job crawls remain phase two.

## Release verification

On 2026-10-14, a separate clone completed `make setup`, `make check`, `make smoke` and `make dist`. All 155 tests passed. Required package coverage: adapters 92.0%, ingestion 97.0%, extraction 100%, matching 95.0%, tailor 91.6%, analytics 100%. The 1,000-company smoke run produced a verified PDF and a confirmed saved-form receipt with zero LLM calls. The wheel was also loaded outside the source checkout to verify bundled data, static UI and health API. No live ATS data or live LLM provider was used in this validation.
