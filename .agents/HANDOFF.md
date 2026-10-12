# HANDOFF

<!-- Overwrite, don't append. Keep under 60 lines. History lives in plans and git. -->

Updated: 2026-10-12 14:45 IST (Claude, merging `counter` `311ea1d` into `main` for Anup)

## Active work
- `main` now has the real counter (`server/counter/`, Amit, plan 003, up to `311ea1d`) and the redacted samples.
- Website: `feature/plan-002` (Anup/Kiro) uses the real counter (4.1 done), has `help_me_unpack` and `brute_force_zip` open, and runs on the Justuju server (104.225.219.86, container on 127.0.0.1:8077) behind a Cloudflare Tunnel being set up; the public domain is moving from justuju.in to csbasics.in.
- Plugin: `feature/plan-004` (Prateek); `agent-golf@0.1.0` is published on npm (`pi install npm:agent-golf@preview`). Left: 3.1 live end-to-end, 3.2.
- Running: nothing.

## Verified (2026-10-12)
- Counter on `main`: `Ran 22 tests … OK`; samples give the verdicts in `samples/README.md`.
- `feature/plan-002` + `counter`, with the import swapped locally (not pushed): gate `Ran 136 tests … OK`.
- Live local uploads through the website with the real counter: a solved session → ranked; wrong answer → `not_solved`; two models under "any" → `model_switched`; a `passed` reply for another challenge → `not_solved`; same folder twice → `folder_reused`; junk → 400 `not_pi_log`; no 500s.
- `custom_setup` (warning only) appears on `real-wrong-answer-redacted.jsonl` because its system message lists rules and skills.

## Decisions
- `help_me_unpack` stays model `"any"`, thinking level `"any"` for the first week (plan 001 on `feature/plan-002`).
- MVP is Pi-only; Hackattic's reply in the log is the only evidence; anti-cheat is version 2.

- `311ea1d` solved check: heredoc-written scripts, `cd` before running, and a `passed` reply followed by an error now count as solved; a pre-existing script never written in the session, a `passed` for another challenge, and a rejected answer do not (checked with constructed sessions).

## Blockers / open questions
- No real *solved* session sample yet: the samples' Hackattic commands are redacted, so the solved path is tested only with constructed logs. Anup to supply one.
- Deployment (plan 002, 5.4): host, CPU type, SSH or Anup runs commands, DNS for `agent-golf.justuju.in`, ports 80/443.
- Plan 003 still has 1.2, 2.5, 3.1, 3.2 unticked although the work is in; Amit to tick.
- GitHub Actions is blocked by an org billing lock; the local gate is the only check.

## Next action
Kiro: plan 002 step 4.1 on `feature/plan-002`, then 4.2 with Anup's solved session; then 5.4 once host details arrive.

## Read next (≤6)
1. `docs/spec.md`
2. `.agents/plans/README.md`
3. Your own plan file

## Do not (promote to AGENTS.md at next checkpoint)
- none yet
