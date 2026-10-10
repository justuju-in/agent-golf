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

Rank sessions that are solved and pass every rule check by fewest total tokens; ties go to fewer prompts, then fewer characters typed. Everything else is listed below the ranked rows as unranked, with reasons.

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
| No custom setup | No extra rules files or skills in the logged system messages | Flag |
| Consistency | Cost matches tokens; timestamps in order; `parentId` chain unbroken; input grows as the chat grows | Flag |
| File fingerprint | SHA-256 of the uploaded file | Duplicate detection |

Field names come from https://pi.dev/docs/latest/session-format — verify against `samples/` before relying on them.

## Contract: plugin → website

`POST /api/v1/submissions` (multipart)

- Header `Authorization: Bearer <student key>` (never in the URL)
- Field `problem`: Hackattic problem slug, e.g. `help_me_unpack`
- Field `session`: the raw Pi session `.jsonl` file, unchanged
- Optional field `folder_was_empty`: `true` / `false`, recorded by the plugin at session start

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

`rejected` = bad key or not a Pi log. Exact reason strings are listed in `server/counter/` and must stay in sync with this file.

## Contract: counter

`score(session_text: str, problem: str, agreed: dict, prior_folders: set[str]) -> dict` returning the `metrics` and `reasons` above. Pure function: no network, no database.

## Registration

Username (`[a-z0-9_]{3,32}`, unique), Hackattic username. The secret key is a random UUID shown once; only its SHA-256 is stored. No email, no password, no recovery.

## Version 2 (not today)

- Route Hackattic calls through our server and record every fetch and answer.
- Count tokens on our server by routing model calls through it (also enforces the model).
- Plugin sends a fingerprint of each reply as it happens.
- Our own Hackattic-style problems with our own checker.
- Readers for Claude Code, Codex, OpenCode, Kilo.
