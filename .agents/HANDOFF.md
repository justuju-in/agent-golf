# HANDOFF

<!-- Overwrite, don't append. Keep under 60 lines. History lives in plans and git. -->

Updated: 2026-10-12 (Kiro, for Anup: `fix/solved-split-url` merged into `main` at `4137eb9` and deployed; every submission re-scored)

## Active work
- Website (plan 002): done, archived at `.agents/plans/archive/002-website.md`. Since then on `main`: `fix/rescore-on-resubmit` and `fix/any-model-no-switch` (merged at `fd185d8`), and `fix/solved-split-url` (`9e9dce0`, merged at `4137eb9`).
- Live: https://agent-golf.csbasics.in, through a Cloudflare Tunnel to our shared server. The `agent-golf` container runs `main` at `4137eb9` on `127.0.0.1:8077` (same volume and env, `--no-access-log`). Deploy steps: `server/README.md`, "Live site".
- Open problems: `help_me_unpack` and `brute_force_zip`, both model "any" and thinking level "any". Model "any" allows several models in one session: `model_switched` is no longer emitted (the code stays only as a label for older rows).
- Rules: 11 rules, `rules_version` `mvp-3`, in `docs/spec.md` and `server/problems.py`. `/rules` shows the install step, the start command, a "Using GitHub Copilot" section ("Auto may change model during a session; that is fine.") and the playground note (formal wording since `9e9dce0`). The version is in `/api/v1/problems`; the page does not print it.
- Supported: GitHub Copilot Auto (via `pi-github-copilot-auto` 0.3.0) and OpenRouter models. Hackattic's `"passed (playground mode)"` counts as solved. `custom_setup` fires only for real extra setup.
- Solved check (since `9e9dce0`): a Hackattic pass in a tool result, plus one agent command or file that names `hackattic.com` and the problem's slug as a whole word, however the URL is built (base + path, f-strings, a slug variable). `help_me_unpack_extra` does not count for `help_me_unpack`.
- Resubmitting: `/golf-submit` on an unchanged session file is scored again with the current counter, and only its status, reasons and metrics change; a changed file of the same session replaces the entry, keeping its link.
- Data: live class data from Class 16 (12 Oct). Do not delete it. Every submission was re-scored with the deployed counter at 20:24 IST, after a backup in the volume (`/data/agent_golf.db.bak-20261012T145417Z`; `…T121754Z` and `…T132357Z` are from the 17:48 and 18:54 IST re-scores).
- Current verdicts (20:24 IST), all `help_me_unpack` (no `brute_force_zip` submissions yet): board #1 submission 5 (38,273 tokens), #2 submission 2 (48,857), #3 submission 7 (438,319; warning `usage_not_recorded`). Also ranked but not their player's best (5 is): 3 (103,400), 9 (74,450) and 11 (42,479); 3 and 9 carry the warning `usage_not_recorded`. Unranked: 4 (59,431; `not_solved`), 6 (45,625; `not_solved`, "passed" only in the agent's own text) and 8 (18,922; `folder_reused`, `not_solved`).
- Plugin plan 004 completed/archived at `.agents/plans/archive/004-plugin-and-deploy.md`; source pushed normally to feature/plan-004 at 50dccfb and merged into main (base f57dda0). Release source 42013d6 matches immutable npm 0.1.1; latest/preview both verified 0.1.1, csbasics.in default.
- Next plugin work: `.agents/plans/005-plugin-mvp3-follow-up.md` (created, not implemented). Change old browser "any model, one per session" to "any model", align docs/tests and stale spec display sentence in a separately approved release. Keep legacy model_switched responses. 0.1.1 already accepts ranked multi-model replies; it does not score/enforce model counts.
- Local testing ran only against disposable data; no live data/server/tunnel/deployment change. Parked review/plan-004-rebased worktree is stale, retained untouched; do not adopt/force-push it.
- Running on the server: `agent-golf` (stop with `docker stop agent-golf`) and `agent-golf-tunnel` (Cloudflare's connector; leave it alone).

## Verified (2026-10-12)
- Gate on `4137eb9` (Kiro, on Anup's machine): backend/counter `Ran 138 tests … OK`. Plugin: 97 pass, 2 skipped (they need `AGENT_GOLF_WEBSITE_DIR` / `AGENT_GOLF_E2E_WEBSITE_DIR`), 2 fail: the PTY smoke tests in `test/package.test.mjs` and `test/problem-view.test.mjs` time out waiting for Pi's extension initialization (8 s limit), also when run alone. The merge changed nothing in `plugin/`.
- Main checkpoint gate (Prateek): `AGENT_GOLF_WEBSITE_DIR=$PWD AGENT_GOLF_E2E_WEBSITE_DIR=$PWD AGENT_GOLF_E2E_PACKAGE_SOURCE=npm:agent-golf@0.1.1 bash tools/check.sh` passed backend/counter 137/137 and plugin 101/101, no skips (/tmp/golf-004-main-final-gate.log). Diff/relative-link checks and source/artifact/backend/spec preservation passed; no conflicts or force push.
- Genuine isolated preview upgrade 0.1.0 -> 0.1.1 with `pi update --extensions` preserved source/settings and verified csbasics.in default; user also confirmed update. Fresh installed latest browsed production with no override, login/model calls/session changes.
- Plan 004 step 3.1 accepted from Anup's Class 16 confirmation: npm agent-golf used throughout class, five live submissions/two ranked at his reported snapshot. This is reported production E2E evidence, not an assistant-performed solve or current aggregate count.
- After deploying `4137eb9`, through Cloudflare: `/rules` shows the new playground note, and `pi install npm:pi-github-copilot-auto@0.3.0` stays plain text (no `__cf_email__` link). Users (18) and submissions unchanged by the redeploy.
- Re-score at 20:24 IST: only submission 11 changed (unranked, `not_solved` → ranked, solved, no reasons); its agent built the solve URL from `base = 'https://hackattic.com'` and a path. Compared with the backup, no other column, user or stored log changed. Earlier re-scores: 17:48 IST cleared the old `custom_setup` and ranked 2 and 5; 18:54 IST ranked 3 once `model_switched` was dropped.
- A real solved help_me_unpack session (Pi, free OpenRouter Nemotron, one prompt) ranked on a local server at `96b61dc`: 11,466 tokens; the Hackattic token never appeared in the log. Not kept as a sample (it was the instructor's account).
- Live, through Cloudflare: `http://` gets a 301 to `https://`. A 19 MiB upload reaches the app, and 21 MiB gets the app's own 413. No keys or upload content in the app's or the connector's log.

## Decisions
- MVP is Pi-only; Hackattic's reply in the log is the only evidence; anti-cheat is version 2.
- Problems use model "any" / thinking level "any" for the first week; model "any" allows several models per session (`mvp-3`, Anup).
- An identical resubmission is re-scored, and only its verdict changes (Anup).
- A pass counts when one command or file names `hackattic.com` and the slug, however the URL is assembled (`9e9dce0`).
- The Copilot install command is wrapped in `<!--email_off-->`; Cloudflare's Email Address Obfuscation stays on for the zone (Anup).
- Hosted at csbasics.in behind a Cloudflare Tunnel, with no proxy or open ports on the shared server. Port 8000 there belongs to another app, so ours is 8077.

## Blockers / open questions
- GitHub Actions blocked by an org billing lock; the local gate is the only check.
- Plugin PTY smoke tests fail on Anup's machine (see Verified). Prateek to check whether 8 s is too short for a fresh Pi start there.
- Backup npm maintainer invitations await confirmed usernames/acceptance; follow plugin/RELEASING.md, never share tokens.
- Published 0.1.1 still has the old model-any guidance; fix next release via plan 005. No new version/tag/spec edit authorized in this merge.

## Next action
Prateek: resume plan 005 for the next-release wording/spec cleanup; obtain explicit version/channel/publication approval before npm mutation.

## Read next (≤6)
1. `docs/spec.md`
2. `.agents/plans/README.md`
3. `.agents/plans/005-plugin-mvp3-follow-up.md`
4. `.agents/plans/archive/004-plugin-and-deploy.md`
5. `plugin/RELEASING.md`
6. `server/README.md` ("Live site")

## Do not (promote to AGENTS.md at next checkpoint)
- Do not put server IPs, tokens or keys in this public repo.
- Do not touch the `agent-golf-tunnel` container, or publish the app on any port but `127.0.0.1:8077`.
