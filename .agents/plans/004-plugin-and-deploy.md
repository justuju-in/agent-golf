---
name: 004-plugin-and-deploy
description: Pi extension with /golf-login and /golf-submit in plugin/, then deploy the website to agent-golf.arnav.tech.
status: created
created: 2026-10-10
updated: 2026-10-10
---

# Pi plugin and going live

## Progress

- [ ] **Phase 1 — Plugin**
  - [ ] 1.1 `plugin/index.ts` loads in Pi (`pi --extension ./plugin/index.ts`)
  - [ ] 1.2 `/golf-login <key>`: check with `GET /api/v1/me`, save key in a private file (mode 0600)
  - [ ] 1.3 `/golf-submit <problem>`: confirm, upload current session file, print score and link
  - [ ] 1.4 Clear messages: no key, bad key, website unreachable
  - [ ] 1.5 Optional: record at session start whether the folder was empty
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

#### 1.3 Submit
- Files: `plugin/index.ts`
- Do: get the current session file path from the session manager; show file size and problem; `ctx.ui.confirm`; POST multipart with `Authorization: Bearer <key>`; print status, reasons, metrics, link.
- Acceptance: submitting a finished session against a local server returns the reply shape in `docs/spec.md`.

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

## Decisions

| Decision | Rationale | Rejected alternative |
|---|---|---|
| Pi plugin, not a CLI | Knows the current session; student stays in Pi | Separate CLI that scans session folders |

## Changelog

- 2026-10-10 — created
