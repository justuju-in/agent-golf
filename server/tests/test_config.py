"""Settings from environment variables, and the data directory."""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import server
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


if __name__ == "__main__":
    unittest.main()
