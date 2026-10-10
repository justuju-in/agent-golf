# HANDOFF

Updated: 2026-10-10 (Prateek, plugin step 1.1)

## Active work
- Plan: `.agents/plans/004-plugin-and-deploy.md` — step 1.1 committed; next is 1.2.
- Owner: Prateek; branch: `feature/plan-004`.
- Implementation commit: `68b27d8`; working tree clean before this handoff update.
- Running: nothing; temporary smoke-test Pi processes stopped.

## Verified
- 2026-10-10 16:38 IST: `bash tools/check.sh` → `gate: ok (no component tests yet)`; no automated component suites exist yet.
- Isolated Pi RPC smoke test: extension loads, both commands registered, four usage/stub cases handled.
- No model activity; zero tokens; commands add no session entries; disposable key absent from notifications and persisted JSONL.
- `git diff --check` passed for the implementation.

## Decisions
- Command-only stubs first; no networking, credential storage, uploads, scoring, or model calls.
- Registered commands are handled before model prompts in installed Pi; do not add speculative login-command blocking.
- Omit optional empty-folder tracking until semantics are agreed.
- MVP remains Pi-only, Hackattic for correctness, raw log as evidence; plugin instead of CLI because it knows the session.

## Blockers / open questions
- Agree `/api/v1/me` auth, success body and error status, plus API-origin configuration with website owner before step 1.2.
- Website API is not implemented; use a mock for plugin development.
- Step 0 (plan 001) remains pending: competition model/thinking level TBD, three redacted logs and sample notes missing.
- Owners for plans 002 and 003 remain unset; plan 004 is assigned.
- Deployment host/ownership and student installation method need agreement before phase 2.

## Next action
Confirm the login API and server-origin contract with the website owner, then implement plan 004 step 1.2 against a mock.

## Read next
1. `.agents/plans/004-plugin-and-deploy.md`
2. `docs/spec.md`
3. `plugin/index.ts`
4. `.agents/plans/002-website.md`
5. `.agents/plans/001-step-0.md`
6. `tools/check.sh`

## Do not
- Never echo/persist keys in session entries; never compute scores or invoke the model from plugin commands.
- Do not change shared contracts without notifying the other owners.
