# Agent Golf MVP — spec

Source of truth for rules, scoring and the contract between the three parts. Change it only after telling all three owners.

## Goal

A student registers, solves a Hackattic problem in Pi, types `/golf-submit`, and appears on a leaderboard ranked by fewest tokens.

In scope: Pi only, Hackattic problems, the session log as the only evidence, trusted students.
Out of scope (version 2): other agents (Claude Code, Codex, OpenCode, Kilo), routing Hackattic or model calls through our server, live reporting from the plugin, our own Hackattic-style problems.

## Rules for students

One attempt = one fresh Pi session in a new, empty folder. Students may make as many attempts as they like; their best solved attempt counts.

1. Setup: the agreed model and thinking level only. No rules files, skills or extra setup.
2. Each attempt: new empty folder, new Pi session, solve from scratch. No code from earlier attempts.
3. Prompts: plain English only, no code pasted in.
4. Proof: the program must print both Hackattic's problem reply (the input) and its solve reply (right/wrong).
5. Finish: stop as soon as Hackattic says correct. Everything in the session counts, including wrong answers and dead ends.
6. Submit: `/golf-submit` in that session. Resubmitting the same session replaces the earlier copy.
7. Spot checks: unusually low scores may be asked to redo the attempt live.

Open decision: model = `<TBD>`, thinking level = `<TBD>` (decided in Step 0).

## Scoring

Rank sessions that have no unranking reason (see [Reason codes](#reason-codes)) by fewest total tokens; ties go to fewer prompts, then fewer characters typed. Everything else is unranked, with its reasons. Warnings are shown but do not unrank.

| Metric / check | How it is read from the Pi log | Used for |
|---|---|---|
| Total tokens | Sum of `usage.totalTokens` on every assistant message, plus `usage` entries (e.g. cache warming), `compaction.usage`, `branch_summary.usage`, and any usage on tool results. Every line counts, including abandoned branches. | Rank |
| Prompts | Messages with role `user` | Tie-break 1 |
| Characters typed | Sum of Unicode code points of those user messages (CRLF/CR → LF, no trimming) | Tie-break 2 |
| Tool calls | Tool-call blocks in assistant content (confirm exact block name from `samples/`) | Shown |
| Model, thinking level | `provider`, `model`, `thinkingLevel` on every assistant message, plus `model_change` / `thinking_level_change` entries | All must match the agreed setup |
| Solved | Hackattic's solve reply appears in a tool result and says correct | Must be yes |
| Answer recheck | Recompute the answer from the printed problem input; it must match what was sent | Must match |
| Folder | Session `cwd` (header line) not used by an earlier submission of this user | Must be new |
| No custom setup | No extra rules files or skills in the logged system messages | Warning only |
| Consistency | Cost matches tokens; timestamps in order; `parentId` chain unbroken; input grows as the chat grows | Warning only |
| File fingerprint | SHA-256 of the uploaded file | Duplicate detection |

Field names come from https://pi.dev/docs/latest/session-format — verify against `samples/` before relying on them.

## Contract: student key validation

`GET /api/v1/me` (used by `/golf-login`; no request body)

- Header: `Authorization: Bearer <student key>` (never in the URL).
- Valid credentials: HTTP `200`, `Content-Type: application/json`, body:

```json
{"username": "<registered username>"}
```

- Missing, malformed, or invalid credentials: HTTP `401`. The error body is unspecified; the plugin must not depend on its shape or text.
- Responses include `Cache-Control: no-store`. Never echo the student key in responses or include it in logs.
- The plugin saves the supplied key only after a valid success response. Network failures and other HTTP statuses are not proof of an invalid key and must not cause the supplied key to be saved. A failed login must preserve any existing saved credentials.
- The production origin remains to be agreed and is configured separately from this endpoint contract. Local testing may use a configured localhost origin; no local port is mandated by the API.

This section defines key validation only; it does not define submission failure status codes or error bodies.

## Contract: plugin → website

`POST /api/v1/submissions` (multipart)

- Header `Authorization: Bearer <student key>` (never in the URL)
- Field `problem`: Hackattic problem slug, e.g. `help_me_unpack`
- Field `session`: the raw Pi session `.jsonl` file, unchanged
- Optional field `folder_was_empty`: `true` / `false`, recorded by the plugin at session start. The website stores it; it has no effect on ranking and no reason code.

## Contract: website → plugin

```json
{
  "status": "ranked | unranked | rejected",
  "reasons": ["model_mismatch", "not_solved"],
  "metrics": {
    "total_tokens": 0, "prompts": 0, "chars_typed": 0, "tool_calls": 0,
    "models": ["provider/model"], "thinking_levels": ["low"], "solved": true
  },
  "url": "https://agent-golf.arnav.tech/submissions/<id>"
}
```

- HTTP `200` for `ranked` and `unranked`.
- Rejected uploads: `401` `bad_key` (missing or unknown key); `400` `not_pi_log` (missing `session`, or not a Pi session log) or `unknown_problem` (missing or unknown `problem`); `413` `file_too_large` (over 20 MB).
- These `200`, `400`, `401` and `413` responses all carry the body above. When `status` is `rejected`, `metrics` and `url` are `null`.
- Any other status (e.g. `500` when the counter crashes) is a server fault with an unspecified body; the plugin reports a server error, not a bad file.

## Reason codes

`reasons` uses only these codes. The counter's codes are constants in `server/counter/` and must match this table.

| Code | Set by | Effect |
|---|---|---|
| `not_solved` | counter | unranked |
| `answer_mismatch` | counter | unranked |
| `model_mismatch` | counter | unranked |
| `thinking_level_mismatch` | counter | unranked |
| `folder_reused` | counter | unranked |
| `custom_setup` | counter | warning only; stays ranked |
| `inconsistent_log` | counter | warning only; stays ranked |
| `bad_key` | website | rejected, HTTP 401 |
| `not_pi_log` | website | rejected, HTTP 400 |
| `unknown_problem` | website | rejected, HTTP 400 |
| `file_too_large` | website | rejected, HTTP 413 |

The website sets `status`: `rejected` for a website code; otherwise `unranked` if any code is marked unranked; otherwise `ranked` (warnings may still be listed).

## Contract: counter

`score(session_text: str, problem: str, agreed: dict, prior_folders: set[str]) -> dict`. Pure function: no network, no database.

- `agreed`: `{"model": "provider/model", "thinking_level": "…"}`, the setup chosen in Step 0.
- `prior_folders`: the `cwd` of each earlier submission by the same user. A resubmitted session leaves its own folder out (earlier copies with the same `session_id` are skipped), so resubmitting never counts as reusing a folder.
- Returns `session_id` and `cwd` from the session header, plus the `metrics` above and the counter's `reasons`:

```json
{"session_id": "…", "cwd": "…", "metrics": {"total_tokens": 0, "…": "…"}, "reasons": []}
```

- The website uses `session_id` to replace a resubmitted session and stores `cwd` for later `prior_folders`; `cwd` is never shown publicly.
- Raises `NotPiLogError`, a dedicated exception defined in `server/counter/`, when the text is not a Pi session log; the website answers `not_pi_log` for it. Any other exception from the counter is a bug, and the website returns `500`.
- The website imports both as `from server.counter import score, NotPiLogError`.

## Registration

Username (`[a-z0-9_]{3,32}`, unique), Hackattic username. The secret key is a random UUID shown once; only its SHA-256 is stored. No email, no password, no recovery.

## Version 2 (not today)

- Route Hackattic calls through our server and record every fetch and answer.
- Count tokens on our server by routing model calls through it (also enforces the model).
- Plugin sends a fingerprint of each reply as it happens.
- Our own Hackattic-style problems with our own checker.
- Readers for Claude Code, Codex, OpenCode, Kilo.
