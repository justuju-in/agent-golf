# AGENTS.md — agent-golf

<!-- Target ≤150 lines (standard A3). CLAUDE.md is `@AGENTS.md`; edit this file only. -->

Agent Golf is a leaderboard for coding-agent efficiency: students solve a Hackattic problem with the Pi coding agent, type `/golf-submit`, and are ranked by fewest total tokens (ties: fewer prompts, then fewer characters typed). This repo holds the MVP built on 2026-10-10 by Anup, Amit and Prateek: a website, a log counter, and a Pi plugin. Most tasks are done when the step's acceptance check in its plan passes and `bash tools/check.sh` is green.

## If starting fresh

Read these first, in order, and nothing else until you need it:

1. `.agents/HANDOFF.md` — team state as of the last merge to `main` (on a branch, your plan's Progress and Changelog are newer)
2. `.agents/plans/README.md` — which plan is yours (one plan per person)
3. `docs/spec.md` — the rules, scoring, and the agreed upload/reply shape
4. The folder your plan names (`server/`, `plugin/`, or `samples/`)

## Repo map

```
docs/spec.md      rules, scoring, upload/reply contract (source of truth)
server/           website + upload API + counter (Python)
server/counter/   Pi log reader + general counter (pure functions, no web code)
plugin/           Pi extension: /golf-login, /golf-submit (TypeScript)
samples/          redacted Pi session logs used as counter test fixtures
tools/check.sh    the gate
.agents/          plans, handoff, skills (.claude is a symlink to it)
```

Source of truth: `docs/spec.md` owns the rules, metric definitions, and the plugin↔website contract. `server/counter/` owns all scoring; the plugin and the web pages never compute scores themselves.

## Commands

```bash
uv venv --python 3.12                       # one-time: Python 3.12 in .venv (the gate uses it when present)
uv pip install -r server/requirements.txt   # whenever server/requirements.txt changes
bash tools/check.sh                         # the gate: runs every test suite that exists yet
```

Run the gate before every commit. When you add a component's tests, add its test command to `tools/check.sh` so one command keeps covering everything.

## Do not

- Do not compute tokens, prompts, or pass/fail in `plugin/`; it only uploads the raw session file. Scoring lives in `server/counter/` so other agents can be added later with just a new reader.
- Do not change the upload/reply shape in `docs/spec.md` without telling the other two owners; three people build against it in parallel.
- Do not commit a real Hackattic access token, a student's secret key, or a student's session log. Redact `access_token=...` in anything added to `samples/`.
- Do not store students' secret keys in plain text; store only a SHA-256 hash.
- Do not show prompts, local paths, or raw logs on public pages; only username, model, numbers and verdicts.
- Do not let `/golf-submit` call the model; submitting must cost zero tokens.
- Do not upgrade dependencies unless explicitly asked.
- Keep one writing agent per working copy. Each person works on their own branch and folder, and pulls before pushing.
- Do not edit `.agents/HANDOFF.md` on a branch. Tick your own plan and add to its Changelog instead; `HANDOFF.md` is updated only when merging to `main`.

## Plans and skills

- `001-step-0.md` is done by all three together first. Then each person owns one plan: `002-website.md`, `003-counter.md`, `004-plugin-and-deploy.md`. Tick checklists as you go; see `.agents/skills/planning/SKILL.md`.
- Skills: `planning` (create/resume plans), `session-handoff` (checkpoint and handoff).
- Before ending a session on a branch, your plan is the handoff: tick it and add to its Changelog. Only a merge to `main` updates `.agents/HANDOFF.md` (see `.agents/skills/session-handoff/SKILL.md`).

## External knowledge

- Pi session format: https://pi.dev/docs/latest/session-format · Pi extensions: https://pi.dev/docs/latest/extensions
- First Hackattic problem: https://hackattic.com/challenges/help_me_unpack
- Original design (much larger than this MVP): https://sites.arnavg.in/plans/agent-golf/
- Library/API questions: use Context7 or the official docs. Do not guess signatures. If an MCP is unavailable, say so and fall back to official docs.

## Conventions

- Commits: one completed plan step per commit, message `<area>: <what>` (e.g. `counter: sum compaction usage`). Push to your own branch; merge to `main` at checkpoints.
- Links in docs: relative markdown paths only.
- Python 3.12 (CI and Docker; locally via `uv`). Standard library first; keep `server/counter/` dependency-free so it is easy to test. Server dependencies are pinned in `server/requirements.txt`.
