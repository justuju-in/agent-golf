# HANDOFF

Updated: 2026-10-10 (Agent Golf plugin step 1.5 on feature/golf-folder-check)

## Active work
- Plan: `.agents/plans/004-plugin-and-deploy.md` — step 1.5 implemented in this worktree for later integration into `feature/plan-004`.
- Owner: Prateek; branch: `feature/golf-folder-check`.
- Folder observation commit: `ad814f9` (rebased onto current `feature/plan-004`).
- Review fixes approved for checkpoint and integration; see the plan changelog.
- Running: nothing; temporary Pi smoke-test processes are stopped.

## Verified
- 2026-10-10: `bash tools/check.sh` → `gate: ok`.
- 2026-10-10: `git diff --check` passed.
- Automated plugin tests cover:
  - command stubs still register and return the existing usage/not-implemented messages
  - empty fresh directory → schema-1 `empty`
  - hidden file in cwd → `nonempty`
  - files created after startup do not change the initial observation
  - resume/reload preserves an existing observation and does not append another
  - existing conversation without evidence → `unknown` with `not-fresh:<reason>`
  - forked/inherited sessions → `unknown` / no future upload certification, even if copied metadata says `empty`
  - filesystem read failure → `unknown` with `read-failed...`
  - session switching uses the current session only, not cached global state
- Review-fix run: `bash tools/check.sh` passed all 16 tests; `git diff --check` passed. Added prior bash/tool/usage/compaction/custom activity regressions and real CLI reopening of a bash-only JSONL.
- Pi smoke uses temporary config, disables MCP/discovery, drains stdout, handles spawn errors and force-kills stalled shutdown. Fresh sessions have one observation with zero projected messages; reopened bash-only sessions yield unknown. Neither run invokes the model.

## Decisions
- Use `session_start`, but do not trust the hook alone as freshness: Pi uses it for startup, reload, resume, new, and fork. Check reason, `parentSession`, and allow only known initialization entries before observing cwd.
- Store metadata via `pi.appendEntry("agent-golf-folder-check", data)` as a custom entry excluded from model context.
- Never overwrite an existing valid observation in the current session.
- Fresh observation permits only startup/new sessions with no `parentSession` and only known initialization entries (model/thinking changes, session name). Any other prior activity, including bash/tool results, yields `unknown` without inspecting cwd.
- Future submit code should use `getFolderWasEmptyUploadValue(header, entries)`: returns `"true"` for `empty`, `"false"` for `nonempty`, and omits for `unknown`/absent/`parentSession`.

## Limitations / open questions
- This is a trusted-student MVP signal, not tamper-proof evidence; session JSONL can be edited by a user.
- Pi does not flush custom-only sessions to disk until a conversation entry exists, so the smoke test verifies session-state persistence and model-context exclusion with zero model calls; normal attempts will persist the entry when the first user/assistant message causes the session file to flush.
- `/api/v1/me` is agreed in `docs/spec.md` on main (`2fd07a1`), included in both rebased feature branches: Bearer key, 200 username JSON, 401 for missing/malformed/invalid credentials. Production origin remains unresolved.
- Anup owns website, Docker and deployment (plan 002); Prateek owns plugin and publishing (plan 004).
- Website API is not implemented; use a mock for future plugin upload development.
- Step 0 (plan 001) remains pending: competition model/thinking level TBD, three redacted logs and sample notes missing.

## Next action
Fast-forward the approved folder-check checkpoint into `feature/plan-004`, then refresh the handoff before login against a mock API.

## Read next
1. `.agents/plans/004-plugin-and-deploy.md`
2. `plugin/index.ts`
3. `plugin/test/folder-check.test.mjs`
4. `docs/spec.md`
5. `tools/check.sh`

## Do not
- Never echo/persist keys in session entries; never compute scores or invoke the model from plugin commands.
- Do not change shared upload contracts or ranking policy without notifying the other owners.
- Do not treat forked/inherited sessions as fresh attempts even if they contain copied `empty` metadata.
