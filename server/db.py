"""SQLite storage. Parameterized queries only."""

import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    hackattic_username TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,  -- SHA-256 hex of the student key; the key itself is never stored
    created_at TEXT NOT NULL        -- ISO 8601, UTC
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    # check_same_thread=False: FastAPI may open, use and close a request's connection
    # on different worker threads. Each connection still serves one request at a time.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> None:
    """Create the data directory and the tables if they do not exist yet."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(db_path)) as conn:
        conn.executescript(SCHEMA)
