# firstlook

A local-first job search workbench. It finds openings on company applicant
tracking systems, where they usually appear days before any aggregator picks them
up; matches them against your profile, including a deliberate band of maybes;
tailors a resume per job from a structured experience bank where every line traces
back to something you actually did; fills and previews the application form for
one-click assisted submission; and tracks what happened, so after fifty
applications you can see which resume variants, categories, and timings actually
produce replies.

Everything runs locally against a SQLite file. No account, no server, no
telemetry. It works with no API key and no local model, and it is built so that AI
spend scales with the jobs you touch rather than the jobs it ingests, because this
repo is meant to be handed to other people without burning their subscriptions.

This repo currently holds the specification only. The code is built by an agent
from the prompts below.

## Files

- `SPEC.md` — the specification: cost model, ATS adapters and the company
  registry, ingestion, extraction, matching, the experience bank and live tailor,
  assisted apply, tracker and analytics, UI and side chat, milestones, tests,
  legal constraints, completion checklist.
- `AGENTS.md` — operating rules for the agent (read automatically by Codex and
  Claude Code).
- `PROMPT.md` — the prompt to paste to start the build, and the one to paste if a
  fresh session has to resume it.

## Building it

1. Clone this repo and open it in Codex (or Claude Code) with the most autonomous
   approval mode available and network access for package installs. Nothing in the
   spec needs an API key, an account, or a paid service, and nothing in the build
   touches a live job board.
2. Paste the Start prompt from `PROMPT.md`.
3. When the usage cap hits, press reset and let it continue. If the same session
   resumes, do nothing. If you land in a new session, paste the Resume prompt.

Milestones are ordered so an interrupted run still leaves something useful: the
registry, adapters, extraction, matching, and the jobs UI come before the tailor,
assisted apply, and analytics.

## After the build

1. Set your target titles and areas, then run `firstlook registry verify --all`.
   The shipped company list is seeded from the model's memory and is marked
   unverified on purpose; this command checks every entry against its real board.
   `REVIEW_REGISTRY.md` lists what needs checking.
2. Add the companies you care about with `firstlook registry discover <careers
   url>`, which works out which ATS they use.
3. Run the first crawl, then fill in your experience bank. The bank is the thing
   that makes the tailor useful, and it is the one part nobody can do for you.
4. Optional: install Ollama or another local OpenAI-compatible server for the
   tailor and chat, or add a hosted API key. Without either, matching and the rest
   of the app still work.
5. Apply to things. The analytics only start paying off at around fifty
   applications, and they will tell you when a number is still too thin to mean
   anything.

`RUNBOOK.md` and `COST.md` cover the details once the build has produced them.
