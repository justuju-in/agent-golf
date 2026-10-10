"""GET /api/v1/me, per docs/spec.md "Contract: student key validation"."""

import tempfile
import unittest
import uuid
from contextlib import closing
from pathlib import Path

from fastapi.testclient import TestClient

from server import db, users
from server.app import create_app
from server.config import Settings


class MeTest(unittest.TestCase):
    def setUp(self):
        settings = Settings(data_dir=Path(self.enterContext(tempfile.TemporaryDirectory())))
        # Entering the client runs startup, which creates the tables.
        self.client = self.enterContext(TestClient(create_app(settings)))
        with closing(db.connect(settings.db_path)) as conn:
            self.key = users.create_user(conn, "alice", "alice_hackattic")

    def get_me(self, authorization=None):
        headers = {} if authorization is None else {"Authorization": authorization}
        return self.client.get("/api/v1/me", headers=headers)

    def test_valid_key(self):
        response = self.get_me(f"Bearer {self.key}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("content-type"), "application/json")
        self.assertEqual(response.json(), {"username": "alice"})
        self.assertEqual(response.headers.get("cache-control"), "no-store")

    def test_key_is_parsed_as_uuid(self):
        for token in (self.key.upper(), self.key.replace("-", "")):
            with self.subTest(token=token):
                response = self.get_me(f"Bearer {token}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"username": "alice"})

    def test_bad_credentials(self):
        unknown = str(uuid.uuid4())
        cases = {  # name: (Authorization header, supplied token)
            "no header": (None, ""),
            "basic scheme": ("Basic xyz", "xyz"),
            "real key, basic scheme": (f"Basic {self.key}", self.key),
            "bearer, no token": ("Bearer", ""),
            "bearer, blank token": ("Bearer ", ""),
            "bearer, not a uuid": ("Bearer not-a-uuid", "not-a-uuid"),
            "bearer, unknown key": (f"Bearer {unknown}", unknown),
        }
        for name, (authorization, token) in cases.items():
            with self.subTest(name):
                response = self.get_me(authorization)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.headers.get("cache-control"), "no-store")
                self.assertNotIn(self.key, response.text)
                if token:
                    self.assertNotIn(token, response.text)

    def test_key_in_url_is_not_accepted(self):
        response = self.client.get("/api/v1/me", params={"key": self.key})
        self.assertEqual(response.status_code, 401)
        self.assertNotIn(self.key, response.text)


if __name__ == "__main__":
    unittest.main()
