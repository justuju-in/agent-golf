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

The ZIP fixture has `usage_not_recorded` (errored zero-usage reply). Both may be
unranked for setup mismatch depending on the configured agreed model/level.
Observed correct response: `{"result":"passed"}`; assistant tool block: `toolCall`.
A real wrong-answer response is still unavailable. Totals are independently summed
from recorded usage, not manually audited across every entry.
