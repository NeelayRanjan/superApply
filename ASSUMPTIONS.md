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
