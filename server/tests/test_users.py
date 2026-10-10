"""Creating students: username rules, duplicates, and storing only the key's hash."""

import hashlib
import io
import os
import tempfile
import unittest
import uuid
from contextlib import closing, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from server import db, users
from server.config import Settings


class CreateUserTest(unittest.TestCase):
    def setUp(self):
        self.data_dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        db_path = Settings(data_dir=self.data_dir).db_path
        db.init_db(db_path)
        self.conn = self.enterContext(closing(db.connect(db_path)))

    def count_users(self):
        return self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def test_only_the_key_hash_is_stored(self):
        key = users.create_user(self.conn, "alice", "alice_hackattic")
        self.assertEqual(str(uuid.UUID(key)), key)
        self.assertEqual(uuid.UUID(key).version, 4)
        row = self.conn.execute("SELECT * FROM users").fetchone()
        self.assertEqual(row["username"], "alice")
        self.assertEqual(row["hackattic_username"], "alice_hackattic")
        self.assertEqual(row["key_hash"], hashlib.sha256(key.encode()).hexdigest())
        self.assertTrue(row["created_at"])

        self.conn.close()
        stored = b"".join(path.read_bytes() for path in self.data_dir.iterdir())
        for form in (key.encode(), uuid.UUID(key).hex.encode(), uuid.UUID(key).bytes):
            with self.subTest(form=form):
                self.assertNotIn(form, stored)

    def test_username_is_lowercased(self):
        users.create_user(self.conn, "Alice_99", "Alice-H")
        row = self.conn.execute("SELECT username, hackattic_username FROM users").fetchone()
        self.assertEqual(row["username"], "alice_99")
        self.assertEqual(row["hackattic_username"], "Alice-H")

    def test_username_length_limits(self):
        for name in ("abc", "a" * 32):
            with self.subTest(name=name):
                users.create_user(self.conn, name, "h")
        self.assertEqual(self.count_users(), 2)

    def test_badly_formed_username_is_rejected(self):
        for name in ("", "ab", "a" * 33, "has space", "dash-name", "dot.name", "ünï", "alice\n"):
            with self.subTest(name=name), self.assertRaises(users.InvalidUsername):
                users.create_user(self.conn, name, "h")
        self.assertEqual(self.count_users(), 0)

    def test_duplicate_username_is_rejected(self):
        users.create_user(self.conn, "alice", "first")
        for name in ("alice", "ALICE"):
            with self.subTest(name=name), self.assertRaises(users.UsernameTaken):
                users.create_user(self.conn, name, "second")
        self.assertEqual(self.count_users(), 1)

    def test_each_user_gets_their_own_key(self):
        alice = users.create_user(self.conn, "alice", "a")
        bob = users.create_user(self.conn, "bob", "b")
        self.assertNotEqual(alice, bob)
        self.assertEqual(users.user_for_authorization(self.conn, f"Bearer {alice}")["username"], "alice")
        self.assertEqual(users.user_for_authorization(self.conn, f"Bearer {bob}")["username"], "bob")


class CommandLineTest(unittest.TestCase):
    def setUp(self):
        self.data_dir = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(mock.patch.dict(os.environ, {"AGENT_GOLF_DATA_DIR": self.data_dir}))

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = users.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_prints_a_working_key(self):
        code, out, _ = self.run_main("Bob", "bob_hackattic")
        self.assertEqual(code, 0)
        key = out.strip()
        with closing(db.connect(Settings(data_dir=Path(self.data_dir)).db_path)) as conn:
            user = users.user_for_authorization(conn, f"Bearer {key}")
        self.assertEqual(user["username"], "bob")

    def test_duplicate_username_fails(self):
        self.run_main("bob", "bob_hackattic")
        code, out, err = self.run_main("bob", "someone_else")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("already taken", err)


if __name__ == "__main__":
    unittest.main()
