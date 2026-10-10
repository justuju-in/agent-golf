# Proposal: zero-token problem browser

Status: draft for website, counter, and plugin owner review. This document does
not change the [MVP spec](../spec.md) or authorize implementation.

## Goal

Students can discover eligible problem slugs and read contest rules inside Pi
without asking the model, spending model tokens, or adding conversation entries.

## Proposed MVP experience

- `/golf-problems` fetches the current catalogue from the configured website origin.
- A Pi UI selection menu lists eligible problem titles and slugs.
- Selecting a problem opens a UI-only details view with its slug, challenge URL,
  contest rules, problem-specific constraints, and `/golf-submit <slug>` instruction.
- Cancellation changes nothing. An empty catalogue says no problems are available
  but still allows the student to read the contest rules.
- Network errors, invalid responses, and unsupported UI modes produce clear
  UI/client feedback without falling back to a model message.
- The command is informational: it does not select or bind a problem to the session,
  start an attempt, fetch a personalized Hackattic input, or submit anything.
- The student still prompts the agent normally; the agent's reading, solving, and
  submission work counts under the existing scoring rules.

## Scoring and privacy boundary

Use Pi UI APIs, not `sendMessage`, `sendUserMessage`, or a model-callable tool.
Do not append catalogue contents or a selection to the session. Direct plugin HTTP
requests are not assistant `toolCall` blocks. The expected scoring delta is zero
model tokens, user prompts, characters typed, and tool calls.

This is exclusion from the model conversation, not a promise that terminal/client
activity cannot be recorded. Verify the persisted JSONL behavior in a smoke test.
Do not send student credentials or a session log when browsing a public catalogue.

## Proposed backend contract (requires agreement)

`GET /api/v1/problems`, public, no authentication or request body. HTTP 200 JSON:

```json
{
  "rules_version": "mvp-1",
  "rules": ["Current contest rules as plain text."],
  "problems": [
    {
      "slug": "help_me_unpack",
      "title": "Help me unpack",
      "challenge_url": "https://hackattic.com/challenges/help_me_unpack",
      "instructions": ["Public challenge constraints and required evidence."]
    }
  ]
}
```

- The website owns this response and publishes only currently eligible problems,
  coordinated with counter support. An empty `problems` array is valid.
- Rules must reflect the agreed spec, not a second independently maintained policy.
  The version identifies displayed rules; it does not pin an attempt's eligibility.
  Include the agreed model and thinking level in the displayed rules; if these are
  undecided, say so explicitly rather than implying the contest is ready.
- Instructions are administrative/evidence requirements and public constraints,
  not solver hints, optimized prompts, or solution code.
- Fetch on command invocation with a bounded timeout; no polling or offline cache.
- Render text as text, not executable markup or terminal control sequences. Validate
  response shape, impose reasonable size limits, and accept only expected Hackattic
  challenge URLs. Do not silently render arbitrary server-provided escape sequences.
- The catalogue is advisory. Submission validation remains authoritative; viewing
  a problem does not guarantee it remains eligible later.
- Non-200 and malformed responses display a generic availability error. The plugin
  does not depend on error-body text.

## Scope and non-goals

Include one command, a small backend-owned catalogue, current rules, problem
constraints, and submit syntax. A single launch problem uses the same response.

Exclude the full Hackattic catalogue, scraping challenge pages, hints, prompt
injection, search/filtering, session binding, status widgets, persisted selection,
new scoring logic, and changes to the existing submission request/reply.

Do not list `brute_force_zip` as ranked-ready until the owners agree how its
expiring downloadable input supports the required correctness evidence. The
existing counter plan explicitly scopes answer rechecking to Help me unpack.

## Acceptance checks for implementation

1. With a mock catalogue, list, view, cancel, and repeat work without model calls.
2. In an idle session with no concurrent model activity, compare persisted JSONL
   before and after: no new conversation, tool-call, usage, or catalogue entries.
   Counter metrics remain unchanged when available.
3. Test empty catalogue, timeout, non-200, malformed/oversized data, unsafe display
   text, and unsupported UI mode; no model-message fallback in any case.
4. Viewing details does not change folder-start metadata or submission behavior.
5. Confirm the endpoint needs no student key and the plugin transmits no log.
6. Add automated tests to the repository gate and run `bash tools/check.sh`.

## Owner approval and rollout

- Website owner: agree endpoint, public access, response shape, and catalogue source.
- Counter owner: confirm which problems are eligible and their evidence requirements.
- Plugin owner: verify supported UI APIs and implement the zero-context command.
- All owners: approve the scope and rule wording before promoting this contract into
  the spec and adding implementation steps to their existing plans.

Suggested sequence: approve this proposal → update shared spec and plans → implement
backend and plugin independently against fixtures → run the JSONL/scoring smoke test.
The model/thinking configuration and launch problem set remain existing MVP decisions;
this proposal neither chooses them nor makes unsupported problems eligible.
