# Counter

Pure standard-library Python; never executes code, accesses the network, or stores logs.

```python
from server.counter import score, NotPiLogError, UNRANKING_REASONS

result = score(session_text, problem="brute_force_zip",
               agreed={"model": "openai/gpt-6.1-sol", "thinking_level": "low"},
               prior_folders=set())
ranked = not (set(result["reasons"]) & UNRANKING_REASONS)
```

Returns `session_id`, private `cwd`, `metrics`, and `reasons` as specified in
[the spec](../../docs/spec.md). Malformed uploads raise `NotPiLogError`.
All physical entries count, including abandoned branches and auxiliary usage.
Characters are Unicode code points, with CRLF/CR normalized to LF, without trimming.

## Integration decision needed

`missing_usage` is an additional **unranking** reason, not yet in the shared spec.
`total_tokens` is `None` (JSON `null`) when usage is missing, invalid, an error/aborted
reply reports zero, or a fork references another file whose usage is unavailable.
The website MUST use `UNRANKING_REASONS` or explicitly handle this reason before
ranking. Do not replace unknown totals with zero. Owners must agree this addition
in the shared spec before integration. The shared contract was not edited here.

## Evidence and limits

Success requires `{"result":"passed"}` in a non-error tool result linked by
`toolCallId` to a bash call mentioning the assigned Hackattic endpoint and solve,
or running an absolute script path whose logged write/edit contains that endpoint.
This supports the observed real `brute_force_zip` session. It is a trusted-log
heuristic, not trace authentication or general Python/shell dataflow analysis.
Relative script paths, external scripts, and unusual output formats may not match.

`help_me_unpack` additionally requires explicit input and answer JSON in tool
output for local numeric comparison (32-byte aligned layout). Missing matching
answer evidence yields `answer_mismatch`. This recheck is not yet validated on a
real accepted unpack fixture; it cannot prove which printed answer was submitted.
Other problems rely on the linked Hackattic response without local answer recheck.

Custom system sections and broken IDs/timestamps produce warnings. Cost-rate
validation and input-growth heuristics are not implemented (rates/context vary).
Unknown entries are retained and ignored unless they carry a recognized usage type.
Missing compaction/branch summary usage conservatively prevents ranking.

Validation: `bash tools/check.sh`. Tests use synthetic, manually counted examples;
no private session or credential is committed. Real private session inspected on
2026-10-10: 10 prompts, 599 characters, 15 tool calls, recorded token sum 202053,
`brute_force_zip` passed. Final total unknown because an error reply reported zero.

Progress: [Amit's plan](../../.agents/plans/003-counter.md).
