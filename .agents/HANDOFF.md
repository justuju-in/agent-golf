# HANDOFF

Updated: 2026-10-10 (Agent Golf plugin step 1.5 on feature/golf-folder-check)

## Active work
- Plan: `.agents/plans/004-plugin-and-deploy.md` — step 1.5 implemented in this worktree for later integration into `feature/plan-004`.
- Owner: Prateek; branch: `feature/golf-folder-check`.
- Implementation commit: this checkpoint commit (`plan 004 step 1.5: record folder observation`).
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
- Isolated Pi RPC smoke test starts Pi with the plugin and a probe extension, makes zero model calls, and verifies one `agent-golf-folder-check` custom entry exists in session state while `buildSessionProjection().messages` has zero model-context messages, zero usage entries, and zero assistant messages.

## Decisions
- Use `session_start`, but do not trust the hook alone as freshness: Pi uses it for startup, reload, resume, new, and fork. The implementation checks event reason, session header `parentSession`, and whether the current session already contains user/assistant conversation entries.
- Store metadata via `pi.appendEntry("agent-golf-folder-check", data)` as a custom entry excluded from model context.
- Never overwrite an existing valid observation in the current session.
- Fresh certification is conservative: only startup/new sessions with no user/assistant conversation and no `parentSession` inspect `ctx.cwd`; forked/inherited sessions and existing conversations without evidence record `unknown`.
- Future submit code should use `getFolderWasEmptyUploadValue(header, entries)`: returns `"true"` for `empty`, `"false"` for `nonempty`, and omits for `unknown`/absent/`parentSession`.

## Limitations / open questions
- This is a trusted-student MVP signal, not tamper-proof evidence; session JSONL can be edited by a user.
- Pi does not flush custom-only sessions to disk until a conversation entry exists, so the smoke test verifies session-state persistence and model-context exclusion with zero model calls; normal attempts will persist the entry when the first user/assistant message causes the session file to flush.
- Step 1.2 login API and server-origin contract are still pending with the website owner.
- Website API is not implemented; use a mock for future plugin upload development.
- Step 0 (plan 001) remains pending: competition model/thinking level TBD, three redacted logs and sample notes missing.

## Next action
Push/review this step 1.5 checkpoint, then integrate/cherry-pick into `feature/plan-004` if desired. After that, return to step 1.2 once the login API contract is agreed.

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
