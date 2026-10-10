"""The stand-in counter (deleted with it in plan 002 step 4.1)."""

import json
import unittest

from server import standin_counter
from server.standin_counter import NotPiLogError, score

ANY = {"model": "any", "thinking_level": "any"}
FIXED = {"model": "openai/gpt-5.5", "thinking_level": "low"}
METRICS = {"total_tokens", "prompts", "chars_typed", "tool_calls", "models", "thinking_levels", "solved"}


def session(n, session_id="s-1", cwd="/work/attempt-1"):
    """A small Pi-like log; `n` changes the bytes, so the made-up result changes too."""
    lines = [
        {"type": "session", "version": 3, "id": session_id, "timestamp": "2026-10-10T11:16:02.463Z", "cwd": cwd},
        {"type": "message", "id": "a1", "parentId": None, "message": {"role": "user", "content": f"try {n}"}},
    ]
    return "".join(json.dumps(line) + "\n" for line in lines)


def first(predicate, agreed=ANY, prior_folders=frozenset()):
    """The first of session(0), session(1), ... whose result passes `predicate`."""
    for n in range(500):
        result = score(session(n), "help_me_unpack", agreed, set(prior_folders))
        if predicate(result):
            return session(n), result
    raise AssertionError("no session gave that result")


class StandinCounterTest(unittest.TestCase):
    def test_reason_codes_match_the_spec(self):
        self.assertEqual(
            standin_counter.UNRANKING_REASONS,
            {"not_solved", "model_mismatch", "thinking_level_mismatch", "model_switched",
             "folder_reused", "missing_usage"},
        )
        self.assertEqual(
            standin_counter.WARNING_REASONS, {"custom_setup", "inconsistent_log", "usage_not_recorded"}
        )

    def test_shape_and_header(self):
        for n in range(50):
            with self.subTest(n=n):
                result = score(session(n), "help_me_unpack", ANY, set())
                self.assertEqual(set(result), {"session_id", "cwd", "metrics", "reasons"})
                self.assertEqual((result["session_id"], result["cwd"]), ("s-1", "/work/attempt-1"))
                self.assertEqual(set(result["metrics"]), METRICS)
                self.assertEqual(result["reasons"], sorted(result["reasons"]))
                self.assertLessEqual(
                    set(result["reasons"]),
                    standin_counter.UNRANKING_REASONS | standin_counter.WARNING_REASONS,
                )
                # The same text always gives the same result.
                self.assertEqual(score(session(n), "help_me_unpack", ANY, set()), result)

    def test_header_without_id_or_cwd(self):
        text = json.dumps({"type": "session", "version": 3}) + "\n"
        result = score(text, "help_me_unpack", ANY, set())
        self.assertTrue(result["session_id"])
        self.assertTrue(result["cwd"])

    def test_ranked(self):
        _, result = first(lambda result: not result["reasons"])
        self.assertIsInstance(result["metrics"]["total_tokens"], int)
        self.assertTrue(result["metrics"]["solved"])
        self.assertEqual(result["metrics"]["models"], ["standin/model-a"])

    def test_unranked_with_reasons(self):
        _, result = first(lambda result: "not_solved" in result["reasons"])
        self.assertFalse(result["metrics"]["solved"])
        self.assertTrue(standin_counter.UNRANKING_REASONS & set(result["reasons"]))

    def test_warning_only(self):
        _, result = first(lambda result: result["reasons"] == ["usage_not_recorded"])
        self.assertIsInstance(result["metrics"]["total_tokens"], int)

    def test_missing_usage_has_a_null_total(self):
        _, result = first(lambda result: "missing_usage" in result["reasons"])
        self.assertIsNone(result["metrics"]["total_tokens"])
        for n in range(50):
            result = score(session(n), "help_me_unpack", ANY, set())
            with self.subTest(n=n):
                self.assertEqual(
                    result["metrics"]["total_tokens"] is None, "missing_usage" in result["reasons"]
                )

    def test_folder_reused(self):
        text, _ = first(lambda result: not result["reasons"])
        self.assertEqual(
            score(text, "help_me_unpack", ANY, {"/work/attempt-1"})["reasons"], ["folder_reused"]
        )
        self.assertEqual(score(text, "help_me_unpack", ANY, {"/work/other"})["reasons"], [])

    def test_model_switched_under_any(self):
        text, result = first(lambda result: "model_switched" in result["reasons"])
        self.assertEqual(result["reasons"], ["model_switched"])
        self.assertEqual(len(result["metrics"]["models"]), 2)
        # With a fixed setup, the same switch is a mismatch of both.
        self.assertEqual(
            score(text, "help_me_unpack", FIXED, set())["reasons"],
            ["model_mismatch", "thinking_level_mismatch"],
        )

    def test_fixed_setup_matches(self):
        _, result = first(lambda result: not result["reasons"], agreed=FIXED)
        self.assertEqual(result["metrics"]["models"], ["openai/gpt-5.5"])
        self.assertEqual(result["metrics"]["thinking_levels"], ["low"])

    def test_not_a_pi_log(self):
        header = json.dumps({"type": "session", "version": 3, "id": "s", "cwd": "/w"})
        for text in ("", "\n\n", "hello", "[1, 2]", '{"type": "message"}', f"{header}\nnot json\n", f"{header}\n[1]\n"):
            with self.subTest(text=text), self.assertRaises(NotPiLogError):
                score(text, "help_me_unpack", ANY, set())


if __name__ == "__main__":
    unittest.main()
