# HANDOFF

Updated: 2026-10-10 (Prateek, folder-check integration)

## Active work
- Plan: `.agents/plans/004-plugin-and-deploy.md` — steps 1.1 and 1.5 complete; next is 1.2.
- Owner: Prateek; branch: `feature/plan-004`.
- Folder feature: `ad814f9`; reviewed fixes: `21d43bf`; both integrated by fast-forward.
- Working tree clean before this handoff update. Folder-review worktree remains on `feature/golf-folder-check` at `21d43bf`.
- Running: nothing; temporary Pi smoke-test processes stopped.

## Verified
- 2026-10-10 20:13 IST: `bash tools/check.sh` → `gate: ok`, all 16 tests passed; `git diff --check` passed after integration.
- Plugin tests cover command stubs, empty/nonempty/hidden folders, immutable initial observations, resume/reload, prior activity, forks, read failures and session switching.
- Real CLI reopening of a bash-only JSONL yields unknown, not a fresh-folder certification.
- Isolated Pi smoke verifies custom metadata outside model context with no model calls or usage.
- Smoke uses temporary Pi config, disables MCP/discovery, drains stdout, handles spawn errors and bounds shutdown with SIGKILL fallback.

## Decisions
- Metadata uses `pi.appendEntry("agent-golf-folder-check", data)`; preserve the first valid observation.
- Before startup/new observation, allow only known initialization entries (model/thinking changes and session name); other prior activity yields unknown.
- Submit should use `getFolderWasEmptyUploadValue(header, entries)`: true/false strings for known observations; omit unknown/absent/inherited-session evidence.
- Use public Pi type exports; plugin does not compute scores or invoke the model.
- `/api/v1/me` is agreed in `docs/spec.md` (main commit `2fd07a1`): Bearer key, 200 username JSON, 401 for missing/malformed/invalid credentials.
- Anup owns website, Docker and deployment; Prateek owns plugin and publishing.

## Limitations / open questions
- Folder observation is a trusted-student signal, not tamper-proof proof of session freshness.
- Pi may keep custom-only sessions in memory until normal conversation causes the file to flush; smoke verifies session state, not disk persistence for a custom-only session.
- Production origin remains unresolved; configure it separately. Login can be built/tested against a mock without deployment.
- Website API is not implemented in this branch; failed submission HTTP/error-body details still need agreement.
- Step 0 (plan 001) remains pending: competition model/thinking level TBD, sample logs and expected notes missing.
- Plan 003 owner remains unset; student installation method still needs choosing before publishing.

## Next action
Implement plan 004 step 1.2 login and repeatable mock-API tests, reusing the existing plugin test setup.

## Read next
1. `.agents/plans/004-plugin-and-deploy.md`
2. `docs/spec.md`
3. `plugin/index.ts`
4. `plugin/test/folder-check.test.mjs`
5. `plugin/package.json`
6. `tools/check.sh`

## Do not
- Never echo/persist keys in session entries, compute scores, or invoke the model from plugin commands.
- Never certify forked/inherited sessions from copied folder metadata.
- Do not change shared contracts or ranking policy without notifying the other owners.
