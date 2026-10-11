"""SQLite storage. Parameterized queries only."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path

DB_FILE_MODE = 0o600  # the database holds key hashes, session folders and Hackattic usernames

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    hackattic_username TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,  -- SHA-256 hex of the student key; the key itself is never stored
    created_at TEXT NOT NULL        -- ISO 8601, UTC
);

-- One row per uploaded session; the raw file is <data dir>/uploads/<id>.jsonl.
-- A resubmitted session replaces its row in place, keeping its id (and so its link).
-- AUTOINCREMENT: an id is never reused, so ids follow first-upload order and an old
-- link never shows another submission.
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id),
    problem TEXT NOT NULL,          -- slug from the problem config
    session_id TEXT NOT NULL,       -- from the counter (session header); never shown publicly
    cwd TEXT NOT NULL,              -- the session's folder, for later prior_folders; never shown publicly
    sha256 TEXT NOT NULL,           -- SHA-256 hex of the uploaded file, to spot the same file again
    folder_was_empty INTEGER,       -- 1 or 0 as the plugin sent it, NULL if not sent; no ranking effect
    status TEXT NOT NULL,           -- ranked or unranked
    reasons TEXT NOT NULL,          -- JSON list of reason codes
    metrics TEXT NOT NULL,          -- JSON object, the counter's metrics
    first_submitted_at TEXT NOT NULL,  -- ISO 8601, UTC: the session's first upload
    submitted_at TEXT NOT NULL,        -- ISO 8601, UTC: its latest upload
    UNIQUE (user_id, session_id)
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    # check_same_thread=False: FastAPI may open, use and close a request's connection
    # on different worker threads. Each connection still serves one request at a time.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> None:
    """Create the data directory, the database file (0600) and the tables if they do not exist yet."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Create the file 0600 before SQLite opens it (an empty file is an empty database), so
    # other accounts can never read it, and set an existing one to exactly 0600 whatever the
    # umask. SQLite gives its journal and WAL files the database file's mode.
    os.close(os.open(db_path, os.O_RDWR | os.O_CREAT, DB_FILE_MODE))
    os.chmod(db_path, DB_FILE_MODE)
    with closing(connect(db_path)) as conn:
        conn.executescript(SCHEMA)
