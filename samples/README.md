# Sample Pi logs

Three real local sessions, heavily redacted for upload testing. Scoring is defined
in [the spec](../docs/spec.md); progress is in [the counter plan](../.agents/plans/003-counter.md).

Use `agreed={"model": "any", "thinking_level": "any"}` and `prior_folders=set()`
for the expected results below. Always pass the listed problem slug to the counter.

| File | Problem | Tokens | Prompts | Characters | Tool calls | Result |
|---|---|---:|---:|---:|---:|---|
| [real-zip-redacted.jsonl](./real-zip-redacted.jsonl) | `brute_force_zip` | 202053 | 10 | 599 | 15 | solved; ranked with `usage_not_recorded` |
| [real-second-redacted.jsonl](./real-second-redacted.jsonl) | `brute_force_zip` | 79221 | 2 | 41 | 9 | no success evidence; unranked, `not_solved` |
| [real-wrong-answer-redacted.jsonl](./real-wrong-answer-redacted.jsonl) | `help_me_unpack` | 7604 | 1 | 736 | 1 | actual rejection; unranked, `custom_setup`, `not_solved` |

The ZIP fixture covers both a real accepted answer and an AI write-and-run-script
solve. It also ranks for its exact setup: model `openai/gpt-6.1-sol`, thinking `low`.
Unused initial selections do not count. The second fixture is not a wrong-answer
attempt; it merely has no success evidence. The third fixture supplies a real
wrong-answer submission, made on 2026-10-12.

Observed accepted response:

```json
{"result": "passed"}
```

Observed rejected response (HTTP 200):

```json
{"rejected": "invalid short decoded, expected -22704 but got 0"}
```

HTTP 200 alone does not indicate a correct answer. Assistant tool-call blocks use
`type: "toolCall"`; tool results reference the call through `toolCallId`.
The wrong-answer token total can be checked directly: `3697 + 3907 = 7604`.

## Redaction and limits

User text is masked character by character with newlines preserved, so prompt
character counts remain unchanged. Assistant prose, thinking, credentials,
provider signatures, error details, private paths, and unrelated tool data are
removed or masked. Session cwd values are replaced.

The ZIP solve script (uses an environment variable rather than a literal token),
its execution command, and actual passed response are retained. The wrong-answer
fixture retains the real rejection and HTTP status, but masks its bash command,
problem input and system-section text. Nonempty system-section markers are kept,
preserving its `custom_setup` warning. Its scored metrics and reasons match the
original private log exactly. Raw original logs are not included.

These are upload fixtures, not replayable solves or proof of trace authenticity.
ZIP/second-session totals were independently summed from recorded usage rather
than manually audited entry by entry. Anup's additional solved log is still not
available here. The historical Step 0 filenames (`pass.jsonl`, `fail.jsonl`,
`script.jsonl`) are not present; the table above names the actual files.

Run `bash tools/check.sh` to check fixture metrics and counter behavior. Never
commit a real Hackattic token; any retained `access_token` values must be redacted.
