"""Student accounts and keys.

A key is a random UUID, shown to the student once. Only its SHA-256 hex digest is
stored, so a leaked database does not leak keys. Never log a key.

Students register at /register. For scripted test users, the command line does the
same and prints the key once:

    python -m server.users <username> <hackattic_username>
"""

import argparse
import hashlib
import re
import sqlite3
import sys
import unicodedata
import uuid
from contextlib import closing
from datetime import UTC, datetime

from server import db
from server.config import load_settings

USERNAME_RE = re.compile(r"[a-z0-9_]{3,32}")
HACKATTIC_USERNAME_MAX = 64


class InvalidUsername(ValueError):
    """The username, once lowercased, does not match [a-z0-9_]{3,32}."""


class InvalidHackatticUsername(ValueError):
    """The Hackattic username, once trimmed, is empty, too long, or has a control character."""


class UsernameTaken(Exception):
    """Another student already registered this username."""


def clean_username(username: str) -> str:
    """The username, lowercased. Raises InvalidUsername unless it then matches [a-z0-9_]{3,32}."""
    username = username.lower()
    if not USERNAME_RE.fullmatch(username):
        raise InvalidUsername(
            "Username must be 3 to 32 characters: lowercase letters, digits or underscores."
        )
    return username


def clean_hackattic_username(hackattic_username: str) -> str:
    """The Hackattic username, trimmed. Raises InvalidHackatticUsername if it is then empty,
    over 64 characters, or contains a control character (Unicode category Cc)."""
    hackattic_username = hackattic_username.strip()
    if not hackattic_username:
        raise InvalidHackatticUsername("Hackattic username is required.")
    if len(hackattic_username) > HACKATTIC_USERNAME_MAX:
        raise InvalidHackatticUsername(
            f"Hackattic username must be at most {HACKATTIC_USERNAME_MAX} characters."
        )
    if any(unicodedata.category(char) == "Cc" for char in hackattic_username):
        raise InvalidHackatticUsername(
            "Hackattic username must not contain control characters, such as tabs or line breaks."
        )
    return hackattic_username


def hash_key(key: str) -> str:
    """SHA-256 hex digest of a key in canonical UUID form."""
    return hashlib.sha256(key.encode("ascii")).hexdigest()


def key_from_authorization(header: str | None) -> str | None:
    """The canonical key from `Authorization: Bearer <key>`, or None if missing or malformed."""
    scheme, _, token = (header or "").partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        return None
    try:
        return str(uuid.UUID(token))
    except ValueError:
        return None


def user_for_authorization(conn: sqlite3.Connection, header: str | None) -> sqlite3.Row | None:
    """The user (id, username) whose key is in the Authorization header, or None."""
    key = key_from_authorization(header)
    if key is None:
        return None
    return conn.execute(
        "SELECT id, username FROM users WHERE key_hash = ?", (hash_key(key),)
    ).fetchone()


def create_user(conn: sqlite3.Connection, username: str, hackattic_username: str) -> str:
    """Register a student and return their new key. It is not stored, so it cannot be shown again.

    Raises InvalidUsername, InvalidHackatticUsername or UsernameTaken; the register page
    and the command line share these checks.
    """
    username = clean_username(username)
    hackattic_username = clean_hackattic_username(hackattic_username)
    key = str(uuid.uuid4())
    with conn:
        inserted = conn.execute(
            "INSERT INTO users (username, hackattic_username, key_hash, created_at)"
            " VALUES (?, ?, ?, ?) ON CONFLICT (username) DO NOTHING",
            (
                username,
                hackattic_username,
                hash_key(key),
                datetime.now(UTC).isoformat(timespec="seconds"),
            ),
        ).rowcount
    if not inserted:
        raise UsernameTaken(f"Username {username} is already taken.")
    return key


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m server.users",
        description="Create a student and print their key once. Uses AGENT_GOLF_DATA_DIR.",
    )
    parser.add_argument("username")
    parser.add_argument("hackattic_username")
    args = parser.parse_args(argv)

    settings = load_settings()
    db.init_db(settings.db_path)
    with closing(db.connect(settings.db_path)) as conn:
        try:
            key = create_user(conn, args.username, args.hackattic_username)
        except (InvalidUsername, InvalidHackatticUsername, UsernameTaken) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    print(key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
