---
name: session-handoff
description: Checkpoint, decide whether to continue or restart, write .agents/HANDOFF.md, and resume safely in a fresh session. Use when a step or phase finishes, when the user says "checkpoint", "hand off", "wrap up", "resume", "where were we", when context is getting large, or before any compaction.
---

# Session handoff

Operational form of `docs/session-lifecycle.md`: budget → checkpoint → decide → hand off → resume. The state lives in two files: the active plan and `.agents/HANDOFF.md`.

## Execution modes

Supervised is the default and is always used by the daily prompts: implementation stops with an uncommitted diff for human review. Delegated mode exists only when a human names an existing plan and supplies every authorization field required by the playbook's `.agents/prompts/delegated-execution.md`; a bare “execute” request never grants it. In delegated mode, the authorization replaces only the live review pause, and the human reviews the bounded commit range before push.

## Checkpoint (every step/phase)

Checkpoint solely owns the step commit transaction in both modes. Supervised work invokes it after human approval; an explicitly authorized delegated executor invokes it after its own step-scope inspection.

1. Run `git status --short`; inspect the worktree diff and every untracked file. Confirm every path belongs to the completed step. Do not stage; stop on unrelated or ambiguous paths.
2. Tick the plan checklist; bump `updated:`/`status:`; add decisions with rationale and rejected alternative.
3. Run the gate command. On failure, restore completion ticks/status, record the exact failure, and stop without staging or committing.
4. Record the passing command + result in the plan (step `Acceptance:` or `## Validation`). "Tests pass" is not a record. This result record is the only permitted edit after the gate; rerun the gate after any other edit.
5. Stage only explicit step-owned paths with `git add --` (never `git add -A` or `git add .`). Inspect `git diff --cached --stat` and the full cached diff; stop if anything is unreviewed or unrelated.
6. Commit one step per commit. Push per the repo's AGENTS.md policy.

## Decide (first matching row wins)

| If | Then |
|---|---|
| Next step is unrelated to the recent thread | restart |
| Phase complete | restart |
| Context is large (harness shows it; or the model re-reads files it already read / forgets constraints) | checkpoint, then restart even mid-phase |
| Many big tool outputs, thread coherent, step unfinished | prune tool results (context_prune / harness equivalent), continue |
| Otherwise | continue |

Avoid `/compact`: it summarizes messages too and drops constraints. If you must, write HANDOFF.md first.

## Hand off (end of session)

On a branch, skip this section: the plan's ticks and Changelog entry, committed with the step, are the handoff. Never edit `.agents/HANDOFF.md` on a branch; it is rewritten only when merging to `main`.

Start only after checkpoint committed the human-reviewed or delegated-authorized step. `git status --short` should be clean; stop on unrelated or ambiguous changes.

Overwrite `.agents/HANDOFF.md` from `playbook/templates/HANDOFF.md`, under 60 lines:

active plan + step · branch/SHA/tree state/anything running and how to stop it · decisions with why · blockers (or "none") · exactly one next action · ≤6 read-next files in order · new "do not"s (then promote repo-specific ones to AGENTS.md).

Research repos: add the dated log entry and its one-liner in the index; point at the evidence directory, not just the log. Update `plans/README.md` only when a plan is added or archived; status lives in each plan's frontmatter. Then run the repository gate. On failure, record it and stop without committing. Record the passing command + result + time in HANDOFF; that record is the only permitted post-gate edit.

Run `git status --short` again; inspect every changed/untracked handoff-owned file. Stage only explicit file paths with `git add --` (never `git add -A`, `git add .`, or a directory pathspec), then inspect the cached stat and full cached diff. Stop on anything unreviewed or unrelated. Commit `handoff: plan NNN step N.M`, then stop; do not begin the next action. A delegated final report also shows the authorized review-range `git log` and never pushes.

## Resume (first thing in a fresh session)

1. Read `AGENTS.md` → `.agents/HANDOFF.md` → active plan → only the "Read next" files. On a branch, the plan's Progress and Changelog are newer than HANDOFF.
2. Re-run the last gate command; if the result differs, that is the first task.
3. If HANDOFF is older than the last commit, trust git + plan; fix HANDOFF only on `main`.
4. Restate the next action in one sentence and do only that step.

Account for every unfinished backlog or open item from the previous HANDOFF: carry it forward, mark it completed with evidence, or move it to a named plan path that exists. Never silently drop an item. Keep the whole handoff under 60 lines by condensing prose, not by omitting dispositions.

## Done criteria

A handoff is complete when a stranger with the repo and no chat history can: run one command and get the recorded result, name the next action, and list what not to do.
