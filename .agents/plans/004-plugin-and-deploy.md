---
name: 004-plugin-and-deploy
description: Pi extension with /golf-login and /golf-submit in plugin/, then deploy the website to agent-golf.arnav.tech.
status: started
created: 2026-10-10
updated: 2026-10-10
---

# Pi plugin and going live

## Progress

- [ ] **Phase 1 — Plugin**
  - [x] 1.1 `plugin/index.ts` loads in Pi (`pi --extension ./plugin/index.ts`)
  - [ ] 1.2 `/golf-login <key>`: check with `GET /api/v1/me`, save key in a private file (mode 0600)
  - [ ] 1.3 `/golf-submit <problem>`: confirm, upload current session file, print score and link
  - [ ] 1.4 Clear messages: no key, bad key, website unreachable
  - [x] 1.5 Optional: record at session start whether the folder was empty
- [ ] **Phase 2 — Publish the plugin** (website deployment moved to plan 002, owned by Anup)
  - [ ] 2.1 Make the plugin installable with one `pi install` command (npm or GitHub; see step 2.1)
  - [ ] 2.2 Plugin points at the live site by default (`https://agent-golf.arnav.tech`), overridable for local testing
  - [ ] 2.3 `plugin/README.md`: install and update steps for students
- [ ] **Phase 3 — Verification and handoff**
  - [ ] 3.1 End-to-end from a fresh laptop: install → login → solve → submit → row on live board
  - [ ] 3.2 Gate passes; update `.agents/HANDOFF.md`

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

#### 1.3 Submit
- Files: `plugin/index.ts`
- Do: get the current session file path from the session manager; show file size and problem; `ctx.ui.confirm`; POST multipart with `Authorization: Bearer <key>`; print status, reasons, metrics, link.
- Acceptance: submitting a finished session against a local server returns the reply shape in `docs/spec.md`.

#### 1.5 Folder start observation
- Files: `plugin/index.ts`, `plugin/package.json`, `plugin/test/folder-check.test.mjs`
- Do: use `session_start`; recover existing `agent-golf-folder-check` custom entries; append at most one schema-1 observation for the current session; use `fs.promises.readdir(ctx.cwd)` with all entries counted; treat inherited/forked sessions, existing conversation without evidence, and read failures as `unknown`; keep the data in `pi.appendEntry()` custom entries excluded from model context.
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

## Decisions

| Decision | Rationale | Rejected alternative |
|---|---|---|
| Pi plugin, not a CLI | Knows the current session; student stays in Pi | Separate CLI that scans session folders |
| Start with command-only stubs | Validates loading and zero-token dispatch independently of the unavailable server | Implement unvalidated key storage or upload before API agreement |
| Folder observation is custom session metadata | `pi.appendEntry()` persists extension state outside model context and survives normal session continuation | Custom messages, external files, watchers, signatures, or upload-time rescans |
| Be conservative for inherited/forked sessions | Pi marks forks/clones with `parentSession`; copied metadata must not become a fresh-attempt certificate | Trust copied `empty` metadata in a forked session |

## Changelog

- 2026-10-10 — created
- 2026-10-10 — Prateek owns plan 004; step 1.1 implemented and approved for commit. Login API response and server-origin configuration still need agreement with the website owner.
- 2026-10-10 — Step 1.5 implemented on `feature/golf-folder-check` for later integration into `feature/plan-004`; automated plugin tests added to the gate.
