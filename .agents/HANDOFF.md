# HANDOFF

<!-- Overwrite, don't append. Keep under 60 lines. History lives in plans and git. -->

Updated: 2026-10-12 (Kiro, for Anup: plan 002 done and archived; `main` at `50df42b` deployed)

## Active work
- Website (plan 002): done, archived at `.agents/plans/archive/002-website.md`, merged into `main` at `50df42b`. Nothing open; 4.2 and 5.5 are done.
- Live: https://agent-golf.csbasics.in, through a Cloudflare Tunnel to our shared server. The `agent-golf` container runs `main` at `50df42b` on `127.0.0.1:8077` (same volume and env, `--no-access-log`). Deploy steps: `server/README.md`, "Live site".
- Open problems: `help_me_unpack` and `brute_force_zip`, both model "any" and thinking level "any".
- Rules: 11 rules (`rules_version` `mvp-2`) in `docs/spec.md` and `server/problems.py`. `/rules` shows the install step, the start command, a "Using GitHub Copilot" section (Copilot Auto; no `/compact`, no provider switch) and a playground-mode note.
- Supported: GitHub Copilot Auto (via `pi-github-copilot-auto`) and OpenRouter models. The counter accepts Hackattic's `"passed (playground mode)"` as solved.
- Fixed in `8eb210f`: `custom_setup` no longer fires on every clean session; it fires only for real extra setup (context files, skills, an appended prompt, or a section an extension added).
- Data: live class data from Class 16 (12 Oct). Do not delete it. Verdicts are stored, not re-scored: submissions 2 to 6 were all scored before `8eb210f`. A re-run of `/golf-submit` is scored again only if the session file changed since its last upload; a byte-identical file gets its stored verdict back.
- Plugin (plan 004): npm `agent-golf` 0.1.1 (tags `preview` and `latest`) defaults to https://agent-golf.csbasics.in. Its source is not on `origin/feature/plan-004` yet (last push 2026-10-11). Phase 3 (end-to-end on the live site) is open; it merges last.
- Running on the server: `agent-golf` (stop with `docker stop agent-golf`) and `agent-golf-tunnel` (Cloudflare's connector; leave it alone).

## Verified (2026-10-12)
- Gate on `50df42b`: `Ran 134 tests … OK`, `gate: ok`.
- After deploying `50df42b`: `/rules` shows "Using GitHub Copilot" and the playground note; `/api/v1/problems` lists both problems, `mvp-2`; users and submissions unchanged by the redeploy.
- Submission 5 (`help_me_unpack`, stored as unranked with `custom_setup` and `not_solved`): its stored log has Hackattic's `"passed (playground mode)"` in a tool result. The new counter, run read-only on that file in the container, gives no reasons, solved, 38,273 tokens, 1 prompt.
- A real solved help_me_unpack session (Pi, free OpenRouter Nemotron, one prompt) ranked on a local server at `96b61dc`: 11,466 tokens, 2 tool calls, 3 model requests; the Hackattic token never appeared in the log. Not kept as a sample (it was the instructor's account).
- Live, through Cloudflare: `http://` gets a 301 to `https://`. Registration, `/api/v1/me`, `/golf-login` and `/golf-submit` work. A 19 MiB upload reaches the app, and 21 MiB gets the app's own 413. No keys or upload content in the app's or the connector's log.

## Decisions
- MVP is Pi-only; Hackattic's reply in the log is the only evidence; anti-cheat is version 2.
- Problems use model "any" / thinking level "any" for the first week.
- Hosted at csbasics.in behind a Cloudflare Tunnel, with no proxy or open ports on the shared server. Port 8000 there belongs to another app, so ours is 8077.
- The rules page's start command sets `AGENT_GOLF_API_BASE_URL` to the site's own origin, and starts Pi with no other extensions, skills, context files, MCP or prompt templates.

## Blockers / open questions
- Old verdicts: submissions 2 to 6 keep the old counter's verdict (submission 5 would now rank). Anup to decide: re-score them once on the server, or leave them.
- Cloudflare's Email Address Obfuscation (on by default) rewrites `pi-github-copilot-auto@0.3.0` in `/rules` as `[email protected]` in the HTML. Browsers with JavaScript decode it; curl and no-JS readers see the broken command. Fix: turn the setting off for the zone, or wrap that text in `<!--email_off-->…<!--/email_off-->` in `server/templates/rules.html`.
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
