---
name: 005-plugin-mvp3-follow-up
description: Align plugin guidance with mvp-3 and prepare the next separately approved npm release.
status: created
created: 2026-10-12
updated: 2026-10-12
---

# Plugin mvp-3 follow-up

Owner: Prateek. Planning only; no implementation or new publication authorized yet.

## Progress

- [ ] **Phase 1 — Guidance alignment**
  - [ ] 1.1 Change model-any detail wording to "any model"; align README/development guide and browser tests
  - [ ] 1.2 Correct the stale model-any display sentence in the shared spec; coordinate with website/counter owners
  - [ ] 1.3 Verify ranked multi-model replies remain displayed unchanged; retain legacy model_switched handling
- [ ] **Phase 2 — Verification and handoff**
  - [ ] 2.1 Run combined gate and registry/local website integration against current main
  - [ ] 2.2 Obtain explicit unused-version/channel/publication approval, then prepare/review/commit the release
  - [ ] 2.3 Publish only after publisher/MFA approval; verify exact artifact, tags, fresh install and previous-version upgrade
  - [ ] 2.4 Record results and checkpoint; update shared handoff/archive only when merging to main

## Goal

Problem guidance matches current mvp-3 rules without changing client-side scoring or upload behavior, and an explicitly approved new npm version ships the corrected text.

## Context

- [Completed plan 004](archive/004-plugin-and-deploy.md) owns 0.1.1 origin/auth/upload/privacy/packaging decisions and accepted live class evidence.
- Published agent-golf 0.1.1 (latest/preview) defaults to https://agent-golf.csbasics.in. Never overwrite it. It still displays "any model, one per session"; Anup requested "any model" for the next release.
- [Spec](../../docs/spec.md) and current counter allow several models under model "any". Production catalogue returns mvp-3. One problem-list display sentence in the spec still contradicts these rules.
- Existing plugin displays server status rather than enforcing model counts. model_switched is no longer emitted by current counter but remains a supported legacy label.
- User's current authorization closes/merges plan 004, not this plan. Suggested next patch is 0.1.2 only if unused and explicitly approved.

## Steps

### 1.1 Guidance
- Files: plugin/problems.ts, plugin/README.md, plugin/DEVELOPMENT.md, plugin/test/problems.test.mjs.
- Do: update only the model-any label and its assertions; keep thinking-level wording, dynamic rules version, safe read-only rendering and RPC fallback. Refresh public readiness wording with attributed class evidence in the next artifact, not by overwriting 0.1.1.
- Acceptance: browser tests expect "any model" and reject the old restriction; no auth, prompt, session or model mutation.

### 1.2 Shared spec
- Files: docs/spec.md.
- Do: replace the stale display sentence with already-agreed mvp-3 wording after notifying owners. Do not change upload/reply shape.
- Acceptance: rules, setup semantics and recommended displayed text agree.

### 1.3 Reply compatibility
- Files: plugin/test/submit.test.mjs; implementation only if an actual defect is found.
- Do: add/verify ranked replies containing multiple models are displayed unchanged; keep model_switched legacy-response tests.
- Acceptance: no local ranking/model enforcement; both current and legacy responses remain supported.

### 2 Verification/release
- Files: plugin/package.json, excluded release guide, tests and this plan as needed.
- Do: follow [release guide](../../plugin/RELEASING.md); use a disposable current-main website and isolated Pi settings. Confirm version and tags before external mutation. Stop for operator authentication/MFA, never share codes or weaken policy.
- Acceptance: bash tools/check.sh; both website opt-ins; exact public-file allowlist/integrity; fresh installed-package behavior and genuine channel upgrade. Record each command/result before checkpoint.

## Validation

- Guidance/spec agree with mvp-3; legacy reason compatibility retained.
- No plugin scoring, automatic setup changes or credential migration.
- No backend, dependency upgrades, production data/tunnel operations or new solve required for a wording-only change.
- Full gate and approved release verification recorded when executed.

## Decisions

| Decision | Rationale | Rejected alternative |
|---|---|---|
| Separate versioned release | 0.1.1 is immutable; Anup requested next-release wording | Rewrite 0.1.1 or mix runtime edits into its source merge |
| Keep legacy reason support | Older rows can still contain model_switched | Remove a backward-compatible response code |
| Backend owns eligibility | mvp-3 already permits multiple models | Compute or override status in plugin |

## Follow-ups

Backup npm maintainers still need confirmed trusted usernames/invitation acceptance; see private release guide. No shared credentials and no owner changes without approval. This is not a blocker for the text-only release.

## Changelog

- 2026-10-12 — Created as the named follow-up while closing/merging plan 004. Anup's request recorded; no implementation, version bump, publication or spec change performed.
