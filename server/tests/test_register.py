"""The register page: GET /register, and POST /register answering with the key page itself."""

import hashlib
import logging
import re
import tempfile
import unittest
import uuid
from contextlib import closing
from html.parser import HTMLParser
from pathlib import Path

from fastapi.testclient import TestClient

from server import db, users
from server.app import create_app
from server.config import Settings
from server.tests.test_users import BAD_HACKATTIC_USERNAMES

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
WARNING = "Save it now. It is shown once and there is no recovery."
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr",
}


class Page(HTMLParser):
    """A parsed page: every tag with its attributes, the text of each element with an id,
    and the text of each label by its `for`."""

    def __init__(self, html):
        super().__init__()
        self.tags = []  # (tag, attributes), in document order
        self.text = {}  # id -> text inside that element
        self.labels = {}  # label's for -> its text
        self._open = []  # (tag, attributes) of the elements not closed yet
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = {name: value or "" for name, value in attrs}
        self.tags.append((tag, attrs))
        if tag not in VOID_TAGS:
            self._open.append((tag, attrs))

    def handle_endtag(self, tag):
        for i in reversed(range(len(self._open))):
            if self._open[i][0] == tag:
                del self._open[i:]
                return

    def handle_data(self, data):
        for tag, attrs in self._open:
            if "id" in attrs:
                self.text[attrs["id"]] = self.text.get(attrs["id"], "") + data
            if tag == "label" and "for" in attrs:
                self.labels[attrs["for"]] = self.labels.get(attrs["for"], "") + data

    def find(self, tag, **attrs):
        """The attributes of every `tag` element that has all of `attrs`."""
        return [
            found for name, found in self.tags if name == tag and attrs.items() <= found.items()
        ]


def rejection(check, value):
    """The message the shared check in server/users.py gives for a bad value."""
    try:
        check(value)
    except ValueError as exc:
        return str(exc)
    raise AssertionError(f"{value!r} was accepted")


class RegisterTest(unittest.TestCase):
    def setUp(self):
        self.data_dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.settings = Settings(data_dir=self.data_dir)
        # Not following redirects, so a redirect would show up as one.
        self.client = self.enterContext(
            TestClient(create_app(self.settings), follow_redirects=False)
        )

    def register(self, username, hackattic_username):
        return self.client.post(
            "/register", data={"username": username, "hackattic_username": hackattic_username}
        )

    def stored_users(self):
        with closing(db.connect(self.settings.db_path)) as conn:
            rows = conn.execute("SELECT username, hackattic_username, key_hash FROM users")
            return [tuple(row) for row in rows]

    def assert_form(self, response, status_code, values, errors):
        """The register form again, with no key, the entered values, and an inline error
        on exactly the fields in `errors` (field name -> message)."""
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertIsNone(UUID_RE.search(response.text))
        page = Page(response.text)
        for name in ("username", "hackattic_username"):
            with self.subTest(field=name):
                (field,) = page.find("input", name=name)
                self.assertEqual(field["value"], values[name])
                described = [
                    page.text.get(id_, "").strip() for id_ in field["aria-describedby"].split()
                ]
                if name in errors:
                    self.assertEqual(field.get("aria-invalid"), "true")
                    self.assertIn(errors[name], described)
                else:
                    self.assertNotIn("aria-invalid", field)
                    self.assertEqual(len(described), 1)  # only the hint
        return page

    def test_form(self):
        response = self.client.get("/register")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/html"))
        page = Page(response.text)
        self.assertEqual(page.find("html")[0].get("lang"), "en")
        self.assertEqual(len(page.find("meta", name="viewport")), 1)
        (form,) = page.find("form")
        self.assertEqual((form["method"], form["action"]), ("post", "/register"))
        for name, label in (("username", "Username"), ("hackattic_username", "Hackattic username")):
            with self.subTest(field=name):
                (field,) = page.find("input", name=name)
                self.assertEqual(page.labels[field["id"]].strip(), label)
                self.assertEqual(field["value"], "")
                self.assertNotIn("aria-invalid", field)
        self.assertEqual(page.find("script"), [])  # JavaScript only on the key page

    def test_links_and_assets_exist(self):
        key_page = self.register("bob", "bob_h").text
        for page in (Page(self.client.get("/register").text), Page(key_page)):
            links = [a["href"] for a in page.find("a")]
            self.assertEqual(links, ["/", "/register"])
            urls = [link["href"] for link in page.find("link")]
            urls += [script["src"] for script in page.find("script")]
            for url in [*links, *urls]:
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(
            [script["src"] for script in Page(key_page).find("script")], ["/static/copy.js"]
        )

    def test_success_is_the_key_page(self):
        with self.assertLogs(level=logging.DEBUG) as logs:
            logging.getLogger(__name__).info("registering")  # assertLogs needs one record
            response = self.register("Bob", "  bob_h ")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertNotIn("location", response.headers)
        self.assertEqual(str(response.url), "http://testserver/register")

        keys = set(UUID_RE.findall(response.text))
        self.assertEqual(len(keys), 1)
        (key,) = keys
        self.assertEqual(uuid.UUID(key).version, 4)
        self.assertIn(f"/golf-login {key}", response.text)
        self.assertIn(WARNING, response.text)
        page = Page(response.text)
        # What the two copy buttons copy, exactly.
        self.assertEqual(page.text["key"], key)
        self.assertEqual(page.text["login-command"], f"/golf-login {key}")
        self.assertEqual(
            [button["data-copy"] for button in page.find("button")], ["key", "login-command"]
        )
        # In no attribute (so in no link or form URL), and in no log record.
        for tag, attrs in page.tags:
            for value in attrs.values():
                self.assertNotIn(key, value, tag)
        self.assertEqual([line for line in logs.output if key in line], [])

        me = self.client.get("/api/v1/me", headers={"Authorization": f"Bearer {key}"})
        self.assertEqual((me.status_code, me.json()), (200, {"username": "bob"}))

        # Lowercased, trimmed, and only the key's SHA-256 stored.
        self.assertEqual(
            self.stored_users(), [("bob", "bob_h", hashlib.sha256(key.encode()).hexdigest())]
        )
        stored = b"".join(path.read_bytes() for path in self.data_dir.iterdir())
        for form in (key.encode(), uuid.UUID(key).hex.encode(), uuid.UUID(key).bytes):
            with self.subTest(form=form):
                self.assertNotIn(form, stored)

    def test_taken_username(self):
        self.assertEqual(self.register("bob", "bob_h").status_code, 200)
        # The same form again, as reloading the key page sends it, and another case.
        for username, hackattic_username in (("bob", "bob_h"), ("BOB", "someone_else")):
            with self.subTest(username=username):
                self.assert_form(
                    self.register(username, hackattic_username),
                    409,
                    {"username": username, "hackattic_username": hackattic_username},
                    {"username": "Username bob is already taken."},
                )
        self.assertEqual(len(self.stored_users()), 1)

    def test_badly_formed_username(self):
        for username in ("", "ab", "a" * 33, "has space", "dash-name", "ünï"):
            with self.subTest(username=username):
                self.assert_form(
                    self.register(username, "carol_h"),
                    400,
                    {"username": username, "hackattic_username": "carol_h"},
                    {"username": rejection(users.clean_username, username)},
                )
        self.assertEqual(self.stored_users(), [])

    def test_bad_hackattic_username(self):
        for name in BAD_HACKATTIC_USERNAMES:
            with self.subTest(hackattic_username=name):
                self.assert_form(
                    self.register("carol", name),
                    400,
                    {"username": "carol", "hackattic_username": name},
                    {"hackattic_username": rejection(users.clean_hackattic_username, name)},
                )
        self.assertEqual(self.stored_users(), [])

    def test_both_fields_wrong(self):
        errors = {
            "username": rejection(users.clean_username, "x"),
            "hackattic_username": rejection(users.clean_hackattic_username, ""),
        }
        response = self.register("x", "")
        page = self.assert_form(response, 400, {"username": "x", "hackattic_username": ""}, errors)
        self.assertIn("<title>Error: Register", response.text)
        # Focus starts on the first field with an error.
        focused = [field["name"] for field in page.find("input") if "autofocus" in field]
        self.assertEqual(focused, ["username"])

        # Missing fields get the same inline errors as empty ones, not FastAPI's 422.
        empty = {"username": "", "hackattic_username": ""}
        errors["username"] = rejection(users.clean_username, "")
        self.assert_form(self.client.post("/register"), 400, empty, errors)

    def test_entered_values_are_escaped(self):
        username = '"><b>bold</b>'
        hackattic_username = "<script>alert(1)</script>"
        response = self.register(username, hackattic_username)
        page = self.assert_form(
            response,
            400,
            {"username": username, "hackattic_username": hackattic_username},
            {"username": rejection(users.clean_username, username)},
        )
        self.assertNotIn(hackattic_username, response.text)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", response.text)
        self.assertNotIn("<b>bold</b>", response.text)
        self.assertEqual(page.find("script"), [])
        self.assertEqual(page.find("b"), [])


if __name__ == "__main__":
    unittest.main()
