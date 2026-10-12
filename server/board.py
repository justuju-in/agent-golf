"""The leaderboard of one problem (docs/spec.md, "Scoring").

Ranked: each player's best ranked session, by fewest total tokens, then fewer prompts,
then fewer characters typed; equal scores share a rank (1, 1, 3). Unranked: the latest
attempt of each player who has no ranked session on this board.

Only public fields are read: never a folder, session id, file hash or raw log.
"""

import json
import sqlite3
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Entry:
    """One stored submission, as the board shows it."""

    id: int
    user_id: int
    username: str
    status: str  # ranked or unranked
    reasons: list[str]
    metrics: dict
    submitted_at: str  # ISO 8601, UTC: the session's latest upload
    rank: int | None = None  # its rank, once it is a ranked row


@dataclass(frozen=True)
class Board:
    ranked: list[Entry]  # best first, each with its rank
    unranked: list[Entry]  # latest first


def score(entry: Entry) -> tuple[int, int, int]:
    """What ranks a session: fewer is better, compared in this order. A ranked session
    always has a total (missing_usage unranks)."""
    metrics = entry.metrics
    return (metrics["total_tokens"], metrics["prompts"], metrics["chars_typed"])


def _order(entry: Entry) -> tuple:
    """Best first; of equal scores, the one submitted first."""
    return (score(entry), entry.submitted_at, entry.id)


def entries(conn: sqlite3.Connection, problem: str) -> list[Entry]:
    """Every stored submission for this problem slug."""
    rows = conn.execute(
        "SELECT submissions.id, submissions.user_id, users.username, submissions.status,"
        " submissions.reasons, submissions.metrics, submissions.submitted_at"
        " FROM submissions JOIN users ON users.id = submissions.user_id"
        " WHERE submissions.problem = ?",
        (problem,),
    )
    return [
        Entry(
            id=row["id"],
            user_id=row["user_id"],
            username=row["username"],
            status=row["status"],
            reasons=json.loads(row["reasons"]),
            metrics=json.loads(row["metrics"]),
            submitted_at=row["submitted_at"],
        )
        for row in rows
    ]


def board(conn: sqlite3.Connection, problem: str) -> Board:
    """The board of this problem slug."""
    found = entries(conn, problem)
    best: dict[int, Entry] = {}
    for entry in sorted((entry for entry in found if entry.status == "ranked"), key=_order):
        best.setdefault(entry.user_id, entry)
    ranked: list[Entry] = []
    for position, entry in enumerate(sorted(best.values(), key=_order), start=1):
        tied = ranked and score(ranked[-1]) == score(entry)
        ranked.append(replace(entry, rank=ranked[-1].rank if tied else position))
    # A player without a ranked session has only unranked ones.
    latest: dict[int, Entry] = {}
    for entry in sorted(found, key=lambda entry: (entry.submitted_at, entry.id), reverse=True):
        if entry.user_id not in best:
            latest.setdefault(entry.user_id, entry)
    return Board(ranked=ranked, unranked=list(latest.values()))


def rank(conn: sqlite3.Connection, problem: str, submission_id: int) -> int | None:
    """The submission's rank, if it is its player's row on this problem's board; else None."""
    return next((entry.rank for entry in board(conn, problem).ranked if entry.id == submission_id), None)
