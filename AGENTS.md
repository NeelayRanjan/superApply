# Operating rules

These rules govern the whole build of `firstlook`. `SPEC.md` is the specification;
this file is how you work. Read both in full before your first action, and re-read
both after any restart or loss of context.

1. Never ask the user a question. When the spec is silent or ambiguous, decide,
   implement, and record the decision with a one-line rationale in `ASSUMPTIONS.md`.
   When something in the spec is impossible as written, implement the closest
   feasible version and record it under a "Deviations" heading in the same file.
   Never stop early for any reason other than the Completion checklist being
   fully satisfied.
2. **Never make a live request to a job board, careers page, ATS, or any third
   party during the build.** Every adapter is developed and tested against
   recorded HTTP fixtures committed to the repo. Live verification is a separate
   opt-in command the user runs afterward. A test that touches the network fails
   the build.
3. **Never auto-submit an application.** Every submission is previewed and
   confirmed by the user. This is a product requirement, not a default, and no
   configuration flag may remove it.
4. Cost discipline is a correctness property. The tiering in the Cost model
   section of `SPEC.md` is binding: no LLM call may run over the full job corpus,
   and no code path may call an LLM without going through the budget ledger.
5. Work milestone by milestone, in order. Do not start milestone N+1 until
   `make check` passes at milestone N. Commit at the end of each milestone with
   the message `M<n>: <summary>`. Commit more often if useful.
6. Keep `PLAN.md` current: one checkbox per task under each milestone, ticked as
   you go, with a "Current task" line at the top. On any restart or loss of
   context, read `AGENTS.md`, `SPEC.md`, `PLAN.md`, `ASSUMPTIONS.md`, and
   `git log --oneline` before doing anything else.
7. Every feature ships with tests. Where the spec gives an acceptance criterion,
   there is a test whose name contains that criterion. A feature without tests is
   not done.
8. The app must be useful with no API key, no local model, and no network beyond
   the ATS endpoints. Every AI-dependent feature degrades to a working
   non-AI path, and the degraded path is tested.
9. Seeded company data is never presented as verified. Registry entries you seed
   from memory carry `verified: false` and are listed in `REVIEW_REGISTRY.md` for
   the user to check with the live verification command.
10. Never store credentials in the database or in plaintext files. API keys come
    from the environment or the OS keyring. No telemetry, no analytics, no
    outbound calls other than ATS endpoints and the user's chosen LLM provider.
11. Prefer boring, widely used libraries, pinned versions, and as few dependencies
    as the job allows. Pin exact versions and commit the lockfiles.
12. Quality bar at every milestone: `ruff` and `mypy` clean, `pytest` green,
    frontend typecheck, lint, and production build green.
13. Documentation is for running the thing, not describing it. `README.md` stays a
    short pointer to `RUNBOOK.md` once that exists.
14. If a milestone is taking far longer than its neighbors, cut scope within it
    (fewer adapters, plainer UI, fewer analytics panels), note the cut in
    `ASSUMPTIONS.md`, and move on. Never cut the confirmation step, the budget
    ledger, the provenance gate, or the test suite to save time.
