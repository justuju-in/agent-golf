---
name: 005-plugin-mvp3-follow-up
description: Align plugin guidance with mvp-3 and prepare the next separately approved npm release.
status: started
created: 2026-10-12
updated: 2026-10-14
---

# Plugin mvp-3 follow-up

Owner: Prateek. The release goal is already delivered by main dd1786c and published 0.1.2. Reconciliation reviewed and approved for a branch-only checkpoint; no main merge, Git push, PR creation or npm mutation is authorized.

## Progress

- [ ] **Phase 3 — Reconciliation verification and handoff**
  - [x] 3.1 Retain unique regression tests and reconcile release/verification evidence; supervised review accepted
  - [ ] 3.2 Obtain approval to push this branch and open a PR for Anup
  - [ ] 3.3 At approved main integration, archive the plan and update shared handoff/index/links with explicit verification limitations

## Reconciliation record (2026-10-14)

- Main includes release source 369c6f2, the Windows credential fix and corrected browser/spec wording. Preserve that release; do not merge the old feature/plan-005 branch wholesale or republish 0.1.2.
- Original feature/plan-005 remains at 7866f54 with its uncommitted step 2.1 evidence intact. Its accepted local checkpoints were 183f3c9 (guidance), 9dee618 (spec) and 7866f54 (reply tests). This review branch ports only the two additional ranked multi-model regression tests, retaining legacy model_switched coverage.
- Original checklist below is historical planning, not a claim that all checks were performed. Reconciliation review accepted; closure/archive disposition awaits main integration. Do not delete the plan or tick unperformed release/upgrade work.
- When main integration is authorized: mark this plan completed with the release/reconciliation evidence and explicit verification limitations; move it to archive; update relative links, the shared index and HANDOFF.md. Those main-only changes are deliberately not applied on this branch.
- Remaining verification: genuine isolated 0.1.1 -> 0.1.2 channel upgrade and actual Windows-machine validation have not been performed here. Windows cases in the gate simulate platform-specific permission behavior. Carry these limitations into the archived plan/release guide rather than claiming acceptance.

## Original progress (superseded release route)

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
- Published agent-golf 0.1.2 is now latest/preview, defaults to https://agent-golf.csbasics.in and displays "any model". Never overwrite published versions. No new release is needed for this reconciliation.
- [Spec](../../docs/spec.md) and current counter allow several models under model "any". Production catalogue returns mvp-3. Main's spec display recommendation now matches those rules.
- Existing plugin displays server status rather than enforcing model counts. model_switched is no longer emitted by current counter but remains a supported legacy label.
- User authorized preparing reconciliation while explicitly forbidding main merges for now. Publication/version preparation has been superseded by the independently merged 0.1.2 release. Anup's npm owner access is verified; Amit's confirmed npm username/access remains pending.

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

### 3 Reconciliation verification and handoff
- 3.1 Files: plugin/test/submit.test.mjs, plugin/RELEASING.md and this plan. Retain the two unique ranked multi-model tests, preserve current main runtime, record installed-package/TUI/artifact evidence and limitations. Acceptance: full gate with TUI and both website opt-ins, unchanged public artifact, reviewed scoped diff and branch checkpoint.
- 3.2 No source changes required: obtain explicit push/PR approval, push the reconciliation branch normally, open a PR targeting main and share its link with Anup. No automatic main merge.
- 3.3 Files at approved main integration only: archived plan, shared plans index, HANDOFF.md and guides with affected relative links. Archive rather than delete; record externally delivered/superseded work and unperformed upgrade/actual-Windows checks honestly.

## Validation

- Guidance/spec agree with mvp-3; legacy reason compatibility retained.
- No plugin scoring, automatic setup changes or credential migration.
- No backend, dependency upgrades, production data/tunnel operations or new solve required for a wording-only change.
- Full gate and approved release verification recorded when executed.
- Reconciliation verification (2026-10-14 09:35 IST, subsequently reviewed and accepted): backend source dd1786c; `AGENT_GOLF_TUI_TESTS=1 AGENT_GOLF_WEBSITE_DIR=$PWD AGENT_GOLF_E2E_WEBSITE_DIR=$PWD bash tools/check.sh` in /tmp/agent-golf-plan005-reconciliation passed 138 backend/counter + 106 plugin tests, no skips, with AGENT_GOLF_E2E_PACKAGE_SOURCE unset (local artifact) and with AGENT_GOLF_E2E_PACKAGE_SOURCE=npm:agent-golf@0.1.2 (registry-installed integration). Both TUI smoke checks were enabled. Logs: /tmp/golf-005-reconcile-local-gate.log and /tmp/golf-005-reconcile-registry-gate.log. These are transport/privacy/compatibility checks, not a fresh Hackattic solve.
- Exact ten-file local public artifact matches downloaded registry 0.1.2 SHA-1/SHA-512: shasum 19b4dd253cd9102afdfc927e5254000d4a27a9d1, integrity sha512-ljq5m75Ws6fmQB3Yfqyy2cQ2014+JHuWWsz39g9IMZ48z+WdfNCAVTNmLZOk/+3Uwtb6mxb/os5ZDuOcSrJheg==. Tests/private-guide/plan changes do not alter shipped bytes. Temporary keys/data/Pi settings removed and servers stopped by the harness; no production operations or user-installed plugin/auth changes.

- Step 3.1 commit gate (2026-10-14 15:49 IST): in the reconciliation worktree, `AGENT_GOLF_TUI_TESTS=1 AGENT_GOLF_WEBSITE_DIR=$PWD AGENT_GOLF_E2E_WEBSITE_DIR=$PWD AGENT_GOLF_E2E_PACKAGE_SOURCE=npm:agent-golf@0.1.2 bash tools/check.sh` → gate ok; 138 backend/counter + 106 plugin tests passed, no skips. `git diff --check` passed. Log: /tmp/golf-005-reconcile-commit-gate.log. Temporary test services/data/settings cleaned up; local venv symlink removed. No shared main metadata or public artifact changes.

## Decisions

| Decision | Rationale | Rejected alternative |
|---|---|---|
| Separate versioned release | 0.1.1 is immutable; Anup requested next-release wording | Rewrite 0.1.1 or mix runtime edits into its source merge |
| Keep legacy reason support | Older rows can still contain model_switched | Remove a backward-compatible response code |
| Backend owns eligibility | mvp-3 already permits multiple models | Compute or override status in plugin |

## Follow-ups

Anup is now a verified npm owner alongside prateek-justuju. Amit still needs a confirmed trusted username/invitation acceptance; see private release guide. No shared credentials and no owner changes without approval. This is not a blocker for the text-only release.

## Changelog

- 2026-10-12 — Created as the named follow-up while closing/merging plan 004. Anup's request recorded; no implementation, version bump, publication or spec change performed.
- 2026-10-14 — Release goal already fulfilled on main by dd1786c/369c6f2 and npm 0.1.2. User authorized branch-only reconciliation, not a main merge. Prepared review/plan-005-reconciliation from latest main; retained two unique regression tests and recorded fully enabled local/registry integration and artifact evidence. Original branch/evidence and parked rebase remain untouched. Review, archive/main metadata update and any commit/push remain separate authorizations.
- 2026-10-14 — Step 3.1 reconciliation reviewed with no blocking issues and approved for commit. Remote main still dd1786c. Checkpoint scope is plugin/test/submit.test.mjs, plugin/RELEASING.md and this plan only. Published runtime/artifact, Windows fix, backend and shared handoff/index unchanged. No push, PR creation, main merge or npm mutation authorized; next action is request approval for step 3.2.
