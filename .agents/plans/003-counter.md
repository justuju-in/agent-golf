---
name: 003-counter
description: Pi log reader and general counter in server/counter/ — tokens, prompts, characters, tool calls, model check, solved check.
status: created
created: 2026-10-10
updated: 2026-10-10
---

# Counter

## Progress

- [ ] **Phase 1 — Pi reader**
  - [ ] 1.1 `server/counter/pi_reader.py`: parse a Pi `.jsonl` into a common event list
  - [ ] 1.2 Tests against `samples/` added; test command added to `tools/check.sh`
- [ ] **Phase 2 — Scoring**
  - [ ] 2.1 `server/counter/score.py`: tokens, prompts, characters, tool calls
  - [ ] 2.2 Model and thinking-level check across every assistant message
  - [ ] 2.3 Solved check from Hackattic's reply in tool results
  - [ ] 2.4 Answer recheck for *Help me unpack*
  - [ ] 2.5 Folder-reuse, custom-setup and consistency checks; reasons list
- [ ] **Phase 3 — Verification and handoff**
  - [ ] 3.1 All three samples give the numbers and verdicts in `samples/README.md`
  - [ ] 3.2 Gate passes; tell the website owner the function is ready; tick this plan and add to its Changelog (`HANDOFF.md` only when merging to `main`)

## Goal

One pure function, `score(...)` as defined in `docs/spec.md`, that the website calls. Done when the three samples match their expected results.

## Context

- Field definitions: `docs/spec.md` (Scoring table) and https://pi.dev/docs/latest/session-format.
- Keep it standard-library Python, no network, no database.
- Reader + counter split: later agents (Claude Code, Codex…) only need a new reader that emits the same events.

## Architecture

```
session .jsonl ──pi_reader──▶ events [{kind: user|assistant|tool_call|tool_result|usage|model_change, ...}]
events ──score──▶ {metrics, reasons}
```

## Steps

### Phase 1 — Pi reader

#### 1.1 Reader
- Files: `server/counter/pi_reader.py`
- Do: read every line (all branches, not just the active one); header gives `cwd` and session id; keep raw usage objects; ignore unknown entry types without crashing.
- Acceptance: reading `samples/pass.jsonl` yields the expected count of user messages and assistant messages.

### Phase 2 — Scoring

#### 2.1 Metrics
- Files: `server/counter/score.py`
- Do: tokens = sum of `usage.totalTokens` on assistant messages + `usage` entries + compaction/branch-summary usage + tool-result usage; prompts = user messages; characters = code points after CRLF/CR → LF.
- Acceptance: `samples/pass.jsonl` total equals the hand count in `samples/README.md`.

#### 2.3 Solved
- Files: `server/counter/score.py`
- Do: find Hackattic's solve reply text in tool results; solved if any says correct (exact text from `samples/README.md`).
- Acceptance: pass and script → solved; fail → `not_solved` reason.

#### 2.4 Answer recheck
- Files: `server/counter/hackattic.py`
- Do: decode the printed base64 `bytes`; unpack int, uint, short, float, double (little-endian) and big-endian double; compare with the values sent.
- Acceptance: pass sample matches; editing one sent number in a copy produces `answer_mismatch`.

## Validation

- `bash tools/check.sh` passes with counter tests included.
- Every unranked sample lists at least one reason.

## Decisions

| Decision | Rationale | Rejected alternative |
|---|---|---|
| Count every branch | Wasted work still costs tokens | Active branch only |
| Use Pi's `totalTokens` per reply | Pi already normalises providers | Re-adding input/output/cache ourselves (double-count risk) |

## Changelog

- 2026-10-10 — created
