# HANDOFF

<!-- Overwrite, don't append. Keep under 60 lines. History lives in plans and git. -->

Updated: 2026-10-12 15:15 IST (Claude, for Anup, on `main`)

## Active work
- Live: https://agent-golf.csbasics.in (Cloudflare Tunnel to the Justuju server; app container on 127.0.0.1:8077). Deployed from `feature/plan-002` at `316e6f7`, which includes the real counter and Amit's `311ea1d` solved-check fix.
- Open problems: `help_me_unpack` and `brute_force_zip`, both model "any", thinking level "any".
- Plugin: `agent-golf@0.1.0` on npm still defaults to agent-golf.justuju.in; until Prateek publishes the csbasics.in default, students set `AGENT_GOLF_API_BASE_URL=https://agent-golf.csbasics.in`.
- Running: the `agent-golf` and `agent-golf-tunnel` containers on the server.

## Verified (2026-10-12)
- `feature/plan-002` gate: `Ran 132 tests … OK`; counter on `main`: 27 tests OK.
- Live: problem list, register, `/api/v1/me`, `/golf-login`, `/golf-submit` and the board all work through https://agent-golf.csbasics.in; a 19 MiB upload reaches the app, 21 MiB gets the app's own 413.
- Solved check (`311ea1d`): heredoc-written scripts, `cd` before running, and a `passed` reply followed by an error count as solved; a pre-existing script never written in the session, a `passed` for another challenge and a rejected answer do not.

## Decisions
- MVP is Pi-only; Hackattic's reply in the log is the only evidence; anti-cheat is version 2.
- Problems use model "any" / thinking level "any" for the first week.
- Domain moved from justuju.in to csbasics.in; hosted behind a Cloudflare Tunnel, not a proxy on the server.

## Blockers / open questions
- Plugin `0.1.1` with the csbasics.in default (Prateek).
- Rules page still has the install-steps placeholder and lacks the student rules (token via env var, no `!commands`, no extra Pi packages).
- `custom_setup` warning appears even for a clean Pi session (Amit to check).
- Cloudflare "Always Use HTTPS" not yet on for csbasics.in.
- `test_anup` test user and its submission are on the live board; delete before students start.
- Real solved session sample still missing (plan 002 step 4.2).
- GitHub Actions blocked by an org billing lock; the local gate is the only check.

## Next action
Kiro: rules page install steps and rules, gate, push, redeploy. Then 5.3 (merge `feature/plan-002` to `main`, updating this file).

## Read next (≤6)
1. `docs/spec.md`
2. `.agents/plans/README.md`
3. Your own plan file

## Do not (promote to AGENTS.md at next checkpoint)
- Do not put server IPs, tokens or keys in this public repo.
