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
