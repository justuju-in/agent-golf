# samples

Redacted Pi session logs from Step 0 ([plan 001](../.agents/plans/001-step-0.md)). Replace every Hackattic `access_token` value with `REDACTED` before committing; the gate fails otherwise.

| File | How it was made | Expected |
|---|---|---|
| `pass.jsonl` | AI solves normally | solved; total tokens = `<hand count>` |
| `fail.jsonl` | AI sends one wrong number | not solved |
| `script.jsonl` | AI writes and runs a fetch-and-solve program | solved |

Hackattic "correct" reply looks like: `<fill in>`
Hackattic "wrong" reply looks like: `<fill in>`
Tool-call block name in assistant content: `<fill in>`

## Counter review fixtures (2026-10-10)

Two real local sessions, heavily redacted for upload testing. These are not the
three planned Step 0 pass/fail/script fixtures. User text is masked character by
character (newlines preserved), preserving prompt character counts. Assistant prose,
reasoning, system sections, unrelated tool arguments/results, provider signatures,
error details and context replacements are removed/masked. Session cwd is replaced.
The ZIP solve script (uses an environment variable, no literal key), its execution
command, and actual passed response are retained. Redaction means setup warnings
may differ from the originals; these files cannot reproduce the full solve.

| File | Tokens | Prompts | Characters | Tool calls | Solved for brute_force_zip |
|---|---:|---:|---:|---:|---|
| [real-zip-redacted.jsonl](./real-zip-redacted.jsonl) | 202053 | 10 | 599 | 15 | yes |
| [real-second-redacted.jsonl](./real-second-redacted.jsonl) | 79221 | 2 | 41 | 9 | no evidence |

The ZIP fixture has `usage_not_recorded` (errored zero-usage reply). With model
`openai/gpt-6.1-sol` / level `low`, or `any` / `any`, it ranks with that warning.
Its reported model is only `openai/gpt-6.1-sol`, and thinking level only `low`;
unused initial selection events do not count. The second fixture has no success
evidence and stays unranked (`not_solved`), including with `any` / `any`.
Observed correct response: `{"result":"passed"}`; assistant tool block: `toolCall`.
A real wrong-answer response is still unavailable. Totals are independently summed
from recorded usage, not manually audited across every entry.

## Remaining real evidence

The ZIP fixture supplies both an actual pass and a write-and-run-script example.
The second fixture supplies an upload without success evidence, not a genuine
Hackattic wrong-answer attempt. No real wrong-answer response is available in the
two local source logs. Anup's promised solved log has not been supplied here yet.
Do not relabel synthetic outputs as real accepted/failed Hackattic responses.
