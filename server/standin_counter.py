"""Stand-in for the counter (plan 003, `server/counter/`), until that is on main.

It has the names and shapes of docs/spec.md, "Contract: counter", but every number
and verdict is made up from the file's SHA-256, so the website can be built and
tested first. Only `session_id` and `cwd` are real (from the session header).
Deleted in plan 002 step 4.1.
"""

import hashlib
import json

NOT_SOLVED = "not_solved"
MODEL_MISMATCH = "model_mismatch"
THINKING_LEVEL_MISMATCH = "thinking_level_mismatch"
MODEL_SWITCHED = "model_switched"
FOLDER_REUSED = "folder_reused"
MISSING_USAGE = "missing_usage"
CUSTOM_SETUP = "custom_setup"
INCONSISTENT_LOG = "inconsistent_log"
USAGE_NOT_RECORDED = "usage_not_recorded"

UNRANKING_REASONS = frozenset(
    {NOT_SOLVED, MODEL_MISMATCH, THINKING_LEVEL_MISMATCH, MODEL_SWITCHED, FOLDER_REUSED, MISSING_USAGE}
)
WARNING_REASONS = frozenset({CUSTOM_SETUP, INCONSISTENT_LOG, USAGE_NOT_RECORDED})


class NotPiLogError(ValueError):
    """The text is not a Pi session log: not JSON lines, or no session header first."""


def _header(session_text: str) -> dict:
    """The session header, once every line is known to be a JSON object."""
    try:
        # Split on "\n" only: str.splitlines() would also split inside JSON strings.
        entries = [json.loads(line) for line in session_text.split("\n") if line.strip()]
    except ValueError as exc:
        raise NotPiLogError("not JSON lines") from exc
    if not entries or any(not isinstance(entry, dict) for entry in entries):
        raise NotPiLogError("not JSON objects")
    if entries[0].get("type") != "session":
        raise NotPiLogError("no session header")
    return entries[0]


def _text(value: object, default: str) -> str:
    """`value` if it is a non-empty string, else `default`."""
    return value if isinstance(value, str) and value else default


def score(session_text: str, problem: str, agreed: dict, prior_folders: set[str]) -> dict:
    """Made-up metrics and reasons, the same every time for the same text.

    By the hash, half of all files are clean, and the rest are not solved, have no
    usage (`total_tokens` None), switch model and thinking level mid-session, or
    carry a warning. `agreed` values of "any" skip that match, as in the spec.
    `problem` is not used: "solved" is made up too.
    """
    header = _header(session_text)
    digest = hashlib.sha256(session_text.encode("utf-8")).digest()
    case = digest[0] % 8  # 0-3 clean, 4 not solved, 5 no usage, 6 switches, 7 a warning

    agreed_model, agreed_level = agreed["model"], agreed["thinking_level"]
    # The agreed setup answers; made-up answers where the problem allows "any" (or has
    # no setup yet, which then mismatches).
    models = [agreed_model if agreed_model not in ("any", None) else "standin/model-a"]
    levels = [agreed_level if agreed_level not in ("any", None) else "medium"]
    if case == 6:
        models.append("standin/model-b")
        levels.append("standin-level-b")

    reasons = set()
    if case == 4:
        reasons.add(NOT_SOLVED)
    if case == 5:
        reasons.add(MISSING_USAGE)
    if case == 7:
        reasons.add(USAGE_NOT_RECORDED)
    if agreed_model == "any":
        if len(models) > 1:
            reasons.add(MODEL_SWITCHED)
    elif models != [agreed_model]:
        reasons.add(MODEL_MISMATCH)
    if agreed_level != "any" and levels != [agreed_level]:
        reasons.add(THINKING_LEVEL_MISMATCH)

    cwd = _text(header.get("cwd"), "/standin/" + digest.hex()[:16])
    if cwd in prior_folders:
        reasons.add(FOLDER_REUSED)

    return {
        "session_id": _text(header.get("id"), "standin-" + digest.hex()[:16]),
        "cwd": cwd,
        "metrics": {
            "total_tokens": None if MISSING_USAGE in reasons else 1000 + int.from_bytes(digest[1:4]) % 200_000,
            "prompts": 1 + digest[4] % 12,
            "chars_typed": 10 + int.from_bytes(digest[5:7]) % 3000,
            "tool_calls": digest[7] % 40,
            "models": sorted(set(models)),
            "thinking_levels": sorted(set(levels)),
            "solved": NOT_SOLVED not in reasons,
        },
        "reasons": sorted(reasons),
    }
