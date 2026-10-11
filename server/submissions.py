"""Uploads: docs/spec.md, "Contract: plugin → website" and "Contract: website → plugin".

Never log a key or anything from an upload; a counter failure logs only the exception's type.
"""

import hashlib
import json
import logging
import os
import sqlite3
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

from server.config import Settings
from server.problems import Problem

# The one place the counter is imported. Plan 002 step 4.1 swaps this line for
# from server.counter import score, NotPiLogError, UNRANKING_REASONS, WARNING_REASONS
from server.standin_counter import NotPiLogError, UNRANKING_REASONS, WARNING_REASONS, score

MAX_SESSION_BYTES = 20 * 1024 * 1024  # a bigger `session` is file_too_large

# The website's reason codes and their HTTP status (docs/spec.md, "Reason codes").
REJECTION_STATUS = {"bad_key": 401, "unknown_problem": 400, "not_pi_log": 400, "file_too_large": 413}

# The counter's reason codes, and the reply's metrics in docs/spec.md's order.
COUNTER_REASONS = UNRANKING_REASONS | WARNING_REASONS
METRICS = ("total_tokens", "prompts", "chars_typed", "tool_calls", "models", "thinking_levels", "solved")
MAX_SAFE_INTEGER = 2**53 - 1  # the largest count the plugin reads exactly (a JavaScript number)
MAX_SQLITE_INTEGER = 2**63 - 1

logger = logging.getLogger(__name__)


class Rejected(Exception):
    """The website refuses the upload, with one of REJECTION_STATUS's reason codes."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class CounterFailed(Exception):
    """The counter raised something other than NotPiLogError, or returned a result outside
    the contract: a bug, so a 500, not a bad file."""


def utc_now() -> str:
    """The current time, ISO 8601 in UTC, to the second."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def rejection(reason: str) -> dict:
    """The reply body for a rejected upload."""
    return {"status": "rejected", "reasons": [reason], "metrics": None, "url": None}


def reply(row: sqlite3.Row, base_url: str) -> dict:
    """The reply body for a stored submission."""
    return {
        "status": row["status"],
        "reasons": json.loads(row["reasons"]),
        "metrics": json.loads(row["metrics"]),
        "url": f"{base_url}/submissions/{row['id']}",
    }


def _count(value: object) -> bool:
    """A non-negative integer (not a bool) that the plugin reads exactly."""
    return type(value) is int and 0 <= value <= MAX_SAFE_INTEGER


def _well_formed(value: object) -> bool:
    """A non-empty string with no unpaired surrogate, so it can be stored and sent as UTF-8."""
    return isinstance(value, str) and value != "" and not any(
        unicodedata.category(char) == "Cs" for char in value
    )


def _names(value: object) -> bool:
    """A list of model or thinking-level names: strings without control characters."""
    return isinstance(value, list) and all(
        isinstance(name, str)
        and not any(unicodedata.category(char) in ("Cc", "Cs") for char in name)
        for name in value
    )


def valid_result(result: object) -> bool:
    """Whether the counter's result keeps docs/spec.md, "Contract: counter", so that the
    reply built from it is what "Contract: website → plugin" promises."""
    if not isinstance(result, dict) or not isinstance(result.get("metrics"), dict):
        return False
    metrics, reasons = result["metrics"], result.get("reasons")
    if not isinstance(reasons, list) or not all(
        isinstance(reason, str) and reason in COUNTER_REASONS for reason in reasons
    ):
        return False
    if not set(METRICS) <= metrics.keys():
        return False
    tokens = metrics["total_tokens"]
    return (
        _well_formed(result.get("session_id"))
        and _well_formed(result.get("cwd"))
        # total_tokens is null exactly when missing_usage is set.
        and (tokens is None if "missing_usage" in reasons else _count(tokens))
        and all(_count(metrics[name]) for name in ("prompts", "chars_typed", "tool_calls"))
        and _names(metrics["models"])
        and _names(metrics["thinking_levels"])
        and type(metrics["solved"]) is bool
    )


def run_counter(text: str, problem: Problem, prior_folders: set[str]) -> dict:
    """The counter's result with the problem's setup as `agreed`, keeping only the spec's metrics.

    Raises Rejected("not_pi_log") for NotPiLogError, and CounterFailed for any other
    exception or for a result outside the contract.
    """
    agreed = {"model": problem.model, "thinking_level": problem.thinking_level}
    try:
        result = score(text, problem.slug, agreed, prior_folders)
    except NotPiLogError:
        raise Rejected("not_pi_log") from None
    except Exception as exc:
        # Its message or traceback could quote the upload, so log the type only.
        logger.error("counter failed: %s", type(exc).__name__)
        raise CounterFailed from None
    if not valid_result(result):
        logger.error("counter failed: result outside docs/spec.md")
        raise CounterFailed
    return {**result, "metrics": {name: result["metrics"][name] for name in METRICS}}


def prior_folders(conn: sqlite3.Connection, user_id: int, session_id: str) -> set[str]:
    """The folders of the user's earlier submissions (docs/spec.md, "Contract: counter").

    Earlier copies of this session are left out, and so are sessions first uploaded after
    this one was (ids follow first uploads), so resubmitting a session never changes its
    folder verdict. A new session gets every other folder of the user.
    """
    rows = conn.execute(
        "SELECT other.cwd FROM submissions AS other"
        " WHERE other.user_id = :user AND other.session_id != :session"
        " AND NOT EXISTS (SELECT 1 FROM submissions AS own WHERE own.user_id = :user"
        " AND own.session_id = :session AND own.id < other.id)",
        {"user": user_id, "session": session_id},
    )
    return {row["cwd"] for row in rows}


UPLOAD_FILE_MODE = 0o600  # raw logs can hold Hackattic tokens, prompts and local paths


def save_upload(uploads_dir: Path, submission_id: int, data: bytes) -> None:
    """The raw file as uploads/<id>.jsonl, readable only by the server's own user,
    replacing an earlier copy of the session whole."""
    uploads_dir.mkdir(parents=True, exist_ok=True)
    path = uploads_dir / f"{submission_id}.jsonl"
    partial = path.with_suffix(".partial")
    # Created 0600, so the log is never readable by other accounts, not even briefly.
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, UPLOAD_FILE_MODE)
    with os.fdopen(fd, "wb") as file:
        file.write(data)
    # Exactly 0600 whatever the umask, also for a .partial left by an older crash.
    os.chmod(partial, UPLOAD_FILE_MODE)
    os.replace(partial, path)


def submit(
    conn: sqlite3.Connection,
    settings: Settings,
    user_id: int,
    problem: Problem,
    data: bytes,
    folder_was_empty: bool | None,
) -> dict:
    """Score and store an upload that passed the key, problem and size checks; the reply body.

    Raises Rejected("not_pi_log") for a file that is not UTF-8 or not a Pi log, and
    CounterFailed for a counter bug. Nothing is stored for either.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Rejected("not_pi_log") from None

    sha256 = hashlib.sha256(data).hexdigest()
    # The same file for the same problem again: the stored entry, not scored again. (For
    # another problem it is scored, and replaces the session's row like any resubmission.)
    same_file = conn.execute(
        "SELECT * FROM submissions WHERE user_id = ? AND problem = ? AND sha256 = ?",
        (user_id, problem.slug, sha256),
    ).fetchone()
    if same_file is not None:
        return reply(same_file, settings.api_base_url)

    # Once to learn the session and its folder, then with the user's earlier folders.
    session_id = run_counter(text, problem, set())["session_id"]
    result = run_counter(text, problem, prior_folders(conn, user_id, session_id))
    status = "unranked" if UNRANKING_REASONS.intersection(result["reasons"]) else "ranked"
    now = utc_now()
    with conn:
        conn.execute(
            "INSERT INTO submissions (user_id, problem, session_id, cwd, sha256, folder_was_empty,"
            " status, reasons, metrics, first_submitted_at, submitted_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            # A resubmitted session (even for another problem): same row, id and first
            # upload time; everything else replaced.
            " ON CONFLICT (user_id, session_id) DO UPDATE SET problem = excluded.problem,"
            " cwd = excluded.cwd, sha256 = excluded.sha256,"
            " folder_was_empty = excluded.folder_was_empty, status = excluded.status,"
            " reasons = excluded.reasons, metrics = excluded.metrics,"
            " submitted_at = excluded.submitted_at",
            (
                user_id,
                problem.slug,
                result["session_id"],
                result["cwd"],
                sha256,
                folder_was_empty,
                status,
                json.dumps(result["reasons"]),
                json.dumps(result["metrics"]),
                now,
                now,
            ),
        )
        row = conn.execute(
            "SELECT * FROM submissions WHERE user_id = ? AND session_id = ?",
            (user_id, result["session_id"]),
        ).fetchone()
        # Still in the transaction: if the file cannot be saved, the row is not changed.
        save_upload(settings.uploads_dir, row["id"], data)
    return reply(row, settings.api_base_url)


def public(conn: sqlite3.Connection, submission_id: int) -> dict | None:
    """A submission's public fields, or None if there is none. Never its folder, session
    id, file hash, folder_was_empty, raw log or the student's Hackattic username."""
    if not 0 < submission_id <= MAX_SQLITE_INTEGER:
        return None  # no such id (and a bigger one would not fit an SQLite query)
    row = conn.execute(
        "SELECT submissions.id, users.username, submissions.problem, submissions.status,"
        " submissions.reasons, submissions.metrics, submissions.first_submitted_at,"
        " submissions.submitted_at"
        " FROM submissions JOIN users ON users.id = submissions.user_id"
        " WHERE submissions.id = ?",
        (submission_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "problem": row["problem"],
        "status": row["status"],
        "reasons": json.loads(row["reasons"]),
        "metrics": json.loads(row["metrics"]),
        "first_submitted_at": row["first_submitted_at"],
        "submitted_at": row["submitted_at"],
    }
