# Agent Golf MVP — spec

Source of truth for rules, scoring and the contract between the three parts. Change it only after telling all three owners.

## Goal

A student registers, solves a Hackattic problem in Pi, types `/golf-submit`, and appears on a leaderboard ranked by fewest tokens.

In scope: Pi only, Hackattic problems, the session log as the only evidence, trusted students.
Out of scope (version 2): other agents (Claude Code, Codex, OpenCode, Kilo), routing Hackattic or model calls through our server, live reporting from the plugin, our own Hackattic-style problems.

## Rules for students

One attempt = one fresh Pi session in a new, empty folder. Students may make as many attempts as they like; their best solved attempt counts.

1. Setup: the problem's model and thinking level only (shown in the problem list). No rules files, skills or extra setup.
2. Each attempt: new empty folder, new Pi session, solve from scratch. No code from earlier attempts.
3. Prompts: plain English only, no code pasted in.
4. Proof: the program must print both Hackattic's problem reply (the input) and its solve reply (right/wrong).
5. Finish: stop as soon as Hackattic says correct. Everything in the session counts, including wrong answers and dead ends.
6. Submit: `/golf-submit` in that session. Resubmitting the same session replaces the earlier copy.
7. Spot checks: unusually low scores may be asked to redo the attempt live.
8. Pass your Hackattic token with `export HACKATTIC_TOKEN=…` before starting Pi, and tell the agent to read it from that variable. Never type the token into a prompt.
9. The agent's own commands must print both Hackattic replies: the problem and the solve reply.
10. Don't run commands yourself with `!`. Only the agent's work counts.
11. No other Pi add-ons, skills or context files. Use the start command on the rules page.

## Problems

Model and thinking level are set per problem, not globally. The website keeps a small problem config in `server/`; each entry has `slug`, `title`, Hackattic URL, `instructions`, `model` (`provider/model`, or `"any"`) and `thinking_level` (a level, or `"any"`). That config is the single source for the problem list, the `unknown_problem` check, and the `agreed` setup passed to the counter, taken from the submitted problem's entry. "Solved" is one generic check (see Scoring), so adding a Hackattic problem needs only a new entry.

With `"any"`, the counter skips that match. A problem whose model is `"any"` accepts any model, and more than one in a session (GitHub Copilot Auto can change model mid-session); the board lists every model that answered. With `thinking_level` `"any"`, thinking-level changes are not flagged. Ranking stays fewest tokens across all models, and the board of a model-`"any"` problem shows each row's model.

## Scoring

Rank sessions that have no unranking reason (see [Reason codes](#reason-codes)) by fewest total tokens; ties go to fewer prompts, then fewer characters typed. Everything else is unranked, with its reasons. Warnings are shown but do not unrank.

| Metric / check | How it is read from the Pi log | Used for |
|---|---|---|
| Total tokens | Sum of `usage.totalTokens` on every assistant message, plus `usage` entries (e.g. cache warming), `compaction.usage`, `branch_summary.usage`, and any usage on tool results. Every line counts, including abandoned branches. The total is unknown (`null`, `missing_usage`) when a normal assistant reply has no usage, or the session is a fork whose earlier usage is in another file. An errored or aborted reply with no (or zero) usage, and a compaction or branch summary with no usage (optional in Pi's format), count as 0 with `usage_not_recorded`. | Rank |
| Prompts | Messages with role `user` | Tie-break 1 |
| Characters typed | Sum of Unicode code points of those user messages (CRLF/CR → LF, no trimming) | Tie-break 2 |
| Tool calls | Tool-call blocks in assistant content (confirm exact block name from `samples/`) | Shown |
| Model, thinking level | Only what actually answered: `provider`/`model` and `thinkingLevel` on assistant messages, plus `provider`/`model` on `usage` entries that name a model. `model_change` and `thinking_level_change` entries are ignored for every check (Pi logs one when a student picks a model before the first prompt). | Must match the problem's setup; `"any"` skips that part (a model-`"any"` session may use more than one model) |
| Solved | A tool result holds Hackattic's `"result": "passed"` reply for the problem's slug, or `"result": "passed (playground mode)"` for a re-solve sent with `&playground=1`. One generic check for every problem; there is no answer re-check. | Must be yes |
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
- The production origin is `https://agent-golf.csbasics.in`, configured separately from this endpoint contract. Local testing may use a configured localhost origin; no local port is mandated by the API.

This section defines key validation only; it does not define submission failure status codes or error bodies.

## Contract: problem list

`GET /api/v1/problems` (used by `/golf-problems`): public, no key, no request body. HTTP `200`, JSON:

```json
{
  "rules_version": "mvp-3",
  "rules": ["Current contest rules as plain text."],
  "problems": [
    {
      "slug": "help_me_unpack",
      "title": "Help me unpack",
      "challenge_url": "https://hackattic.com/challenges/help_me_unpack",
      "instructions": ["Public challenge constraints and required evidence."],
      "model": "provider/model",
      "thinking_level": "low"
    }
  ]
}
```

- Built from the problem config (see [Problems](#problems)); a problem is listed once its model and thinking level are set. Either may be `"any"`: show that as "any model, one per session" or "any thinking level". An empty `problems` list is valid; the plugin still shows the rules.
- `rules` mirror "Rules for students" above, and `rules_version` names that wording. `instructions` are public constraints and evidence requirements, never hints or solution code.
- Safety, kept by the website and checked by the plugin: every string is plain text and is rendered as text (no markup, terminal control or escape sequences); the body is at most 64 KB and any one string at most 1,000 characters; `challenge_url` is exactly `https://hackattic.com/challenges/<slug>` for that problem's slug.
- Browsing costs zero tokens: the plugin shows the list with Pi UI only, never through the model or the session, and sends no key and no log.
- The list is advisory; the upload checks stay authoritative. A non-200 or malformed reply means "problem list unavailable"; the plugin does not depend on error bodies.

## Contract: plugin → website

`POST /api/v1/submissions` (multipart)

- Header `Authorization: Bearer <student key>` (never in the URL)
- Field `problem`: Hackattic problem slug from the problem list, e.g. `help_me_unpack`
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
  "url": "https://agent-golf.csbasics.in/submissions/<id>"
}
```

- HTTP `200` for `ranked` and `unranked`; rejected uploads get the status shown in [Reason codes](#reason-codes) (`401`, `400` or `413`).
- These `200`, `400`, `401` and `413` responses all carry the body above. When `status` is `rejected`, `metrics` and `url` are `null`. `metrics.total_tokens` is `null` when `missing_usage` is set.
- Any other status (e.g. `500` when the counter crashes) is a server fault with an unspecified body; the plugin reports a server error, not a bad file.

## Reason codes

`reasons` uses only these codes. The counter's codes are constants in `server/counter/` and must match this table.

| Code | Set by | Effect | When |
|---|---|---|---|
| `not_solved` | counter | unranked | no `"result": "passed"` (or playground-mode pass) reply for the problem's slug |
| `model_mismatch` | counter | unranked | the models that answered (`metrics.models`) are not exactly the problem's model (not checked when it is `"any"`) |
| `thinking_level_mismatch` | counter | unranked | the assistant messages' thinking levels (`metrics.thinking_levels`) are not exactly the problem's thinking level (not checked when it is `"any"`) |
| `model_switched` | counter | unranked | no longer emitted (since `mvp-3`); kept so rows scored earlier still show a label |
| `folder_reused` | counter | unranked | the session's `cwd` is in `prior_folders` |
| `missing_usage` | counter | unranked | a normal assistant reply has no usage, or the session is a fork whose earlier usage is in another file; `total_tokens` is `null` |
| `custom_setup` | counter | warning only; stays ranked | a logged system message has context files (`project_context`), skills, an appended prompt (`addendum`), or a section an extension added; Pi's own `preamble`, `tools`, `rules`, `docs` and `cwd` do not count |
| `inconsistent_log` | counter | warning only; stays ranked | a Consistency check in Scoring fails |
| `usage_not_recorded` | counter | warning only; stays ranked | an errored or aborted reply had no (or zero) usage, or a compaction or branch summary had none (optional in Pi's format); counted as 0 |
| `bad_key` | website | rejected, HTTP 401 | missing or unknown key |
| `not_pi_log` | website | rejected, HTTP 400 | missing `session`, not UTF-8, or the counter raised `NotPiLogError` |
| `unknown_problem` | website | rejected, HTTP 400 | missing `problem`, or not in the problem config |
| `file_too_large` | website | rejected, HTTP 413 | `session` over 20 MB |

The website sets `status`: `rejected` for a website code; otherwise `unranked` if any code is marked unranked; otherwise `ranked` (warnings may still be listed).

## Contract: counter

`score(session_text: str, problem: str, agreed: dict, prior_folders: set[str]) -> dict`. Pure function: no network, no database.

- `agreed`: `{"model": "provider/model", "thinking_level": "…"}`, the problem's configured setup. Either value may be `"any"`: the counter skips that match, so model `"any"` accepts any number of models.
- `metrics.models` lists each `provider/model` that actually answered: assistant messages, plus `usage` entries that name a model. `metrics.thinking_levels` lists the `thinkingLevel` values on assistant messages. Both lists ignore `model_change` and `thinking_level_change` entries (no fallback to them for a reply without `thinkingLevel`), and the model and thinking-level checks use only these two lists.
- `prior_folders`: the `cwd` of each earlier submission by the same user. A resubmitted session leaves its own folder out (earlier copies with the same `session_id` are skipped), so resubmitting never counts as reusing a folder.
- Returns `session_id` and `cwd` from the session header, plus the `metrics` above and the counter's `reasons`:

```json
{"session_id": "…", "cwd": "…", "metrics": {"total_tokens": 0, "…": "…"}, "reasons": []}
```

- The website uses `session_id` to replace a resubmitted session and stores `cwd` for later `prior_folders`; `cwd` is never shown publicly.
- "Solved" is the generic check in Scoring for every problem: no per-problem code and no answer re-check.
- Raises `NotPiLogError`, a dedicated exception defined in `server/counter/`, when the text is not a Pi session log; the website answers `not_pi_log` for it. Any other exception from the counter is a bug, and the website returns `500`.
- The website imports `from server.counter import score, NotPiLogError, UNRANKING_REASONS, WARNING_REASONS` and sets `status` from the two sets, which must match the Reason codes table.

## Registration

Username (`[a-z0-9_]{3,32}`, unique), Hackattic username. The secret key is a random UUID shown once; only its SHA-256 is stored. No email, no password, no recovery.

## Version 2 (not today)

- Route Hackattic calls through our server and record every fetch and answer.
- Count tokens on our server by routing model calls through it (also enforces the model).
- Plugin sends a fingerprint of each reply as it happens.
- Our own Hackattic-style problems with our own checker.
- Readers for Claude Code, Codex, OpenCode, Kilo.
