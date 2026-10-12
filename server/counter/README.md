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

## Usage and correctness

Errored/aborted assistant replies with absent, null or zero usage contribute zero
and emit the warning `usage_not_recorded`. Recorded positive usage still counts.
Normal replies with missing/invalid usage emit `missing_usage`, set total tokens
to `None` (JSON `null`), and prevent ranking. The website should import
`UNRANKING_REASONS` and `WARNING_REASONS` rather than duplicate these sets.
The reason sets match the final spec at main `c1b61da` (2026-10-12).

There is no local answer recomputation or `answer_mismatch` reason. Hackattic's
actual response is the correctness evidence.

Success requires `{"result":"passed"}` in a non-error tool result linked by
`toolCallId` to a bash call whose command or referenced logged script mentions
`hackattic.com`. URLs can be assembled from variables. Explicit `/challenges/slug`
evidence for a different problem is rejected; when no literal path is present,
the requested problem is used. Referenced absolute/relative script paths are
resolved against session cwd. Shell directory changes and general dataflow are
not interpreted. This is trusted-log evidence, not trace authentication; host-only
evidence cannot independently identify a problem. Failed writes/edits and
filesystem changes outside tracked writes/edits are not modeled.

Custom system sections and broken IDs/timestamps produce warnings. Cost-rate
validation and input-growth heuristics are not implemented (rates/context vary).
Unknown entries are retained and ignored unless they carry a recognized usage type.
Missing compaction/branch-summary usage contributes zero with `usage_not_recorded`,
without preventing ranking. Forked sessions still have unknown usage (`missing_usage`).

Validation: `bash tools/check.sh`; synthetic cases and three heavily redacted real
upload fixtures in [samples](../../samples/README.md). No credentials committed.
Real solved ZIP session: 202053 tokens, 10 prompts, 599 characters, 15 tool calls,
with `usage_not_recorded` warning. It ranks for model `openai/gpt-6.1-sol` and
thinking level `low`, or `any`/`any`; unused initial selections do not count.

Both available real logs record `thinkingLevel` on every assistant reply (26/26
and 8/8). The latter has only its initial `thinking_level_change` event, `medium`.
This verifies these local examples, not every Pi version. There is no fallback to
selection events: thinking levels come only from assistant replies, per the spec.

Progress: [Amit's plan](../../.agents/plans/003-counter.md).

## Per-problem setup

The website supplies `agreed` from the submitted problem's config. `"any"` skips
that match. Model `"any"` still requires one answering model: more than one emits
`model_switched` and prevents ranking. Models come only from assistant messages
and model-attributed `usage` entries, never selection events or summary metadata.
Thinking levels come only from assistant messages. Both selection-event types
are ignored, including selections before the first prompt. With `"any"` thinking,
changes and missing level metadata do not trigger thinking_level_mismatch.
