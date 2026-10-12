"""The board: GET / and GET /problems/<slug> (plan 002 step 3.1)."""

import hashlib
import json
import tempfile
import unittest
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from server import db, pages, problems, submissions, users
from server.app import create_app
from server.config import Settings
from server.tests.dom import parse

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
SCORING = "Fewest tokens wins. Ties: fewer prompts, then fewer characters."
# Another listed problem with one fixed model, and one whose setup is not set yet.
FIXED = problems.Problem(
    slug="fixed_setup",
    title="Fixed setup",
    challenge_url="https://hackattic.com/challenges/fixed_setup",
    instructions=("Solve it.",),
    model="openai/gpt-5.5",
    thinking_level="low",
)
UNSET = problems.Problem(
    slug="not_set_yet",
    title="Not set yet",
    challenge_url="https://hackattic.com/challenges/not_set_yet",
    instructions=("Solve it.",),
)


def session(
    session_id,
    tokens=1000,
    prompts=2,
    chars=40,
    tool_calls=3,
    reasons=(),
    models=("openai/gpt-5.5",),
    levels=("low",),
    cwd=None,
):
    """A small Pi session log whose header holds the result fake_counter gives for it."""
    header = {
        "type": "session", "version": 3, "id": session_id, "timestamp": "2026-10-11T10:00:00.000Z",
        "cwd": cwd or f"/home/student/{session_id}",
        "fake": {
            "total_tokens": tokens, "prompts": prompts, "chars_typed": chars, "tool_calls": tool_calls,
            "models": list(models), "thinking_levels": list(levels), "reasons": list(reasons),
        },
    }
    prompt = {
        "type": "message", "id": "u1", "parentId": None, "timestamp": "2026-10-11T10:00:01.000Z",
        "message": {"role": "user", "content": [{"type": "text", "text": f"secret prompt of {session_id}"}]},
    }
    return (json.dumps(header) + "\n" + json.dumps(prompt) + "\n").encode()


def fake_counter(session_text, problem, agreed, prior_folders):
    """docs/spec.md, "Contract: counter", giving the result the session's header holds."""
    header = json.loads(session_text.split("\n", 1)[0])
    fake = header["fake"]
    reasons = set(fake["reasons"]) | ({"folder_reused"} if header["cwd"] in prior_folders else set())
    metrics = {
        "total_tokens": None if "missing_usage" in reasons else fake["total_tokens"],
        "prompts": fake["prompts"], "chars_typed": fake["chars_typed"], "tool_calls": fake["tool_calls"],
        "models": fake["models"], "thinking_levels": fake["thinking_levels"],
        "solved": "not_solved" not in reasons,
    }
    return {"session_id": header["id"], "cwd": header["cwd"], "metrics": metrics, "reasons": sorted(reasons)}


class PageTestCase(unittest.TestCase):
    """A fresh app scoring with fake_counter, with the time fixed at NOW."""

    def setUp(self):
        self.settings = Settings(
            data_dir=Path(self.enterContext(tempfile.TemporaryDirectory())), api_base_url="https://golf.example"
        )
        self.client = self.enterContext(TestClient(create_app(self.settings)))
        self.enterContext(mock.patch.object(submissions, "score", fake_counter))
        self.enterContext(mock.patch.object(pages, "now", return_value=NOW))
        self.keys = {}

    def key(self, username):
        """The player's key, registering them (Hackattic username <username>_hackattic) first."""
        if username not in self.keys:
            with closing(db.connect(self.settings.db_path)) as conn:
                self.keys[username] = users.create_user(conn, username, f"{username}_hackattic")
        return self.keys[username]

    def upload(self, username, content, minutes_ago=0, problem="help_me_unpack"):
        """Upload as the plugin does, `minutes_ago` minutes before NOW; the reply."""
        when = (NOW - timedelta(minutes=minutes_ago)).isoformat(timespec="seconds")
        with mock.patch.object(submissions, "utc_now", return_value=when):
            response = self.client.post(
                "/api/v1/submissions",
                headers={"Authorization": f"Bearer {self.key(username)}"},
                data={"problem": problem},
                files={"session": ("session.jsonl", content, "application/x-ndjson")},
            )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def page(self, path):
        """The page at `path`, parsed; it must be a 200 HTML page."""
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/html; charset=utf-8")
        return parse(response.text)


def link(url):
    """The path of a reply's url: the link a page should have."""
    return urlsplit(url).path


class BoardTest(PageTestCase):
    def table(self, page, name):
        """A board table's rows (header row first), or None if the page has no such table."""
        tables = page.find_all("table", id=name)
        return tables[0].rows() if tables else None

    def test_header(self):
        page = self.page("/")
        self.assertEqual(page.find("title").text(), "Help me unpack – Agent Golf")
        self.assertEqual(page.find("h1").text(), "Help me unpack")
        self.assertEqual(page.find("p", class_="setup").text(), "Setup: any model, one per session; any thinking level")
        self.assertEqual(page.find("p", class_="scoring").text(), SCORING)
        # Reloads itself every 30 seconds.
        self.assertEqual(page.find("meta", http_equiv="refresh").attrs["content"], "30")
        with mock.patch.object(problems, "PROBLEMS", (FIXED,)):
            page = self.page("/problems/fixed_setup")
        self.assertEqual(page.find("p", class_="setup").text(), "Setup: openai/gpt-5.5; thinking level low")

    def test_footer(self):
        footer = self.page("/").find("ol", class_="steps")
        steps = [item.text() for item in footer.find_all("li")]
        self.assertEqual(
            [(a.attrs["href"], a.text()) for a in footer.find_all("a")],
            [("/rules#install", "Install the Pi plugin"), ("/register", "Register")],
        )
        self.assertEqual(
            steps,
            [
                "Install the Pi plugin",
                "/golf-login <key> with the key from Register",
                "Solve it in a new Pi session, in a new, empty folder",
                "/golf-submit help_me_unpack",
            ],
        )

    def test_ranked_in_order_and_equal_scores_share_a_rank(self):
        self.upload("dave", session("d", tokens=900, prompts=9, chars=900), minutes_ago=50)
        alice = self.upload("alice", session("a", tokens=12345, prompts=2, chars=40, tool_calls=7), minutes_ago=40)
        self.upload("bob", session("b", tokens=12345, prompts=2, chars=40), minutes_ago=30)
        self.upload("carol", session("c", tokens=12345, prompts=2, chars=41), minutes_ago=20)
        self.upload("erin", session("e", tokens=12345, prompts=3, chars=1), minutes_ago=10)
        page = self.page("/")
        self.assertEqual(
            self.table(page, "ranked"),
            [
                ["Rank", "Player", "Model", "Tokens", "Prompts", "Chars", "Tool calls", "Submitted"],
                ["1", "dave", "openai/gpt-5.5", "900", "9", "900", "3", "50 min ago"],
                # Equal scores: one rank, the first submitted first.
                ["2", "alice", "openai/gpt-5.5", "12,345", "2", "40", "7", "40 min ago"],
                ["2", "bob", "openai/gpt-5.5", "12,345", "2", "40", "3", "30 min ago"],
                ["4", "carol", "openai/gpt-5.5", "12,345", "2", "41", "3", "20 min ago"],  # more characters
                ["5", "erin", "openai/gpt-5.5", "12,345", "3", "1", "3", "10 min ago"],  # more prompts
            ],
        )
        # Each row links to its submission.
        links = [a.attrs["href"] for a in page.find("table", id="ranked").find_all("a")]
        self.assertEqual(len(links), 5)
        self.assertEqual(links[1], link(alice["url"]))
        self.assertIsNone(self.table(page, "unranked"))

    def test_each_players_best_ranked_session_only(self):
        self.upload("alice", session("a1", tokens=5000))
        best = self.upload("alice", session("a2", tokens=3000))
        self.upload("alice", session("a3", tokens=3000))  # as good, but later
        self.upload("alice", session("a4", tokens=4000))
        self.upload("alice", session("a5", tokens=100, reasons=["not_solved"]))  # fewer tokens, unranked
        self.upload("bob", session("b1", tokens=3500))
        page = self.page("/")
        rows = self.table(page, "ranked")[1:]
        self.assertEqual([(row[0], row[1], row[3]) for row in rows], [("1", "alice", "3,000"), ("2", "bob", "3,500")])
        self.assertEqual(page.find("table", id="ranked").find_all("a")[0].attrs["href"], link(best["url"]))
        # Alice has a ranked row, so her unranked attempt is not listed.
        self.assertIsNone(self.table(page, "unranked"))

    def test_unranked_is_each_unranked_players_latest_attempt(self):
        self.upload("bob", session("b1", reasons=["not_solved"]), minutes_ago=30)
        latest = self.upload(
            "bob",
            session("b2", reasons=["model_switched", "usage_not_recorded"], models=("a/one", "b/two")),
            minutes_ago=10,
        )
        self.upload("carol", session("c1", reasons=["missing_usage"]), minutes_ago=20)
        self.upload("dave", session("d1"), minutes_ago=50)
        self.upload("dave", session("d2", reasons=["not_solved"]), minutes_ago=5)  # dave is ranked
        self.upload("erin", session("e1", reasons=["not_solved", "model_mismatch", "folder_reused"]), minutes_ago=60)
        page = self.page("/")
        self.assertEqual(
            self.table(page, "unranked"),
            [
                ["Player", "Reasons", "Submitted"],
                # Latest first; the reasons that unranked it, in plain English, without warnings.
                ["bob", "Model switched", "10 min ago"],
                ["carol", "Tokens unknown", "20 min ago"],
                ["erin", "Folder reused, Wrong model, Not solved", "1 hour ago"],
            ],
        )
        self.assertEqual(page.find("table", id="unranked").find_all("a")[0].attrs["href"], link(latest["url"]))
        self.assertEqual([row[1] for row in self.table(page, "ranked")[1:]], ["dave"])

    def test_latest_follows_resubmission(self):
        self.upload("bob", session("b1", reasons=["not_solved"]), minutes_ago=30)
        self.upload("bob", session("b2", reasons=["missing_usage"]), minutes_ago=20)
        # Resubmitting the first session makes it the latest.
        content = session("b1", reasons=["not_solved", "model_mismatch"], prompts=3)
        self.upload("bob", content, minutes_ago=10)
        self.assertEqual(
            self.table(self.page("/"), "unranked")[1:], [["bob", "Wrong model, Not solved", "10 min ago"]]
        )

    def test_every_reason_has_plain_english(self):
        self.assertEqual(set(pages.REASONS), submissions.UNRANKING_REASONS | submissions.WARNING_REASONS)
        for code, (label, detail) in pages.REASONS.items():
            with self.subTest(code=code):
                self.assertNotIn("_", label + detail)
                self.assertTrue(detail.endswith("."))

    def test_model_column_only_for_any_model_problems(self):
        with mock.patch.object(problems, "PROBLEMS", (*problems.PROBLEMS, FIXED)):
            self.upload("alice", session("a1", models=("anthropic/claude-sonnet-4-5",)), minutes_ago=3)
            self.upload("alice", session("a2", models=("openai/gpt-5.5",)), minutes_ago=2, problem="fixed_setup")
            any_model = self.page("/problems/help_me_unpack")
            fixed = self.page("/problems/fixed_setup")
        self.assertEqual(
            self.table(any_model, "ranked"),
            [
                ["Rank", "Player", "Model", "Tokens", "Prompts", "Chars", "Tool calls", "Submitted"],
                ["1", "alice", "anthropic/claude-sonnet-4-5", "1,000", "2", "40", "3", "3 min ago"],
            ],
        )
        self.assertEqual(
            self.table(fixed, "ranked"),
            [
                ["Rank", "Player", "Tokens", "Prompts", "Chars", "Tool calls", "Submitted"],
                ["1", "alice", "1,000", "2", "40", "3", "2 min ago"],
            ],
        )
        self.assertNotIn("openai/gpt-5.5", fixed.find("table", id="ranked").text())

    def test_tables_are_labelled_and_have_header_cells(self):
        self.upload("alice", session("a1"))
        self.upload("bob", session("b1", reasons=["not_solved"]))
        page = self.page("/")
        for name, heading in (("ranked", "Ranked"), ("unranked", "Unranked")):
            with self.subTest(table=name):
                table = page.find("table", id=name)
                self.assertTrue(all(th.attrs.get("scope") == "col" for th in table.find("thead").find_all("th")))
                # The player is each row's header.
                for row in table.find("tbody").find_all("tr"):
                    self.assertEqual([th.attrs.get("scope") for th in row.find_all("th")], ["row"])
                # Inside a focusable region named by its heading, so it can scroll from the keyboard.
                region = table.parent
                self.assertEqual((region.attrs["role"], region.attrs["tabindex"]), ("region", "0"))
                self.assertEqual(page.find(id=region.attrs["aria-labelledby"]).text(), heading)
                time = table.find("time")
                self.assertEqual((time.attrs["datetime"], time.text()), (NOW.isoformat(timespec="seconds"), "just now"))

    def test_empty_states(self):
        page = self.page("/")
        self.assertEqual(page.find("p", class_="empty").text(), "No submissions yet. Be the first: the steps are below.")
        self.assertEqual(page.find_all("table"), [])
        self.assertEqual(len(page.find_all("ol", class_="steps")), 1)
        self.upload("bob", session("b1", reasons=["not_solved"]))
        page = self.page("/")
        self.assertEqual(page.find("p", class_="empty").text(), "No ranked attempts yet.")
        self.assertIsNone(self.table(page, "ranked"))
        self.assertEqual(self.table(page, "unranked")[1:], [["bob", "Not solved", "just now"]])

    def test_home_is_the_first_listed_problems_board(self):
        with mock.patch.object(problems, "PROBLEMS", (*problems.PROBLEMS, UNSET, FIXED)):
            self.upload("alice", session("a1"))
            self.upload("bob", session("b1"), problem="fixed_setup")
            home = self.client.get("/")
            self.assertEqual(home.text, self.client.get("/problems/help_me_unpack").text)
            fixed = self.page("/problems/fixed_setup")
            # Not listed yet, so no board.
            self.assertEqual(self.client.get("/problems/not_set_yet").status_code, 404)
        page = parse(home.text)
        self.assertEqual([row[1] for row in self.table(page, "ranked")[1:]], ["alice"])
        others = page.find("p", class_="other-boards")
        self.assertEqual([(a.attrs["href"], a.text()) for a in others.find_all("a")], [("/problems/fixed_setup", "Fixed setup")])
        self.assertEqual(fixed.find("h1").text(), "Fixed setup")
        self.assertEqual([row[1] for row in self.table(fixed, "ranked")[1:]], ["bob"])
        others = fixed.find("p", class_="other-boards")
        self.assertEqual(
            [(a.attrs["href"], a.text()) for a in others.find_all("a")], [("/problems/help_me_unpack", "Help me unpack")]
        )
        # With one problem there are no others to link.
        self.assertEqual(self.page("/").find_all("p", class_="other-boards"), [])

    def test_no_problems_listed(self):
        with mock.patch.object(problems, "PROBLEMS", (UNSET,)):
            page = self.page("/")
        self.assertEqual(page.find("h1").text(), "Board")
        self.assertIn("No problems are open yet.", page.find("main").text())
        self.assertEqual(page.find_all("meta", http_equiv="refresh"), [])

    def test_unknown_problem(self):
        for path in ("/problems/nope", "/problems/Help_Me_Unpack", "/problems/help_me_unpack.json"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.headers["content-type"], "text/html; charset=utf-8")
                self.assertEqual(parse(response.text).find("h1").text(), "Not found")

    def test_nav_on_every_page(self):
        reply = self.upload("alice", session("a1"))
        current = {  # path: the nav link marked as the current page
            "/": "/", "/problems/help_me_unpack": "/", "/rules": "/rules", "/register": "/register",
            link(reply["url"]): None, "/problems/nope": None, "/submissions/999": None,
        }
        for path, expected in current.items():
            with self.subTest(path=path):
                nav = parse(self.client.get(path).text).find("nav")
                links = [(a.attrs["href"], a.text()) for a in nav.find_all("a")]
                self.assertEqual(links, [("/", "Board"), ("/rules", "Rules"), ("/register", "Register")])
                marked = [a.attrs["href"] for a in nav.find_all("a", aria_current="page")]
                self.assertEqual(marked, [expected] if expected else [])

    def test_only_public_fields(self):
        content = session("session-id-1234", cwd="/home/alice/secret-folder")
        self.upload("alice", content)
        self.upload("bob", session("session-id-5678", reasons=["not_solved"], cwd="/home/bob/other-folder"))
        html = self.client.get("/").text
        for private in (
            "/home/alice/secret-folder", "/home/bob/other-folder", "session-id-1234", "session-id-5678",
            "alice_hackattic", "bob_hackattic", "secret prompt", hashlib.sha256(content).hexdigest(),
            *self.keys.values(),
        ):
            with self.subTest(private=private):
                self.assertNotIn(private, html)

    def test_text_is_escaped(self):
        self.upload("alice", session("a1", models=("evil/<script>alert(1)</script>",)))
        html = self.client.get("/").text
        self.assertNotIn("<script>", html)
        self.assertIn("evil/&lt;script&gt;alert(1)&lt;/script&gt;", html)


class TextTest(unittest.TestCase):
    def test_ago(self):
        cases = (
            (-5, "just now"), (0, "just now"), (0.9, "just now"), (1, "1 min ago"), (59, "59 min ago"),
            (60, "1 hour ago"), (119, "1 hour ago"), (120, "2 hours ago"), (24 * 60 - 1, "23 hours ago"),
            (24 * 60, "1 day ago"), (3 * 24 * 60, "3 days ago"),
        )
        for minutes, text in cases:
            with self.subTest(minutes=minutes):
                when = (NOW - timedelta(minutes=minutes)).isoformat(timespec="seconds")
                self.assertEqual(pages.ago(when, NOW), text)

    def test_numbers(self):
        self.assertEqual([pages.number(n) for n in (0, 999, 1000, 1234567, None)], ["0", "999", "1,000", "1,234,567", "unknown"])
        self.assertEqual(pages.names(["a/b", "c/d"]), "a/b, c/d")
        self.assertEqual(pages.names([]), "none recorded")


class ConfiguredCounterBoardTest(unittest.TestCase):
    """Mixed uploads, scored by the counter submissions.py imports (server.counter):
    the board agrees with the replies."""

    def test_board_matches_the_replies(self):
        settings = Settings(data_dir=Path(self.enterContext(tempfile.TemporaryDirectory())))
        client = self.enterContext(TestClient(create_app(settings)))
        keys = {}
        with closing(db.connect(settings.db_path)) as conn:
            for n in range(18):
                keys[f"player{n}"] = users.create_user(conn, f"player{n}", f"hackattic{n}")
        replies = []
        for n in range(30):
            # Four players with four sessions each, then fourteen with one each.
            player = f"player{n % 4 if n < 16 else n - 12}"
            header = {"type": "session", "version": 3, "id": f"s-{n}", "timestamp": "2026-10-11T10:00:00.000Z",
                      "cwd": f"/work/{n}"}
            when = (NOW + timedelta(minutes=n)).isoformat(timespec="seconds")
            with mock.patch.object(submissions, "utc_now", return_value=when):
                response = client.post(
                    "/api/v1/submissions",
                    headers={"Authorization": f"Bearer {keys[player]}"},
                    data={"problem": "help_me_unpack"},
                    files={"session": ("session.jsonl", json.dumps(header) + "\n")},
                )
            self.assertEqual(response.status_code, 200)
            replies.append((n, player, response.json()))

        def score(reply):
            metrics = reply["metrics"]
            return (metrics["total_tokens"], metrics["prompts"], metrics["chars_typed"])

        best = {}
        for n, player, reply in sorted(
            (item for item in replies if item[2]["status"] == "ranked"), key=lambda item: (score(item[2]), item[0])
        ):
            best.setdefault(player, (n, reply))
        expected_ranked = sorted(best.items(), key=lambda item: (score(item[1][1]), item[1][0]))
        latest = {}
        for n, player, reply in reversed(replies):
            if player not in best:
                latest.setdefault(player, reply)

        page = parse(client.get("/").text)
        ranked = page.find_all("table", id="ranked")
        rows = ranked[0].find("tbody").find_all("tr") if ranked else []
        self.assertEqual(
            [(row.find("th").text(), row.find("a").attrs["href"]) for row in rows],
            [(player, link(reply["url"])) for player, (n, reply) in expected_ranked],
        )
        unranked = page.find_all("table", id="unranked")
        rows = unranked[0].find("tbody").find_all("tr") if unranked else []
        self.assertEqual(
            [(row.find("th").text(), row.find("a").attrs["href"]) for row in rows],
            [(player, link(reply["url"])) for player, reply in latest.items()],
        )


if __name__ == "__main__":
    unittest.main()
