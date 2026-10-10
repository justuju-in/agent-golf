---
name: planning
description: Create, resume, and execute phased plans stored as numbered markdown files in .agents/plans/. Use when the user says "make a plan", "plan this", "scope X", "break this down", "continue the plan", "execute the plan", or whenever a task touches more than one file or more than one session. Skip for one-file fixes under ~30 lines.
---

# Planning

Distilled from the planning skills in datacenter-tycoon, pi-context-prune, libfprint-eh577, cityguide and TwoFac (playbook `docs/repo-patterns.md` P-07/P-08/P-09). Plans are the memory that outlives the session; the checklist is the resume token.

## When to use / not use

- Use: multi-file, multi-session, architectural, or anything whose done-state you cannot state in one sentence.
- Don't: one obvious fix in one file (<~30 lines), or the user asked for a quick edit.
- Planning and implementing are separate turns. Do not start implementing in the same turn unless the user says "plan and execute".

## Location and naming

- `.agents/plans/NNN-kebab-slug.md`, zero-padded, sequential. Next number: `ls .agents/plans | grep -E '^[0-9]{3}-' | sort | tail -1` → +1. Never reuse or renumber; if two sessions collided, keep both and note it in `plans/README.md`.
- Multi-part plans may be a directory `NNN-slug/` with `00-overview.md` plus parts.
- Completed plans: set `status: completed` and move to `.agents/plans/archive/`. Never delete. Fix relative links when moving.
- Keep `.agents/plans/README.md` current: active list, and a "Related plan guidance" line routing future work into archived plans.

## File shape (template: `playbook/templates/plan.md`)

Frontmatter `name, description, status (created|started|completed), created, updated`. Then:

1. `## Progress` — the checklist, first thing in the body. Phases as `- [ ] **Phase N — name**` with `- [ ] N.M step` children. The last phase is always **Verification and handoff**.
2. `## Goal` — problem and one-sentence done-state.
3. `## Context` — relevant files, constraints, what is already validated, related plans.
4. `## Architecture` — only if new modules/data flow/state; mermaid welcome.
5. `## Steps` — per step: **Files**, **Do** (1–5 bullets), **Acceptance** (a command or visible behaviour).
6. `## Validation` — "complete when all of the following are true" list.
7. `## Decisions` — table: decision · rationale · rejected alternative.
8. `## Changelog`.

Step quality: concrete and observable. Bad: "work on driver". Good: "capture post-init dump while finger is held on sensor". Each step names its files.

## Execution modes

- **Supervised is the default**, including every daily resume/checkpoint/handoff flow. Implementation stops with an uncommitted diff for human review; checkpoint commits only after approval.
- **Delegated is explicit and bounded.** It exists only when the human names an existing plan and supplies every field required by the playbook's `.agents/prompts/delegated-execution.md`: authorized steps and paths, starting-tree baseline, gate, stop condition, review-range base, commit cadence, staging/review rules, and failure stops. A bare “execute the plan” is supervised and never grants commit authority.

## Executing

1. Read the whole plan first. Check `plans/README.md` for related archived plans before designing anything that touches their topic. In delegated mode, verify the named plan exists and the authorization matches its steps and paths before editing.
2. Work one step at a time. Mark it in progress in your head, do only it, and keep the evidence needed for acceptance.
3. Do not tick the step or record final acceptance during implementation in supervised mode. Implementation does not stage or commit in supervised mode: show the worktree diff and stop for human review; after approval, the checkpoint procedure in `session-handoff` owns the plan update and one-step commit (`plan NNN step N.M: …`).
4. In delegated mode, the explicit authorization replaces only the live pre-commit pause: after implementing each authorized step, invoke the same checkpoint transaction yourself. Stop rather than broaden the named plan, step, or path scope.
5. At checkpoint in either mode, verify every changed path belongs to the step, run the gate, selectively stage explicit file paths (never `git add -A`, `git add .`, or a directory pathspec), inspect the cached stat and full diff, then commit. Branch `feature/plan-NNN` first if on main and the repo uses branches.
6. Do not move to the next phase until the current one is done. If scope changes, stop; supervised work returns to the human, and delegated work requires a new authorization. If a step is too big, add a phase rather than a giant step.
7. Record blockers in the plan explicitly; never silently drop an item.
8. At phase end: checkpoint, then apply the continue/prune/restart decision (`session-handoff` skill). A delegated run stops at its authorized boundary, writes the handoff, shows the review-range `git log`, and never pushes.

## Anti-patterns

- Plans without a checklist, or checklists updated only at the end.
- Vague steps; steps without acceptance; "tests pass" without the command.
- Reusing numbers; deleting completed plans; restating docs instead of linking them.
- Starting implementation in the planning turn.
