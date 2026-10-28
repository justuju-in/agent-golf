"""The submission page: GET /submissions/<id> (plan 002 step 3.2)."""

import hashlib
import unittest
from unittest import mock
from urllib.parse import urlsplit

from server import pages, problems, submissions
from server.tests.dom import parse
from server.tests.test_board import FIXED, PageTestCase, link, session


class SubmissionPageTest(PageTestCase):
    def open(self, reply):
        """The page the reply's url links to, parsed."""
        return self.page(link(reply["url"]))

    def standing(self, reply):
        return self.open(reply).find("p", class_="standing").text()

    def numbers(self, page):
        boxes = page.find("dl", class_="numbers").find_all("div")
        return {box.find("dt").text(): box.find("dd").text() for box in boxes}

    def facts(self, page):
        facts = page.find("dl", class_="facts")
        return dict(zip((dt.text() for dt in facts.find_all("dt")), (dd.text() for dd in facts.find_all("dd"))))

    def reasons(self, page):
        found = page.find_all("ul", class_="reasons")
        return [item.text() for item in found[0].find_all("li")] if found else None

    def test_the_replys_url_opens_it(self):
        content = session(
            "a1", tokens=15147, prompts=4, chars=845, tool_calls=19, models=("standin/model-a",), levels=("medium",)
        )
        reply = self.upload("alice", content, minutes_ago=5)
        self.assertEqual(urlsplit(reply["url"]).netloc, "golf.example")
        page = self.open(reply)
        self.assertEqual(page.find("title").text(), "Submission by alice – Agent Golf")
        self.assertEqual(page.find("h1").text(), "Submission by alice")
        self.assertEqual(page.find("p", class_="standing").text(), "Ranked #1")
        self.assertEqual(
            self.numbers(page), {"Tokens": "15,147", "Prompts": "4", "Characters": "845", "Tool calls": "19"}
        )
        self.assertEqual(
            self.facts(page),
            {
                "Problem": "Help me unpack",
                "Model": "standin/model-a",
                "Thinking level": "medium",
                "Solved": "Yes",
                "Submitted": "11 Oct 2026, 11:55 UTC (5 min ago)",
            },
        )
        facts = page.find("dl", class_="facts")
        self.assertEqual(facts.find("a").attrs["href"], "/problems/help_me_unpack")
        self.assertEqual(facts.find("time").attrs["datetime"], "2026-10-11T11:55:00+00:00")
        self.assertIsNone(self.reasons(page))
        self.assertEqual(page.find("h2").text(), "Reasons")
        self.assertIn("None.", page.find("main").text())
        # Only boards reload themselves.
        self.assertEqual(page.find_all("meta", http_equiv="refresh"), [])

    def test_standing(self):
        bob = self.upload("bob", session("b1", tokens=100), minutes_ago=50)
        carol = self.upload("carol", session("c1", tokens=100), minutes_ago=40)  # the same score
        alice_best = self.upload("alice", session("a1", tokens=200), minutes_ago=30)
        alice_other = self.upload("alice", session("a2", tokens=300), minutes_ago=20)
        alice_unranked = self.upload("alice", session("a3", tokens=50, reasons=["not_solved"]), minutes_ago=10)
        dave = self.upload("dave", session("d1", reasons=["missing_usage"]))
        expected = (
            (bob, "Ranked #1"),
            (carol, "Ranked #1"),
            (alice_best, "Ranked #3"),
            (alice_other, "Ranked (not your best attempt)"),
            (alice_unranked, "Unranked"),
            (dave, "Unranked"),
        )
        for reply, standing in expected:
            with self.subTest(url=reply["url"]):
                self.assertEqual(self.standing(reply), standing)

    def test_tokens_unknown(self):
        page = self.open(self.upload("alice", session("a1", reasons=["missing_usage"])))
        self.assertEqual(self.numbers(page)["Tokens"], "unknown")
        self.assertEqual(page.find("p", class_="standing").text(), "Unranked")

    def test_models_and_thinking_levels_always(self):
        # The fixed-model board has no model column; the page still shows the model.
        with mock.patch.object(problems, "PROBLEMS", (*problems.PROBLEMS, FIXED)):
            reply = self.upload("alice", session("a1"), problem="fixed_setup")
            page = self.open(reply)
        facts = self.facts(page)
        self.assertEqual((facts["Problem"], facts["Model"], facts["Thinking level"]), ("Fixed setup", "openai/gpt-5.5", "low"))
        # Several, and none.
        several = self.upload(
            "bob", session("b1", reasons=["model_switched"], models=("a/one", "b/two"), levels=("high", "low"))
        )
        facts = self.facts(self.open(several))
        self.assertEqual((facts["Models"], facts["Thinking levels"]), ("a/one, b/two", "high, low"))
        facts = self.facts(self.open(self.upload("carol", session("c1", models=(), levels=()))))
        self.assertEqual((facts["Model"], facts["Thinking level"]), ("none recorded", "none recorded"))

    def test_solved(self):
        self.assertEqual(self.facts(self.open(self.upload("alice", session("a1"))))["Solved"], "Yes")
        unsolved = self.upload("alice", session("a2", reasons=["not_solved"]))
        self.assertEqual(self.facts(self.open(unsolved))["Solved"], "No")

    def test_reasons_in_plain_english_and_warnings_marked(self):
        reply = self.upload(
            "alice", session("a1", reasons=["usage_not_recorded", "not_solved", "custom_setup", "model_mismatch"])
        )
        page = self.open(reply)
        # What unranked it first, then the warnings.
        self.assertEqual(
            self.reasons(page),
            [
                f"Wrong model. {pages.reason_detail('model_mismatch')}",
                f"Not solved. {pages.reason_detail('not_solved')}",
                f"Warning: Custom setup. {pages.reason_detail('custom_setup')} Warnings do not unrank.",
                f"Warning: Usage not recorded. {pages.reason_detail('usage_not_recorded')} Warnings do not unrank.",
            ],
        )
        warnings = page.find("ul", class_="reasons").find_all("li", class_="reason-warning")
        self.assertEqual(len(warnings), 2)
        self.assertNotIn("_", page.find("ul", class_="reasons").text())
        # A warning alone leaves it ranked.
        page = self.open(self.upload("bob", session("b1", reasons=["inconsistent_log"])))
        self.assertEqual(page.find("p", class_="standing").text(), "Ranked #1")
        self.assertEqual(
            self.reasons(page),
            [f"Warning: Inconsistent log. {pages.reason_detail('inconsistent_log')} Warnings do not unrank."],
        )

    def test_folder_reused(self):
        self.upload("alice", session("a1", cwd="/home/alice/attempt"))
        page = self.open(self.upload("alice", session("a2", cwd="/home/alice/attempt")))
        self.assertEqual(page.find("p", class_="standing").text(), "Unranked")
        self.assertEqual(self.reasons(page), [f"Folder reused. {pages.reason_detail('folder_reused')}"])
        self.assertNotIn("/home/alice", page.find("main").text())

    def test_only_public_fields(self):
        content = session("session-id-1234", cwd="/home/alice/secret-folder")
        reply = self.upload("alice", content)
        html = self.client.get(link(reply["url"])).text
        for private in (
            "/home/alice/secret-folder", "secret-folder", "session-id-1234", "alice_hackattic", "secret prompt",
            hashlib.sha256(content).hexdigest(), self.keys["alice"],
        ):
            with self.subTest(private=private):
                self.assertNotIn(private, html)

    def test_public_prompts_only_where_the_problem_allows(self):
        public = problems.Problem(
            slug="open_prompts", title="Open prompts", challenge_url="https://hackattic.com/challenges/open_prompts",
            instructions=("Solve it.",), model="any", thinking_level="any", prompts_public=True,
        )
        with mock.patch.object(problems, "PROBLEMS", (*problems.PROBLEMS, public)):
            reply = self.upload("alice", session("p1", cwd="/home/alice/hidden"), problem="open_prompts")
            html = self.client.get(link(reply["url"])).text
        self.assertIn("secret prompt of p1", html)
        for private in ("/home/alice/hidden", "alice_hackattic", self.keys["alice"]):
            with self.subTest(private=private):
                self.assertNotIn(private, html)
        # Every other problem keeps its prompts private (test_only_public_fields).

    def test_published_prompts_are_scrubbed(self):
        text = ("GET https://hackattic.com/x?access_token=abc123def456 then export HACKATTIC_TOKEN=zzz999yyy "
                "key sk-or-v1-0123456789abcdefghijklmn and ghp_0123456789abcdefghijklmnop")
        out = submissions.scrub(text)
        for secret in ("abc123def456", "zzz999yyy", "sk-or-v1-0123", "ghp_0123"):
            with self.subTest(secret=secret):
                self.assertNotIn(secret, out)
        self.assertIn("access_token=<token>", out)

    def test_unknown_submission(self):
        self.upload("alice", session("a1"))
        for path in ("/submissions/999", "/submissions/0", f"/submissions/{2**64}"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.headers["content-type"], "text/html; charset=utf-8")
                self.assertEqual(parse(response.text).find("h1").text(), "Not found")
        for path in ("/submissions/-1", "/submissions/abc", "/submissions/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_problem_no_longer_listed(self):
        with mock.patch.object(problems, "PROBLEMS", (*problems.PROBLEMS, FIXED)):
            reply = self.upload("alice", session("a1"), problem="fixed_setup")
        page = self.open(reply)
        self.assertEqual(self.facts(page)["Problem"], "fixed_setup")
        self.assertEqual(page.find("dl", class_="facts").find_all("a"), [])
        self.assertEqual(page.find("p", class_="standing").text(), "Ranked #1")

    def test_text_is_escaped(self):
        page = self.client.get(link(self.upload("alice", session("a1", models=("evil/<b>bold</b>",)))["url"]))
        self.assertNotIn("<b>bold</b>", page.text)
        self.assertIn("evil/&lt;b&gt;bold&lt;/b&gt;", page.text)


if __name__ == "__main__":
    unittest.main()
