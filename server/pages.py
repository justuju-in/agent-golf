"""Text for the HTML pages: setups, reasons in plain English, numbers and times.

Pages show only usernames, models, numbers and verdicts: never prompts, folders,
session ids, raw logs, keys or Hackattic usernames.
"""

from datetime import UTC, datetime

from server.problems import Problem
from server.submissions import UNRANKING_REASONS, WARNING_REASONS

SCORING = "Fewest tokens wins. Ties: fewer prompts, then fewer characters."

# Each counter reason code (docs/spec.md, "Reason codes"): a short label for the board,
# and a sentence for the submission page.
REASONS = {
    "not_solved": (
        "Not solved",
        'The log has no Hackattic reply saying "passed" for this problem.',
    ),
    "model_mismatch": (
        "Wrong model",
        "The models that answered are not exactly the problem's model.",
    ),
    "thinking_level_mismatch": (
        "Wrong thinking level",
        "The thinking levels that answered are not exactly the problem's thinking level.",
    ),
    "model_switched": (
        "Model switched",
        "More than one model answered. Older rules allowed only one model per session.",
    ),
    "folder_reused": (
        "Folder reused",
        "An earlier submission by the same player came from the same folder.",
    ),
    "missing_usage": (
        "Tokens unknown",
        "A reply has no usage recorded, or the session continues one whose usage is in another"
        " file, so the total cannot be counted.",
    ),
    "custom_setup": (
        "Custom setup",
        "Extra rules files or skills appear in the session's system messages.",
    ),
    "inconsistent_log": (
        "Inconsistent log",
        "A consistency check failed: cost against tokens, timestamp order, the message chain,"
        " or input growth.",
    ),
    "usage_not_recorded": (
        "Usage not recorded",
        "An errored or aborted reply, or a summary, had no usage recorded. It counts as 0 tokens.",
    ),
}


def reason_label(code: str) -> str:
    """A reason code's short label, e.g. "Not solved"."""
    return REASONS[code][0]


def reason_detail(code: str) -> str:
    """A reason code's explanation, a sentence or two."""
    return REASONS[code][1]


def unranking(reasons: list[str]) -> list[str]:
    """The codes that unranked a session, without its warnings."""
    return [code for code in reasons if code in UNRANKING_REASONS]


def warnings(reasons: list[str]) -> list[str]:
    """The warning codes: shown, but the session stays ranked."""
    return [code for code in reasons if code in WARNING_REASONS]


def setup_text(problem: Problem) -> str:
    """The problem's model and thinking level, e.g. "any model; any thinking level"."""
    model = "any model" if problem.model == "any" else problem.model
    if problem.thinking_level == "any":
        level = "any thinking level"
    else:
        level = f"thinking level {problem.thinking_level}"
    return f"{model}; {level}"


def number(value: int | None) -> str:
    """A count with thousands separators, or "unknown" for a total that could not be counted."""
    return "unknown" if value is None else f"{value:,}"


def names(values: list[str]) -> str:
    """Models or thinking levels as one line of text."""
    return ", ".join(values) if values else "none recorded"


def now() -> datetime:
    """The current time, once per page, so every row on it agrees."""
    return datetime.now(UTC)


def ago(when: str, now: datetime) -> str:
    """How long before `now` the ISO 8601 time `when` is, e.g. "5 min ago"."""
    minutes = int((now - datetime.fromisoformat(when)).total_seconds() // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return "1 hour ago" if hours == 1 else f"{hours} hours ago"
    days = hours // 24
    return "1 day ago" if days == 1 else f"{days} days ago"


def utc_time(when: str) -> str:
    """The ISO 8601 time `when`, for people, e.g. "11 Oct 2026, 10:05 UTC"."""
    moment = datetime.fromisoformat(when).astimezone(UTC)
    return f"{moment.day} {moment:%b %Y, %H:%M} UTC"
