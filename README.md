# firstlook

A local-first job search workbench: direct ATS discovery, explained matches, a provenance-backed resume bank, reviewed application assistance and outcome analytics.

**[Read RUNBOOK.md to install and use it](RUNBOOK.md).** See [COST.md](COST.md) for the enforced zero-cost discovery path and optional AI budgets, and [ASSUMPTIONS.md](ASSUMPTIONS.md) for fixture and scope decisions.

```sh
make setup PYTHON=python3.12
.venv/bin/playwright install chromium
make check
make run
```

Open `http://127.0.0.1:8765`. No API key is required. All shipped company candidates are unverified; [REVIEW_REGISTRY.md](REVIEW_REGISTRY.md) explains the explicit live verification step. Development and tests use synthetic offline fixtures; no live job board was queried during this build.
