"""The problem config, and GET /api/v1/problems per docs/spec.md "Contract: problem list"."""

import tempfile
import unittest
import uuid
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from server import problems
from server.app import create_app
from server.config import Settings

SPEC = Path(__file__).resolve().parents[2] / "docs" / "spec.md"
GOOD = problems.get("help_me_unpack")
ZIP = problems.get("brute_force_zip")
UNSET = problems.Problem(
    slug="not_set_yet",
    title="Not set yet",
    challenge_url="https://hackattic.com/challenges/not_set_yet",
    instructions=("Solve it.",),
)
FIXED = replace(
    UNSET,
    slug="fixed_setup",
    challenge_url="https://hackattic.com/challenges/fixed_setup",
    model="openai/gpt-5.5",
    thinking_level="low",
)


class ProblemConfigTest(unittest.TestCase):
    def test_help_me_unpack(self):
        problem = problems.get("help_me_unpack")
        self.assertEqual(problem.title, "Help me unpack")
        self.assertEqual(problem.challenge_url, "https://hackattic.com/challenges/help_me_unpack")
        self.assertTrue(problem.instructions)
        # Step 0 (plan 001) kept any model and any thinking level for Monday.
        self.assertEqual((problem.model, problem.thinking_level), ("any", "any"))

    def test_brute_force_zip(self):
        problem = problems.get("brute_force_zip")
        self.assertEqual(problem.title, "Brute force ZIP")
        self.assertEqual(problem.challenge_url, "https://hackattic.com/challenges/brute_force_zip")
        self.assertTrue(problem.instructions)
        self.assertEqual((problem.model, problem.thinking_level), ("any", "any"))
        # Listed after help_me_unpack, so the home page stays help_me_unpack's board.
        self.assertEqual([listed.slug for listed in problems.listed()][:2], ["help_me_unpack", "brute_force_zip"])

    def test_exam_problems(self):
        # CS437 exam: listed only for its sitting, GitHub Copilot (Auto) only.
        listed = {problem.slug: problem for problem in problems.listed()}
        self.assertEqual((listed["touch_tone_dialing"].model, listed["touch_tone_dialing"].thinking_level),
                         ("github-copilot/*", "any"))
        self.assertNotIn("basic_face_detection", listed)

    def test_unknown_slugs(self):
        for slug in ("nope", "Help_Me_Unpack", "", None, 3):
            with self.subTest(slug=slug):
                self.assertIsNone(problems.get(slug))

    def test_unset_setup_is_neither_listed_nor_accepted(self):
        half_set = (
            replace(UNSET, slug="model_only", model="any"),
            replace(UNSET, slug="level_only", thinking_level="low"),
        )
        with mock.patch.object(problems, "PROBLEMS", (GOOD, UNSET, *half_set)):
            self.assertEqual([problem.slug for problem in problems.listed()], ["help_me_unpack"])
            for slug in ("not_set_yet", "model_only", "level_only"):
                with self.subTest(slug=slug):
                    self.assertIsNone(problems.get(slug))

    @unittest.skipUnless(SPEC.is_file(), "docs/spec.md is not here")
    def test_rules_mirror_the_spec(self):
        section = SPEC.read_text(encoding="utf-8").split("## Rules for students\n", 1)[1].split("\n## ", 1)[0]
        rules = [line.strip().replace("`", "") for line in section.splitlines() if line.strip()]
        self.assertEqual(list(problems.RULES), rules)
        self.assertEqual(problems.RULES_VERSION, "mvp-3")


class ProblemListTest(unittest.TestCase):
    def get_list(self, headers=None):
        settings = Settings(data_dir=Path(self.enterContext(tempfile.TemporaryDirectory())))
        client = self.enterContext(TestClient(create_app(settings)))
        return client.get("/api/v1/problems", headers=headers or {})

    def test_populated(self):
        response = self.get_list()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/json")
        self.assertEqual(
            response.json(),
            {
                "rules_version": "mvp-3",
                "rules": list(problems.RULES),
                "problems": [
                    {
                        "slug": "help_me_unpack",
                        "title": "Help me unpack",
                        "challenge_url": "https://hackattic.com/challenges/help_me_unpack",
                        "instructions": list(GOOD.instructions),
                        "model": "any",
                        "thinking_level": "any",
                    },
                    {
                        "slug": "brute_force_zip",
                        "title": "Brute force ZIP",
                        "challenge_url": "https://hackattic.com/challenges/brute_force_zip",
                        "instructions": list(ZIP.instructions),
                        "model": "any",
                        "thinking_level": "any",
                    },
                    {
                        "slug": "touch_tone_dialing",
                        "title": "Touch-Tone dialing",
                        "challenge_url": "https://hackattic.com/challenges/touch_tone_dialing",
                        "instructions": list(problems.get("touch_tone_dialing").instructions),
                        "model": "github-copilot/*",
                        "thinking_level": "any",
                    },
                ],
            },
        )
        # The bytes check() measured at startup.
        self.assertEqual(response.content, problems.problem_list_json())
        self.assertLessEqual(len(response.content), 64 * 1024)

    def test_no_key_needed(self):
        for headers in ({}, {"Authorization": "Bearer not-a-key"}, {"Authorization": f"Bearer {uuid.uuid4()}"}):
            with self.subTest(headers=headers):
                response = self.get_list(headers)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    [problem["slug"] for problem in response.json()["problems"]],
                    [problem.slug for problem in problems.listed()],
                )

    def test_empty_list(self):
        with mock.patch.object(problems, "PROBLEMS", ()):
            response = self.get_list()
        self.assertEqual(response.status_code, 200)
        # The rules are still there.
        self.assertEqual(
            response.json(), {"rules_version": "mvp-3", "rules": list(problems.RULES), "problems": []}
        )

    def test_only_set_problems_are_listed(self):
        with mock.patch.object(problems, "PROBLEMS", (GOOD, UNSET, FIXED)):
            listed = self.get_list().json()["problems"]
        self.assertEqual(
            [(problem["slug"], problem["model"], problem["thinking_level"]) for problem in listed],
            [("help_me_unpack", "any", "any"), ("fixed_setup", "openai/gpt-5.5", "low")],
        )


class LimitsTest(unittest.TestCase):
    """problems.check(): the problem list's safety limits, checked at startup."""

    def check_config(self, *entries, rules=None, rules_version=None):
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(problems, "PROBLEMS", entries))
            if rules is not None:
                stack.enter_context(mock.patch.object(problems, "RULES", rules))
            if rules_version is not None:
                stack.enter_context(mock.patch.object(problems, "RULES_VERSION", rules_version))
            problems.check()

    def assert_invalid(self, *entries, **config):
        with self.assertRaises(problems.InvalidConfig):
            self.check_config(*entries, **config)

    def test_the_config_keeps_the_limits(self):
        problems.check()
        self.check_config()  # an empty list is valid
        self.check_config(GOOD, UNSET, FIXED)

    def test_plain_text_only(self):
        for text in (
            "\x1b[31mred", "two\nlines", "tab\there", "nul\x00", "del\x7f", "c1\x85", "csi\x9b",
            "\u202eevil", "\u2066isolated", "lone \ud800", "<b>bold</b>", "</p>", "<!-- note -->",
            "<script>alert(1)</script>",
        ):
            with self.subTest(text=text):
                self.assert_invalid(replace(GOOD, title=text))
                self.assert_invalid(replace(GOOD, instructions=("Fine.", text)))
                self.assert_invalid(GOOD, rules=(text,))
        # Comparisons, quotes, ampersands and non-ASCII letters are plain text.
        self.check_config(replace(GOOD, title='a < b, "quoted" & café'))

    def test_string_length(self):
        # Characters (code points), as the plugin counts them, not bytes.
        self.check_config(replace(GOOD, title="x" * 1000, instructions=("é" * 1000,)), rules=("😀" * 1000,))
        self.assert_invalid(replace(GOOD, title="x" * 1001))
        self.assert_invalid(replace(GOOD, instructions=("x" * 1001,)))
        self.assert_invalid(GOOD, rules=("x" * 1001,))

    def test_body_size(self):
        # Every string within its own limit, but over 64 KB in all.
        self.assert_invalid(replace(GOOD, instructions=("x" * 1000,) * 66))
        self.check_config(replace(GOOD, instructions=("x" * 1000,) * 60))

    def test_challenge_url(self):
        for url in (
            "http://hackattic.com/challenges/help_me_unpack",
            "https://hackattic.com/challenges/help_me_unpack/",
            "https://www.hackattic.com/challenges/help_me_unpack",
            "https://hackattic.com/challenges/other_problem",
            "https://hackattic.com/challenges/HELP_ME_UNPACK",
            " https://hackattic.com/challenges/help_me_unpack",
        ):
            with self.subTest(url=url):
                self.assert_invalid(replace(GOOD, challenge_url=url))

    def test_slugs(self):
        for slug in ("Help_me_unpack", "help-me-unpack", "help__me", "_help", "help_", "help me", ""):
            with self.subTest(slug=slug):
                self.assert_invalid(replace(GOOD, slug=slug, challenge_url=f"https://hackattic.com/challenges/{slug}"))
        self.assert_invalid(GOOD, GOOD)

    def test_setup_shapes(self):
        for model in ("any", "openai/gpt-5.5", "anthropic/claude-sonnet-4-5", None):
            self.check_config(replace(GOOD, model=model))
        for model in ("gpt-5.5", "openai/", "/gpt-5.5", "openai/gpt 5", "", "Any "):
            with self.subTest(model=model):
                self.assert_invalid(replace(GOOD, model=model))
        for level in ("any", "low", "xhigh", None):
            self.check_config(replace(GOOD, thinking_level=level))
        for level in ("High", "very high", "1", ""):
            with self.subTest(level=level):
                self.assert_invalid(replace(GOOD, thinking_level=level))

    def test_rules_and_lists(self):
        for version in ("", " ", "mvp\n1"):
            with self.subTest(version=version):
                self.assert_invalid(GOOD, rules_version=version)
        self.assert_invalid(GOOD, rules="One rule, not a list.")
        self.assert_invalid(replace(GOOD, instructions="One line, not a list."))

    def test_problems_not_listed_yet_are_checked_too(self):
        self.assert_invalid(GOOD, replace(UNSET, title="<b>Later</b>"))

    def test_the_app_refuses_a_bad_config(self):
        settings = Settings(data_dir=Path(self.enterContext(tempfile.TemporaryDirectory())))
        with mock.patch.object(problems, "PROBLEMS", (replace(GOOD, title="\x1b[2J"),)):
            with self.assertRaises(problems.InvalidConfig):
                create_app(settings)


if __name__ == "__main__":
    unittest.main()
