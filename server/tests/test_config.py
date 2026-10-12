"""Settings from environment variables, and the data directory."""

import os
import stat
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from fastapi.testclient import TestClient

import server
from server import db, users
from server.app import create_app
from server.config import Settings, load_settings


class SettingsTest(unittest.TestCase):
    def test_defaults(self):
        settings = load_settings({})
        # Relative to the server package, not the current directory.
        self.assertEqual(settings.data_dir, Path(server.__file__).resolve().parent / "data")
        self.assertEqual(settings.api_base_url, "http://localhost:8000")

    def test_from_environment(self):
        settings = load_settings(
            {
                "AGENT_GOLF_DATA_DIR": "/srv/agent-golf",
                "AGENT_GOLF_API_BASE_URL": "https://agent-golf.justuju.in/",
            }
        )
        self.assertEqual(settings.data_dir, Path("/srv/agent-golf"))
        self.assertEqual(settings.db_path.parent, Path("/srv/agent-golf"))
        self.assertEqual(settings.api_base_url, "https://agent-golf.justuju.in")

    def test_startup_creates_missing_data_dir(self):
        data_dir = Path(self.enterContext(tempfile.TemporaryDirectory())) / "new" / "data"
        with TestClient(create_app(Settings(data_dir=data_dir))):
            self.assertTrue(data_dir.is_dir())
            self.assertTrue((data_dir / "agent_golf.db").is_file())

    def test_database_file_is_private(self):
        # Even under a permissive umask, only the server's own user can read the database.
        self.addCleanup(os.umask, os.umask(0))
        settings = Settings(data_dir=Path(self.enterContext(tempfile.TemporaryDirectory())))
        with TestClient(create_app(settings)):
            self.assertEqual(stat.S_IMODE(settings.db_path.stat().st_mode), 0o600)
            # Still 0600 once rows are written.
            with closing(db.connect(settings.db_path)) as conn:
                users.create_user(conn, "alice", "alice_hackattic")
            self.assertEqual(stat.S_IMODE(settings.db_path.stat().st_mode), 0o600)

    def test_existing_database_file_is_made_private(self):
        settings = Settings(data_dir=Path(self.enterContext(tempfile.TemporaryDirectory())))
        db.init_db(settings.db_path)
        with closing(db.connect(settings.db_path)) as conn:
            users.create_user(conn, "alice", "alice_hackattic")
        settings.db_path.chmod(0o644)  # as databases made before this change are
        db.init_db(settings.db_path)
        self.assertEqual(stat.S_IMODE(settings.db_path.stat().st_mode), 0o600)
        with closing(db.connect(settings.db_path)) as conn:
            self.assertEqual(conn.execute("SELECT username FROM users").fetchone()["username"], "alice")


if __name__ == "__main__":
    unittest.main()
