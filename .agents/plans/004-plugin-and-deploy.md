---
name: 004-plugin-and-deploy
description: Pi extension with /golf-login, /golf-submit and /golf-problems in plugin/, then publish the plugin; Anup owns website deployment.
status: started
created: 2026-10-10
updated: 2026-10-11
---

# Pi plugin and going live

## Progress

- [ ] **Phase 1 — Plugin**
  - [x] 1.1 `plugin/index.ts` loads in Pi (`pi --extension ./plugin/index.ts`)
  - [x] 1.2 `/golf-login <key>`: check with `GET /api/v1/me`, save key in a private file (mode 0600)
  - [x] 1.3 `/golf-submit <problem>`: confirm, upload current session file, print score and link (aligned with the updated reply contract)
  - [ ] 1.4 Clear messages: no key, bad key, website unreachable
  - [x] 1.5 Optional: record at session start whether the folder was empty
  - [ ] 1.6 `/golf-problems`: browse public rules, problems and per-problem setup through Pi UI only
- [ ] **Phase 2 — Publish the plugin** (website deployment moved to plan 002, owned by Anup)
  - [ ] 2.1 Make the plugin installable with one `pi install` command (npm or GitHub; see step 2.1)
  - [x] 2.2 Plugin points at the live site by default (`https://agent-golf.justuju.in`), overridable for local testing
  - [ ] 2.3 `plugin/README.md`: install and update steps for students
- [ ] **Phase 3 — Verification and handoff**
  - [ ] 3.1 End-to-end from a fresh laptop: install → login → solve → submit → row on live board
  - [ ] 3.2 Gate passes; tick this plan and add to its Changelog (`HANDOFF.md` only when merging to `main`)

## Goal

A student never leaves Pi to submit. Done when `/golf-submit` from a fresh install puts a row on the live leaderboard.

## Context

- Pi extensions: https://pi.dev/docs/latest/extensions — `pi.registerCommand(name, {description, handler})`; the handler gets `ctx` with `ctx.sessionManager`, `ctx.ui.notify`, `ctx.ui.confirm`, `ctx.cwd`.
- Contract: `docs/spec.md`. The plugin sends the raw file only; it never computes scores. Feature branch rebased onto origin/main `810982a` (includes `d32ff18` plus per-problem `"any"` setup and `model_switched`); local `docs/spec.md` now matches that shared spec. Model/thinking requirements now come from each problem's config, not a global Step 0 choice.
- Never call the model from the plugin: submitting must cost zero tokens.

## Steps

### Phase 1 — Plugin

#### 1.1 Command skeleton
- Files: `plugin/index.ts`
- Do: register `/golf-login` and `/golf-submit` with usage and explicit not-implemented notifications; no networking, credential storage, session mutations, or model calls.
- Acceptance: isolated Pi RPC smoke test (`pi --mode rpc --offline --no-extensions --extension <absolute plugin/index.ts> --session <temporary JSONL>`, with MCP, skills, templates and context discovery disabled) passed: both commands registered; four usage/stub cases handled; zero tokens; no new session entries; disposable key and commands absent from persisted JSONL. Manual TUI check remains available via the command above.

#### 1.2 Login
- Files: `plugin/login.ts`, `plugin/index.ts`, `plugin/test/login.test.mjs`, `AGENTS.md`
- Do: use shared origin configuration, defaulting to `https://agent-golf.justuju.in` with an `AGENT_GOLF_API_BASE_URL` override; permit HTTPS or loopback-only HTTP origins, reject redirects; validate via the `/me` contract before atomic local credential storage; preserve existing credentials on failure; never print response bodies, keys, or raw exceptions.
- Storage: `~/.config/agent-golf/credentials.json`, directory 0700 and file 0600; keep separate credentials per canonical server origin. Server key storage remains hash-only.
- Acceptance: mock-API and isolated Pi command tests exercise successful login, failures, permissions, origin isolation, secret-free output and unchanged session/model state; `bash tools/check.sh` passes. Real-server integration remains pending.

#### 1.3 Submit
- Files: `plugin/index.ts`, `plugin/submit.ts`, `plugin/user-bash.ts`, credential reader in `plugin/login.ts`, `plugin/test/submit.test.mjs`, `plugin/test/user-bash.test.mjs`, shared `plugin/test/rpc-helper.mjs`, existing test adjustments, `plugin/README.md`
- Do: require idle Pi, no outstanding user Bash starts without recorded results, and a persisted session file; load private credentials for the configured origin; show problem, origin, file size and raw-log privacy warning; confirm via `ctx.ui.confirm`; refuse session/file changes during confirmation; POST unchanged bytes as multipart with `Authorization: Bearer <key>` and optional known folder observation; display server-provided status, reasons, metrics and link. Refuse redirects and automatic retries; distinguish server faults from rejected uploads; never echo arbitrary response bodies or secrets.
- Contract refresh: remove `answer_mismatch`; accept `missing_usage`, `usage_not_recorded` and `model_switched`. Display a null token total as unknown, never zero; validate the missing-usage/null relationship from the spec. Continue displaying the server's status without scoring or reranking locally.
- Acceptance: mock HTTP tests verify multipart fields and unchanged full-file bytes, cancellation, preflight errors, session changes, ranked/unranked/warning/rejected responses and network failures. Add regression cases for new codes, unknown totals, removed codes and malformed null/number replies. Real Pi RPC tests confirm UI cancellation/upload with unchanged session entries, file and model activity. Real-server integration remains pending.

#### 1.4 Clear errors and real login integration
- Files: `plugin/test/login.test.mjs`, `plugin/test/submit.test.mjs`, error messages in `plugin/login.ts` / `plugin/submit.ts` only if the audit identifies a gap.
- Do: verify actionable messages for absent/invalid keys and unavailable servers; preserve credentials, hide response bodies/secrets, and warn about uncertain upload delivery with no automatic retry. Test login against Anup's website branch in an isolated worktree/temporary environment; do not merge website implementation into this branch or use production credentials.
- Acceptance: mock and Pi tests assert the intended guidance; real local `/me` accepts a disposable key, rejects an invalid key, and failed login preserves the original credential file. No model calls or session secrets; repository gate passes. Website submission integration stays pending until its API exists.

#### 1.5 Folder start observation
- Files: `plugin/index.ts`, `plugin/package.json`, `plugin/test/folder-check.test.mjs`
- Do: use `session_start`; recover existing `agent-golf-folder-check` custom entries; append at most one schema-1 observation for the current session; use `fs.promises.readdir(ctx.cwd)` with all entries counted; permit only known initialization entries before observing startup/new sessions; treat inherited/forked sessions, prior activity without evidence (including bash/tool results), and read failures as `unknown`; keep the data in `pi.appendEntry()` custom entries excluded from model context.
- Acceptance: `bash tools/check.sh` passes unit coverage for empty/nonempty/hidden/later-created/resume/reload/existing/fork/read-failure/session-switch behavior, plus an isolated Pi RPC smoke test with zero model calls proving the custom entry is present in session state and absent from model context.

#### 1.6 Public problem browser
- Files: `plugin/problems.ts`, `plugin/index.ts`, `plugin/test/problems.test.mjs`, `plugin/test/rpc-helper.mjs` if needed, `plugin/README.md`.
- Do: fetch public `GET /api/v1/problems` from the shared configured origin with no key, cookie or session file; refuse redirects and use bounded requests. Validate the 64 KB body cap, 1,000-character string cap, plain-text/terminal-safety requirements, complete fields and exact `https://hackattic.com/challenges/<slug>` URLs from the contract.
- UI: show rules/version and a problem list with title, slug, challenge URL, instructions, model and thinking level. Show `"any"` as "any model, one per session" / "any thinking level". An empty catalogue still shows rules. Non-200 or malformed responses show "problem list unavailable" without using arbitrary error bodies.
- Boundaries: informational Pi UI only; no model calls, prompt insertion, persisted selection, attempt binding, automatic model/thinking changes, session entries, personalized Hackattic fetching or submission. Browsing is advisory; server upload checks remain authoritative.
- Acceptance: mock tests cover populated/empty lists, safety limits, malformed fields/URLs, redirects and network failures with no auth/log sent. Real Pi UI/RPC tests prove registration, display/cancellation and unchanged session/model activity. `bash tools/check.sh` passes; live catalogue test waits for the website endpoint.

### Phase 2 — Publish the plugin

#### 2.1 One-command install
- Files: `plugin/package.json`, and a root `package.json` only if using the GitHub route
- Do (pick one; see https://pi.dev/docs/latest/packages):
  - npm: publish the plugin as a Pi package; students run `pi install npm:<package-name>`.
  - GitHub: Pi installs a whole repo, not a subfolder, so add a root `package.json` whose `pi.extensions` points at `plugin/index.ts`; students run `pi install git:github.com/justuju-in/agent-golf`.
  - Host packages (`@earendil-works/pi-coding-agent` etc.) go in `peerDependencies` with `"*"`.
- Acceptance: on a laptop without the repo, the install command adds `/golf-login` and `/golf-submit`; `pi update --extensions` picks up a new version.

#### 2.2 Confirmed default origin
- Files: `plugin/config.ts`, `plugin/login.ts`, `plugin/submit.ts`, `plugin/test/config.test.mjs`, `plugin/README.md`
- Do: use the confirmed HTTPS origin when no override is present; preserve environment/local overrides, fail closed on invalid overrides, and never reuse or migrate another origin's credentials. No startup HTTP requests.
- Acceptance: resolver and mocked command tests prove both commands share the default/override, invalid overrides send no credentials, and changing origins does not migrate saved keys. Run the repository gate; live-server verification remains separate.

## Validation

- End-to-end test passes for all three team members.
- `bash tools/check.sh` passes.
- Step 1.1 checkpoint (2026-10-10): `bash tools/check.sh` → `gate: ok (no component tests yet)`; `git diff --check` passed. Plugin behavior was verified separately with the Pi RPC smoke test described above.
- Step 1.5 verification (2026-10-10): `bash tools/check.sh` → `gate: ok`; `git diff --check` passed. Tests verified empty fresh cwd → `empty`; hidden file → `nonempty`; files created after startup do not change the initial observation; resume/reload preserves existing metadata; existing conversation without evidence → `unknown`; forked/inherited sessions are not upload-certified; read failure → `unknown`; session switching uses per-session state; Pi RPC smoke saw one custom entry, no projected model messages, no usage entries, and no assistant messages.

- Step 1.5 review-fix checkpoint (2026-10-10): `bash tools/check.sh` → `gate: ok` with 16 tests passed, including real CLI reopening of a bash-only session as `unknown`; `git diff --check` passed.

- Step 1.2 checkpoint (2026-10-10 20:42 IST): `bash tools/check.sh` → `gate: ok`, all 26 tests passed; `git diff --check` passed. Mock API and real Pi command verified login without model activity or session secrets; real-server integration pending.

- Step 1.3 checkpoint (2026-10-10 21:23 IST): `bash tools/check.sh` → `gate: ok`, all 55 tests passed; `git diff --check` passed. Real Pi regressions refuse upload while user Bash is outstanding, then upload its recorded final output after completion. Mock multipart uploads preserve full raw bytes and folder metadata; submission adds no model activity or session mutations. Real-server integration pending.

## Decisions

| Decision | Rationale | Rejected alternative |
|---|---|---|
| Pi plugin, not a CLI | Knows the current session; student stays in Pi | Separate CLI that scans session folders |
| Start with command-only stubs | Validates loading and zero-token dispatch independently of the unavailable server | Implement unvalidated key storage or upload before API agreement |
| Folder observation is custom session metadata | `pi.appendEntry()` persists extension state outside model context and survives normal session continuation | Custom messages, external files, watchers, signatures, or upload-time rescans |
| Be conservative for inherited/forked sessions | Pi marks forks/clones with `parentSession`; copied metadata must not become a fresh-attempt certificate | Trust copied `empty` metadata in a forked session |
| Confirmed default origin with explicit override | Team confirmed https://agent-golf.justuju.in; shared resolution keeps login and submit consistent, and invalid overrides never fall back silently | Unconfirmed production host or automatically migrating credentials |
| Permission-protected local credentials, isolated per origin | Approved MVP storage lets the plugin authenticate without conflating test/live keys; server still stores only hashes | OS keychain dependency or unusable client-side hash-only storage |
| Refuse credential-validation redirects | Do not forward keys to an unexpected destination | Automatically follow server redirects |
| Confirm raw bytes and refuse changed-session uploads | User approves the exact session snapshot and destination; preserve all branches without model calls | Branch export, upload-time redaction, or uploading after the user switches sessions |
| Server owns submission results; no automatic retry | Display agreed response fields without scoring; network failures can leave delivery uncertain | Infer verdicts locally or silently retry a possibly accepted submission |
| User Bash start hashes matched to recorded results | Pi's isIdle excludes user Bash; custom markers reconstruct pending state without intercepting execution or duplicating plaintext commands; missing results fail closed | Rely only on isIdle, poll file size, or replace Bash execution |
| Public problem browsing is advisory and UI-only | Shared spec supplies per-problem rules/setup; browsing must cost zero tokens and leave attempts unchanged | Persist selections, bind attempts, insert prompts, or automatically select a model |

## Changelog

- 2026-10-10 — created
- 2026-10-10 — Prateek owns plan 004; step 1.1 implemented and approved for commit. Login API response and server-origin configuration still need agreement with the website owner.
- 2026-10-10 — Step 1.5 implemented on `feature/golf-folder-check` for later integration into `feature/plan-004`; automated plugin tests added to the gate.
- 2026-10-10 — Review fixes approved: reject prior non-initialization activity, use public Pi type exports, and isolate/harden subprocess tests. `/me` contract is agreed on main; production origin remains unresolved.
- 2026-10-10 — Step 1.2 reviewed and approved: login validates `/me` before private atomic per-origin storage; redirects refused; 26-test mock/Pi coverage. Real-server integration is pending. Writes are serialized within one Pi process only. No model calls, session secrets, or upload implementation added.
- 2026-10-10 — Rebased onto main `278dc35`, including upload HTTP/error contracts from `d412128` and updated branch-only plan status/Python gate rules. Resolved plan-index conflict by retaining main's owner-only table (Amit owns counter); login and local-storage clarification preserved. Post-integration verification: `bash tools/check.sh` → `gate: ok`, all 26 tests passed; `git diff --check` passed.
- 2026-10-10 — Step 1.3 reviewed and approved: unchanged multipart upload, explicit raw-log confirmation, private per-origin credential reading, server-owned response display, no automatic retries, and no model calls. Fixed reviewed P2 incomplete-upload issue with hashed user-Bash start markers matched to recorded results; real Pi tests cover Bash already running and started during confirmation. Missing Bash results fail closed. Real-server integration remains pending.
- 2026-10-10 — Approved metadata cleanup restores HANDOFF.md exactly to current origin/main; plan index already matches main. Historical branch-only shared-state edits are removed from the final branch diff; code unchanged. Verification (21:55 IST): `bash tools/check.sh` → `gate: ok`, 55 tests passed; `git diff --check` passed; `git diff --exit-code origin/main -- .agents/HANDOFF.md .agents/plans/README.md` passed.
- 2026-10-10 — API origin confirmed as https://agent-golf.justuju.in; default-origin implementation/docs update still pending. Counter branch dc44ac9 removes answer recheck, adds missing_usage (unknown/null total, unrank) and usage_not_recorded (warning with numeric total), and supplies two redacted fixtures. These changes are not yet in the shared spec on main; current plugin parser must be aligned after the contract lands. Observed thinkingLevel fields do not settle the official competition setup.
- 2026-10-10 — Step 2.2 reviewed and approved: shared config resolver defaults to the confirmed origin; explicit override precedence and origin validation are preserved. Five new tests cover default/override routing in both commands, fail-closed invalid overrides, and no cross-origin credential migration. README updated; real production API was not contacted. No blocking review findings. Verification (22:23 IST): `bash tools/check.sh` → `gate: ok`, 60 tests passed; `git diff --check` and shared-metadata comparison against origin/main passed.
- 2026-10-10 — Fetched final contracts: origin/main `810982a` includes `d32ff18` (unknown totals, usage codes, removed answer recheck, problem browser) plus `"any"` per-problem setup and `model_switched`. Reopened 1.3 for reply alignment and added 1.6 without renumbering. No runtime changes yet; integrate main before implementing the parser refresh. Per-problem config replaces the old global setup decision; actual listed problems/config and counter alignment still gate ranked E2E.
- 2026-10-10 — Website branch `b7f5f7a` provides a real `/api/v1/me` and local user-key CLI. Local login testing is unblocked; use an isolated website worktree and disposable credentials. `/api/v1/problems` and submission routes are not present yet. Counter branch remains `dc44ac9`; its summary-usage behavior and `"any"`/model-switch handling still need Amit's alignment to latest main.
- 2026-10-10 — Integrated main `810982a` by rebase, preserving all plugin code and the stashed contract plan. Only conflict was plan 2.2's completion checkbox: retained the approved completed status and shared justuju.in domain. Restored planning changes; HANDOFF.md and plan index still match main. Default-origin commit is now `d51758e` (previously `3df979c`); no push made.
- 2026-10-10 — Step 1.3 reply refresh reviewed and approved: new reason codes accepted, answer_mismatch removed, missing_usage/null pair validated and displayed as unknown. No token calculation or local reranking added. Mock regressions cover zero/known/unknown totals, model switches, mixed codes and malformed replies; three additional real Pi RPC cases verify display without model calls, session mutation or changed upload bytes. Pre-review verification: `bash tools/check.sh` → `gate: ok`, 71 tests passed; `git diff --check` and shared-metadata comparison against main passed. No blocking review findings; actual website submission integration still pending.
- 2026-10-11 — Step 1.3 contract-refresh checkpoint approved for commit. Review found no blocking issues; only owner plan and plugin files changed. Commit-gate verification (01:03 IST): `bash tools/check.sh` → `gate: ok`, 71 tests passed; `git diff --check` and shared-metadata comparison against origin/main passed. No live submission API test yet.
- Next: finish 1.4 error/login integration, followed by 1.6 browser implementation, then choose the publishing route. Do not update HANDOFF.md on this branch.
