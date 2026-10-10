"""The problem config."""

import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from server import problems

SPEC = Path(__file__).resolve().parents[2] / "docs" / "spec.md"
UNSET = problems.Problem(
    slug="not_set_yet",
    title="Not set yet",
    challenge_url="https://hackattic.com/challenges/not_set_yet",
    instructions=("Solve it.",),
)


class ProblemConfigTest(unittest.TestCase):
    def test_help_me_unpack(self):
        problem = problems.get("help_me_unpack")
        self.assertEqual(problem.title, "Help me unpack")
        self.assertEqual(problem.challenge_url, "https://hackattic.com/challenges/help_me_unpack")
        self.assertTrue(problem.instructions)
        # Until Step 0 (plan 001) sets the real setup.
        self.assertEqual((problem.model, problem.thinking_level), ("any", "any"))

    def test_unknown_slugs(self):
        for slug in ("nope", "Help_Me_Unpack", "", None, 3):
            with self.subTest(slug=slug):
                self.assertIsNone(problems.get(slug))

    def test_unset_setup_is_neither_listed_nor_accepted(self):
        half_set = (
            replace(UNSET, slug="model_only", model="any"),
            replace(UNSET, slug="level_only", thinking_level="low"),
        )
        with mock.patch.object(problems, "PROBLEMS", (*problems.PROBLEMS, UNSET, *half_set)):
            self.assertEqual([problem.slug for problem in problems.listed()], ["help_me_unpack"])
            for slug in ("not_set_yet", "model_only", "level_only"):
                with self.subTest(slug=slug):
                    self.assertIsNone(problems.get(slug))

    @unittest.skipUnless(SPEC.is_file(), "docs/spec.md is not here")
    def test_rules_mirror_the_spec(self):
        section = SPEC.read_text(encoding="utf-8").split("## Rules for students\n", 1)[1].split("\n## ", 1)[0]
        rules = [line.strip().replace("`", "") for line in section.splitlines() if line.strip()]
        self.assertEqual(list(problems.RULES), rules)
        self.assertEqual(problems.RULES_VERSION, "mvp-1")


if __name__ == "__main__":
    unittest.main()
