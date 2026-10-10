---
name: 004-plugin-and-deploy
description: Pi extension with /golf-login and /golf-submit in plugin/, then publish the plugin; Anup owns website deployment.
status: started
created: 2026-10-10
updated: 2026-10-10
---

# Pi plugin and going live

## Progress

- [ ] **Phase 1 — Plugin**
  - [x] 1.1 `plugin/index.ts` loads in Pi (`pi --extension ./plugin/index.ts`)
  - [x] 1.2 `/golf-login <key>`: check with `GET /api/v1/me`, save key in a private file (mode 0600)
  - [x] 1.3 `/golf-submit <problem>`: confirm, upload current session file, print score and link
  - [ ] 1.4 Clear messages: no key, bad key, website unreachable
  - [x] 1.5 Optional: record at session start whether the folder was empty
- [ ] **Phase 2 — Publish the plugin** (website deployment moved to plan 002, owned by Anup)
  - [ ] 2.1 Make the plugin installable with one `pi install` command (npm or GitHub; see step 2.1)
  - [ ] 2.2 Plugin points at the live site by default (`https://agent-golf.justuju.in`), overridable for local testing
  - [ ] 2.3 `plugin/README.md`: install and update steps for students
- [ ] **Phase 3 — Verification and handoff**
  - [ ] 3.1 End-to-end from a fresh laptop: install → login → solve → submit → row on live board
  - [ ] 3.2 Gate passes; tick this plan and add to its Changelog (`HANDOFF.md` only when merging to `main`)

## Goal

A student never leaves Pi to submit. Done when `/golf-submit` from a fresh install puts a row on the live leaderboard.

## Context

- Pi extensions: https://pi.dev/docs/latest/extensions — `pi.registerCommand(name, {description, handler})`; the handler gets `ctx` with `ctx.sessionManager`, `ctx.ui.notify`, `ctx.ui.confirm`, `ctx.cwd`.
- Contract: `docs/spec.md`. The plugin sends the raw file only; it never computes scores.
- Never call the model from the plugin: submitting must cost zero tokens.

## Steps

### Phase 1 — Plugin

#### 1.1 Command skeleton
- Files: `plugin/index.ts`
- Do: register `/golf-login` and `/golf-submit` with usage and explicit not-implemented notifications; no networking, credential storage, session mutations, or model calls.
- Acceptance: isolated Pi RPC smoke test (`pi --mode rpc --offline --no-extensions --extension <absolute plugin/index.ts> --session <temporary JSONL>`, with MCP, skills, templates and context discovery disabled) passed: both commands registered; four usage/stub cases handled; zero tokens; no new session entries; disposable key and commands absent from persisted JSONL. Manual TUI check remains available via the command above.

#### 1.2 Login
- Files: `plugin/login.ts`, `plugin/index.ts`, `plugin/test/login.test.mjs`, `AGENTS.md`
- Do: require an explicit `AGENT_GOLF_API_BASE_URL` until the live origin is agreed; permit HTTPS or loopback-only HTTP origins, reject redirects; validate via the `/me` contract before atomic local credential storage; preserve existing credentials on failure; never print response bodies, keys, or raw exceptions.
- Storage: `~/.config/agent-golf/credentials.json`, directory 0700 and file 0600; keep separate credentials per canonical server origin. Server key storage remains hash-only.
- Acceptance: mock-API and isolated Pi command tests exercise successful login, failures, permissions, origin isolation, secret-free output and unchanged session/model state; `bash tools/check.sh` passes. Real-server integration remains pending.

#### 1.3 Submit
- Files: `plugin/index.ts`, `plugin/submit.ts`, `plugin/user-bash.ts`, credential reader in `plugin/login.ts`, `plugin/test/submit.test.mjs`, `plugin/test/user-bash.test.mjs`, shared `plugin/test/rpc-helper.mjs`, existing test adjustments, `plugin/README.md`
- Do: require idle Pi, no outstanding user Bash starts without recorded results, and a persisted session file; load private credentials for the configured origin; show problem, origin, file size and raw-log privacy warning; confirm via `ctx.ui.confirm`; refuse session/file changes during confirmation; POST unchanged bytes as multipart with `Authorization: Bearer <key>` and optional known folder observation; display server-provided status, reasons, metrics and link. Refuse redirects and automatic retries; distinguish server faults from rejected uploads; never echo arbitrary response bodies or secrets.
- Acceptance: mock HTTP tests verify multipart fields and unchanged full-file bytes, cancellation, preflight errors, session changes, ranked/unranked/warning/rejected responses and network failures. Real Pi RPC tests confirm UI cancellation/upload with unchanged session entries, file and model activity. Real-server integration remains pending.

#### 1.5 Folder start observation
- Files: `plugin/index.ts`, `plugin/package.json`, `plugin/test/folder-check.test.mjs`
- Do: use `session_start`; recover existing `agent-golf-folder-check` custom entries; append at most one schema-1 observation for the current session; use `fs.promises.readdir(ctx.cwd)` with all entries counted; permit only known initialization entries before observing startup/new sessions; treat inherited/forked sessions, prior activity without evidence (including bash/tool results), and read failures as `unknown`; keep the data in `pi.appendEntry()` custom entries excluded from model context.
- Acceptance: `bash tools/check.sh` passes unit coverage for empty/nonempty/hidden/later-created/resume/reload/existing/fork/read-failure/session-switch behavior, plus an isolated Pi RPC smoke test with zero model calls proving the custom entry is present in session state and absent from model context.

### Phase 2 — Publish the plugin

#### 2.1 One-command install
- Files: `plugin/package.json`, and a root `package.json` only if using the GitHub route
- Do (pick one; see https://pi.dev/docs/latest/packages):
  - npm: publish the plugin as a Pi package; students run `pi install npm:<package-name>`.
  - GitHub: Pi installs a whole repo, not a subfolder, so add a root `package.json` whose `pi.extensions` points at `plugin/index.ts`; students run `pi install git:github.com/justuju-in/agent-golf`.
  - Host packages (`@earendil-works/pi-coding-agent` etc.) go in `peerDependencies` with `"*"`.
- Acceptance: on a laptop without the repo, the install command adds `/golf-login` and `/golf-submit`; `pi update --extensions` picks up a new version.

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
| Explicit API origin until production address is agreed | Avoid sending credentials to an assumed host; localhost:8000 is a manual development convention | Hardcoded provisional production default |
| Permission-protected local credentials, isolated per origin | Approved MVP storage lets the plugin authenticate without conflating test/live keys; server still stores only hashes | OS keychain dependency or unusable client-side hash-only storage |
| Refuse credential-validation redirects | Do not forward keys to an unexpected destination | Automatically follow server redirects |
| Confirm raw bytes and refuse changed-session uploads | User approves the exact session snapshot and destination; preserve all branches without model calls | Branch export, upload-time redaction, or uploading after the user switches sessions |
| Server owns submission results; no automatic retry | Display agreed response fields without scoring; network failures can leave delivery uncertain | Infer verdicts locally or silently retry a possibly accepted submission |
| User Bash start hashes matched to recorded results | Pi's isIdle excludes user Bash; custom markers reconstruct pending state without intercepting execution or duplicating plaintext commands; missing results fail closed | Rely only on isIdle, poll file size, or replace Bash execution |

## Changelog

- 2026-10-10 — created
- 2026-10-10 — Prateek owns plan 004; step 1.1 implemented and approved for commit. Login API response and server-origin configuration still need agreement with the website owner.
- 2026-10-10 — Step 1.5 implemented on `feature/golf-folder-check` for later integration into `feature/plan-004`; automated plugin tests added to the gate.
- 2026-10-10 — Review fixes approved: reject prior non-initialization activity, use public Pi type exports, and isolate/harden subprocess tests. `/me` contract is agreed on main; production origin remains unresolved.
- 2026-10-10 — Step 1.2 reviewed and approved: login validates `/me` before private atomic per-origin storage; redirects refused; 26-test mock/Pi coverage. Real-server integration is pending. Writes are serialized within one Pi process only. No model calls, session secrets, or upload implementation added.
- 2026-10-10 — Rebased onto main `278dc35`, including upload HTTP/error contracts from `d412128` and updated branch-only plan status/Python gate rules. Resolved plan-index conflict by retaining main's owner-only table (Amit owns counter); login and local-storage clarification preserved. Post-integration verification: `bash tools/check.sh` → `gate: ok`, all 26 tests passed; `git diff --check` passed.
- 2026-10-10 — Step 1.3 reviewed and approved: unchanged multipart upload, explicit raw-log confirmation, private per-origin credential reading, server-owned response display, no automatic retries, and no model calls. Fixed reviewed P2 incomplete-upload issue with hashed user-Bash start markers matched to recorded results; real Pi tests cover Bash already running and started during confirmation. Missing Bash results fail closed. Real-server integration remains pending.
- Next: verify step 1.4 error-message acceptance, then choose the plugin publishing route for phase 2. Production origin remains unresolved; do not update HANDOFF.md on this branch.
