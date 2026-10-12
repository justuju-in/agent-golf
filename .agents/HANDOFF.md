# HANDOFF

<!-- Overwrite, don't append. Keep under 60 lines. History lives in plans and git. -->

Updated: 2026-10-12 (Claude, for Anup: `fix/counter-setup-playground` merged into `main` at `8eb210f` and deployed)

## Active work
- Website (plan 002): merged into `main` here, and `feature/plan-002` is moved to the same commit. Done through 5.4. Open: 4.2 (Anup's solved real session), 5.5 (no keys in the tunnel's log), Phase 6.
- Live: https://agent-golf.csbasics.in, through a Cloudflare Tunnel to our shared server. The `agent-golf` container runs `main` at `8eb210f` on `127.0.0.1:8077` (same volume and env as before). Deploy steps: `server/README.md`, "Live site".
- Open problems: `help_me_unpack` and `brute_force_zip`, both model "any" and thinking level "any".
- Rules: 11 rules (`rules_version` `mvp-2`) in `docs/spec.md` and `server/problems.py`. `/rules` shows the install step, the start command, a "Using GitHub Copilot" section (Copilot Auto; no `/compact`, no provider switch) and a playground-mode note.
- Supported: GitHub Copilot Auto (via `pi-github-copilot-auto`) and OpenRouter models. The counter accepts Hackattic's `"passed (playground mode)"` as solved.
- Data: live class data from Class 16 (12 Oct). Do not delete it. Submissions stored before `8eb210f` were scored by the old counter; a student re-running `/golf-submit` in the same session gets the new verdict.
- Plugin (plan 004): on `feature/plan-004`, npm preview published; Phase 3 (end-to-end on the live site) is open; it merges last.
- Running on the server: `agent-golf` (stop with `docker stop agent-golf`) and `agent-golf-tunnel` (Cloudflare's connector; leave it alone).

## Verified (2026-10-12)
- Gate on `8eb210f`: `Ran 134 tests … OK`, `gate: ok`.
- After deploy: `/rules` shows "Using GitHub Copilot"; `/api/v1/problems` lists both problems, `mvp-2`. Submission 5's stored log contains `"passed (playground mode)"`, so it should rank once resubmitted.
- A real solved help_me_unpack session (Pi, free OpenRouter Nemotron, one prompt) ranked on a local server at `96b61dc`: 11,466 tokens, 2 tool calls, 3 model requests; the Hackattic token never appeared in the log. Not kept as a sample (it was the instructor's account).
- Live, through Cloudflare: `/rules` shows the install and start steps; `/api/v1/problems` lists both problems with `rules_version` `mvp-2`; `http://` gets a 301 to `https://`; both boards show "No submissions yet".
- Earlier today: registration, `/api/v1/me`, `/golf-login` and `/golf-submit` work live. A 19 MiB upload reaches the app, and 21 MiB gets the app's own 413.

## Decisions
- MVP is Pi-only; Hackattic's reply in the log is the only evidence; anti-cheat is version 2.
- Problems use model "any" / thinking level "any" for the first week.
- Hosted at csbasics.in behind a Cloudflare Tunnel, with no proxy or open ports on the shared server. Port 8000 there belongs to another app, so ours is 8077.
- The rules page's start command sets `AGENT_GOLF_API_BASE_URL` to the site's own origin, and starts Pi with no other extensions, skills, context files, MCP or prompt templates.

## Blockers / open questions
- The npm plugin's default origin: the start command sets it, so students are not blocked. Prateek to confirm the default is csbasics.in.
- A redacted real solved session is still not in `samples/` (plan 002 step 4.2); one was verified live but not kept.
- GitHub Actions blocked by an org billing lock; the local gate is the only check.

## Next action
Prateek: plan 004 step 3.1, end-to-end from a fresh laptop against https://agent-golf.csbasics.in using the rules page's steps, then merge `feature/plan-004` to `main`.

## Read next (≤6)
1. `docs/spec.md`
2. `.agents/plans/README.md`
3. Your own plan file
4. `server/README.md` ("Live site")

## Do not (promote to AGENTS.md at next checkpoint)
- Do not put server IPs, tokens or keys in this public repo.
- Do not touch the `agent-golf-tunnel` container, or publish the app on any port but `127.0.0.1:8077`.
