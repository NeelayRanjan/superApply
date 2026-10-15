# Prompts

Two prompts. Paste the first one to start the build. Paste the second only if the
agent comes back in a fresh session after a usage reset.

## Start

```
Build firstlook, the project specified in this repo. Read AGENTS.md and SPEC.md in
full before doing anything else, then build it end to end without asking me a
single question.

AGENTS.md is binding. Three rules matter more than the rest: never make a live
request to a job board or ATS during the build (everything is developed and tested
against the recorded fixtures in fixtures/), never write a code path that submits
an application without explicit user confirmation, and never let an LLM call
happen outside the budget ledger or over the full job corpus. The cost tiering in
SPEC.md is a correctness requirement, not a preference.

Record every decision in ASSUMPTIONS.md. One milestone at a time with a commit at
the end of each. Tests with every feature, including the degradation tests for
running with no API key, no embedding model, no Typst, and no Playwright.

Start at M0 by writing PLAN.md with a checkbox for every task in every milestone,
then work straight through M0 to M10. Keep PLAN.md ticked as you go so a fresh
session can resume from it. Do not stop, do not report back for approval, and do
not declare the build finished until every line of the Completion checklist in
SPEC.md is true.
```

## Resume

```
You are resuming an unattended build of firstlook. Do not ask me anything.

1. Read AGENTS.md, SPEC.md, PLAN.md, and ASSUMPTIONS.md in full, then run
   `git log --oneline` and `git status`.
2. If the working tree is dirty, finish or revert the in-progress change so
   `make check` passes, then commit.
3. Find the first unticked task in PLAN.md and continue from there, following
   every rule in AGENTS.md.
4. Keep going, milestone by milestone, until every item in the Completion
   checklist in SPEC.md is true. Then tag v0.1.0.
```
