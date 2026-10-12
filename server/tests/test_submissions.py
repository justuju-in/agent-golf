"""POST /api/v1/submissions and GET /submissions/<id>, per docs/spec.md."""

import hashlib
import json
import logging
import os
import stat
import tempfile
import unittest
import uuid
from contextlib import closing
from pathlib import Path
from unittest import mock
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from server import db, problems, submissions, users
from server.app import create_app
from server.config import Settings

PROBLEM = problems.get("help_me_unpack")
AGREED = {"model": PROBLEM.model, "thinking_level": PROBLEM.thinking_level}
BASE_URL = "https://golf.example"
# Another listed problem, with a fixed setup, and one whose setup is not set yet.
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
MULTIPART_X = {"Content-Type": "multipart/form-data; boundary=x"}
BROKEN_MULTIPART = b"--x\r\nnot a header\r\n\r\n"


def session(session_id="s-1", cwd="/work/attempt-1", turns=1):
    """A small Pi session log; more turns give other bytes for the same session."""
    lines = [
        {"type": "session", "version": 3, "id": session_id, "timestamp": "2026-10-10T11:16:02.463Z", "cwd": cwd}
    ]
    for n in range(turns):
        lines.append(
            {
                "type": "message", "id": f"u{n}", "parentId": None, "timestamp": "2026-10-10T11:16:03.000Z",
                "message": {"role": "user", "content": [{"type": "text", "text": f"prompt {n}"}]},
            }
        )
    return "".join(json.dumps(line) + "\n" for line in lines).encode()


class FakeCounter:
    """Follows docs/spec.md, "Contract: counter": session_id and cwd from the header,
    folder_reused when cwd is in prior_folders, plus the reasons a test sets."""

    def __init__(self):
        self.reasons = []
        self.calls = []  # (problem, agreed, prior_folders) per call

    def __call__(self, session_text, problem, agreed, prior_folders):
        self.calls.append((problem, dict(agreed), set(prior_folders)))
        header = json.loads(session_text.split("\n", 1)[0])
        reasons = set(self.reasons) | ({"folder_reused"} if header["cwd"] in prior_folders else set())
        metrics = {
            "total_tokens": None if "missing_usage" in reasons else 1234, "prompts": 2, "chars_typed": 40,
            "tool_calls": 3, "models": ["openai/gpt-5.5"], "thinking_levels": ["low"],
            "solved": "not_solved" not in reasons,
        }
        return {"session_id": header["id"], "cwd": header["cwd"], "metrics": metrics, "reasons": sorted(reasons)}


class UploadTestCase(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(
            data_dir=Path(self.enterContext(tempfile.TemporaryDirectory())), api_base_url=BASE_URL
        )
        self.client = self.enterContext(TestClient(create_app(self.settings)))
        with closing(db.connect(self.settings.db_path)) as conn:
            self.key = users.create_user(conn, "alice", "alice_hackattic")
            self.bob_key = users.create_user(conn, "bob", "bob_hackattic")
        self.auth = {"Authorization": f"Bearer {self.key}"}

    def post(self, **request):
        return self.client.post("/api/v1/submissions", **request)

    def upload(self, content, problem="help_me_unpack", key=None, **fields):
        """POST as the plugin does: a `problem` field and the log as the `session` file part."""
        return self.post(
            headers={"Authorization": f"Bearer {key or self.key}"},
            data={"problem": problem, **fields},
            files={"session": ("session.jsonl", content, "application/x-ndjson")},
        )

    def assert_rejected(self, response, status_code, reason):
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(response.headers["content-type"], "application/json")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(
            response.json(), {"status": "rejected", "reasons": [reason], "metrics": None, "url": None}
        )

    def rows(self):
        with closing(db.connect(self.settings.db_path)) as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM submissions ORDER BY id")]

    def stored_file(self, row):
        return (self.settings.uploads_dir / f"{row['id']}.jsonl").read_bytes()


class SubmissionsTest(UploadTestCase):
    """Against a fake counter, so these keep working when 4.1 brings the real one."""

    def setUp(self):
        super().setUp()
        self.counter = FakeCounter()
        self.enterContext(mock.patch.object(submissions, "score", self.counter))

    def test_ranked(self):
        content = session()
        response = self.upload(content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/json")
        self.assertEqual(response.headers["cache-control"], "no-store")
        (row,) = self.rows()
        expected = FakeCounter()(content.decode(), "help_me_unpack", AGREED, set())
        self.assertEqual(
            response.json(),
            {
                "status": "ranked",
                "reasons": [],
                "metrics": expected["metrics"],
                "url": f"{BASE_URL}/submissions/{row['id']}",
            },
        )
        # Twice with the problem's setup: to learn the session, then with earlier folders.
        self.assertEqual(self.counter.calls, [("help_me_unpack", AGREED, set())] * 2)
        self.assertEqual(
            (row["problem"], row["session_id"], row["cwd"], row["status"], row["folder_was_empty"]),
            ("help_me_unpack", "s-1", "/work/attempt-1", "ranked", None),
        )
        self.assertEqual(row["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(self.stored_file(row), content)

    def test_status_from_the_reason_sets(self):
        # Every unranking code unranks; warnings alone stay ranked, and are listed.
        for n, reason in enumerate(sorted(submissions.UNRANKING_REASONS | submissions.WARNING_REASONS)):
            with self.subTest(reason=reason):
                self.counter.reasons = [reason]
                body = self.upload(session(f"s-{n}", f"/work/{n}")).json()
                expected = "unranked" if reason in submissions.UNRANKING_REASONS else "ranked"
                self.assertEqual((body["status"], body["reasons"]), (expected, [reason]))

    def test_unranked(self):
        self.counter.reasons = ["not_solved", "usage_not_recorded"]
        response = self.upload(session())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/json")
        body = response.json()
        self.assertEqual((body["status"], body["reasons"]), ("unranked", ["not_solved", "usage_not_recorded"]))
        self.assertFalse(body["metrics"]["solved"])
        self.assertEqual(self.rows()[0]["status"], "unranked")

    def test_total_tokens_null_exactly_with_missing_usage(self):
        for n, reasons in enumerate((["missing_usage"], ["missing_usage", "not_solved"], [], ["not_solved"])):
            with self.subTest(reasons=reasons):
                self.counter.reasons = reasons
                body = self.upload(session(f"s-{n}", f"/work/{n}")).json()
                if "missing_usage" in reasons:
                    self.assertEqual((body["status"], body["metrics"]["total_tokens"]), ("unranked", None))
                else:
                    self.assertEqual(body["metrics"]["total_tokens"], 1234)

    def test_reply_has_only_the_spec_metrics(self):
        def counter(*args):
            result = FakeCounter()(*args)
            result["metrics"]["cost"] = 0.25
            return result

        with mock.patch.object(submissions, "score", counter):
            body = self.upload(session()).json()
        self.assertEqual(list(body["metrics"]), list(submissions.METRICS))

    def test_bad_key(self):
        unknown = str(uuid.uuid4())
        for authorization in (
            None, "Basic xyz", f"Basic {self.key}", "Bearer", "Bearer not-a-uuid", f"Bearer {unknown}"
        ):
            headers = {} if authorization is None else {"Authorization": authorization}
            # Wrong on every other count too: the key is checked first, before the form is read.
            for request in (
                {"headers": headers, "data": {"problem": "nope"}},
                {"headers": {**headers, **MULTIPART_X}, "content": BROKEN_MULTIPART},
            ):
                with self.subTest(authorization=authorization, request=request):
                    response = self.post(**request)
                    self.assert_rejected(response, 401, "bad_key")
                    self.assertEqual(response.headers["www-authenticate"], "Bearer")
                    self.assertNotIn(self.key, response.text)
                    self.assertNotIn(unknown, response.text)
        too_big = b"\xff" * (submissions.MAX_SESSION_BYTES + 1)
        response = self.upload(too_big, problem="nope", key=unknown)
        self.assert_rejected(response, 401, "bad_key")
        # Never from the URL.
        response = self.post(
            params={"key": self.key},
            data={"problem": "help_me_unpack"},
            files={"session": ("session.jsonl", session())},
        )
        self.assert_rejected(response, 401, "bad_key")
        self.assertEqual((self.rows(), self.counter.calls), ([], []))

    def test_unknown_problem(self):
        file = {"session": ("session.jsonl", session())}
        cases = {
            "missing": {"files": file},
            "not in the config": {"data": {"problem": "nope"}, "files": file},
            "other case": {"data": {"problem": "Help_Me_Unpack"}, "files": file},
            "a file, not a field": {"files": {"problem": ("p.txt", b"help_me_unpack"), **file}},
            # Not a form at all, so no problem field either.
            "JSON body": {"json": {"problem": "help_me_unpack"}},
            "no body": {},
        }
        for name, request in cases.items():
            with self.subTest(name):
                self.assert_rejected(self.post(headers=self.auth, **request), 400, "unknown_problem")
        # A problem whose setup is not set yet is not accepted.
        with mock.patch.object(problems, "PROBLEMS", (*problems.PROBLEMS, UNSET)):
            self.assert_rejected(self.upload(session(), problem="not_set_yet"), 400, "unknown_problem")
        # Checked before the session and its size.
        too_big = b"x" * (submissions.MAX_SESSION_BYTES + 1)
        self.assert_rejected(self.upload(too_big, problem="nope"), 400, "unknown_problem")
        response = self.post(headers=self.auth, data={"problem": "nope"})
        self.assert_rejected(response, 400, "unknown_problem")
        self.assertEqual((self.rows(), self.counter.calls), ([], []))

    def test_file_too_large(self):
        self.assertEqual(submissions.MAX_SESSION_BYTES, 20 * 1024 * 1024)
        # Not UTF-8 either: the size is checked first.
        response = self.upload(b"\xff" * (submissions.MAX_SESSION_BYTES + 1))
        self.assert_rejected(response, 413, "file_too_large")
        self.assertEqual((self.rows(), self.counter.calls), ([], []))
        # Exactly 20 MiB is fine.
        content = session()
        content += b" " * (submissions.MAX_SESSION_BYTES - len(content))
        response = self.upload(content)
        self.assertEqual((response.status_code, response.json()["status"]), (200, "ranked"))

    def test_not_pi_log(self):
        auth, problem = self.auth, {"problem": (None, "help_me_unpack")}
        cases = {
            "no session part": self.post(headers=auth, files=problem),
            "no session, not multipart": self.post(headers=auth, data={"problem": "help_me_unpack"}),
            "session as a plain field": self.post(
                headers=auth, files={**problem, "session": (None, session().decode())}
            ),
            "not UTF-8": self.upload(b"\xff\xfe" + session()),
            # Unreadable multipart: the problem cannot even be read.
            "broken framing": self.post(headers={**auth, **MULTIPART_X}, content=BROKEN_MULTIPART),
            "no boundary": self.post(
                headers={**auth, "Content-Type": "multipart/form-data"}, content=b"--x--\r\n"
            ),
            "plain field over 1 MiB": self.post(
                headers=auth, files={**problem, "session": (None, "x" * (1024 * 1024 + 1))}
            ),
            "urlencoded field over 1 MiB": self.post(
                headers=auth, data={"problem": "help_me_unpack", "session": "x" * (1024 * 1024 + 1)}
            ),
        }
        with mock.patch.object(submissions, "score", side_effect=submissions.NotPiLogError("no header")):
            cases["the counter's NotPiLogError"] = self.upload(session())
        for name, response in cases.items():
            with self.subTest(name):
                self.assert_rejected(response, 400, "not_pi_log")
        self.assertEqual((self.rows(), self.counter.calls), ([], []))
        self.assertFalse(self.settings.uploads_dir.exists())

    def test_broken_multipart_is_not_logged(self):
        # python-multipart would warn with bytes quoted from the upload.
        with self.assertNoLogs(level=logging.WARNING):
            response = self.post(headers={**self.auth, **MULTIPART_X}, content=BROKEN_MULTIPART)
        self.assert_rejected(response, 400, "not_pi_log")

    def test_never_a_422(self):
        """Whatever the request, the reply is the spec's, never FastAPI's own 422."""
        requests = {
            "no body": {},
            "text": {"content": b"hello", "headers": {"Content-Type": "text/plain"}},
            "JSON": {"json": {"problem": "help_me_unpack", "session": "x"}},
            "bad JSON": {"content": b"{", "headers": {"Content-Type": "application/json"}},
            "urlencoded": {"data": {"problem": "help_me_unpack", "session": "x"}},
            "query string only": {"params": {"problem": "help_me_unpack"}},
            "empty multipart": {"content": b"", "headers": MULTIPART_X},
            "broken multipart": {"content": BROKEN_MULTIPART, "headers": MULTIPART_X},
            "part without a name": {
                "content": b'--x\r\nContent-Disposition: form-data\r\n\r\nhi\r\n--x--\r\n',
                "headers": MULTIPART_X,
            },
            "boundary too long": {
                "content": b"--x--\r\n",
                "headers": {"Content-Type": "multipart/form-data; boundary=" + "x" * 300},
            },
            "problem twice": {"data": {"problem": ["nope", "help_me_unpack"]}},
            "two session files": {
                "data": {"problem": "help_me_unpack"},
                "files": [("session", ("a.jsonl", b"\xff")), ("session", ("b.jsonl", b"\xff"))],
            },
        }
        for name, request in requests.items():
            for auth in ({}, self.auth):
                with self.subTest(name, key=bool(auth)):
                    headers = {**auth, **request.get("headers", {})}
                    response = self.post(**{**request, "headers": headers})
                    self.assertIn(response.status_code, (400,) if auth else (401,))
                    self.assertEqual(response.headers["content-type"], "application/json")
                    body = response.json()
                    self.assertEqual((body["status"], body["metrics"], body["url"]), ("rejected", None, None))
        self.assertEqual(self.rows(), [])

    def test_counter_crash_is_a_500(self):
        secret = "text-only-in-the-upload"
        # A bare ValueError is a counter bug, not a bad file.
        crash = mock.patch.object(submissions, "score", side_effect=ValueError(secret))
        with crash, self.assertLogs(level=logging.DEBUG) as logs:
            response = self.upload(session(cwd=f"/home/{secret}"))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"error": "server_error"})
        self.assertIn("ERROR:server.submissions:counter failed: ValueError", logs.output)
        for line in logs.output:
            self.assertNotIn(secret, line)
            self.assertNotIn(self.key, line)
        self.assertEqual(self.rows(), [])

    def test_counter_result_outside_the_contract_is_a_500(self):
        good = FakeCounter()(session().decode(), "help_me_unpack", AGREED, set())

        def broken(metrics=None, **changes):
            return {**good, **changes, "metrics": {**good["metrics"], **(metrics or {})}}

        no_tool_calls = broken()
        del no_tool_calls["metrics"]["tool_calls"]
        cases = {
            "not a dict": None,
            "no metrics": {**good, "metrics": None},
            "a metric missing": no_tool_calls,
            "a website code": broken(reasons=["bad_key"]),
            "an unknown code": broken(reasons=["nope"]),
            "null total without missing_usage": broken({"total_tokens": None}),
            "a total with missing_usage": broken(reasons=["missing_usage"]),
            "a negative count": broken({"prompts": -1}),
            "a bool count": broken({"tool_calls": True}),
            "a float count": broken({"chars_typed": 1.5}),
            "a count the plugin cannot read": broken({"total_tokens": 2**53}),
            "a control character in a model": broken({"models": ["openai/gpt\x1b[31m"]}),
            "a model that is not text": broken({"models": [5]}),
            "solved not a bool": broken({"solved": 1}),
            "no session id": broken(session_id=""),
            "an unpaired surrogate in the folder": broken(cwd="/work/\ud800"),
        }
        for name, result in cases.items():
            with self.subTest(name):
                score = mock.patch.object(submissions, "score", return_value=result)
                with score, self.assertLogs("server.submissions", logging.ERROR) as logs:
                    response = self.upload(session())
                self.assertEqual(response.status_code, 500)
                self.assertEqual(response.json(), {"error": "server_error"})
                self.assertEqual(logs.output, ["ERROR:server.submissions:counter failed: result outside docs/spec.md"])
        self.assertEqual(self.rows(), [])

    def test_resubmitting_replaces(self):
        times = ["2026-10-11T10:00:00+00:00", "2026-10-11T10:05:00+00:00"]
        with mock.patch.object(submissions, "utc_now", side_effect=times):
            first = self.upload(session(turns=1)).json()
            (before,) = self.rows()
            self.counter.reasons = ["not_solved"]
            content = session(turns=2)
            response = self.upload(content)
        self.assertEqual(response.status_code, 200)
        second = response.json()
        # Same row and link, new file and result; first upload time kept.
        self.assertEqual(second["url"], first["url"])
        self.assertEqual(second["status"], "unranked")
        (row,) = self.rows()
        self.assertEqual(row["id"], before["id"])
        self.assertEqual(row["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(row["status"], "unranked")
        self.assertEqual((row["first_submitted_at"], row["submitted_at"]), tuple(times))
        self.assertEqual(self.stored_file(row), content)
        self.assertEqual([path.name for path in self.settings.uploads_dir.iterdir()], [f"{row['id']}.jsonl"])
        # Its own folder is not a reuse.
        self.assertEqual(self.counter.calls[-1], ("help_me_unpack", AGREED, set()))
        self.assertNotIn("folder_reused", second["reasons"])

    def test_stored_log_is_private(self):
        # Even under a permissive umask, only the server's own user can read a raw log.
        self.addCleanup(os.umask, os.umask(0))
        self.upload(session(turns=1))
        (row,) = self.rows()
        path = self.settings.uploads_dir / f"{row['id']}.jsonl"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        # A resubmission's new copy too.
        self.upload(session(turns=2))
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_resubmitting_for_another_problem_replaces(self):
        content = session()
        with mock.patch.object(problems, "PROBLEMS", (*problems.PROBLEMS, FIXED)):
            first = self.upload(content).json()
            # The same file, but for another problem: scored again, with that problem's setup.
            second = self.upload(content, problem="fixed_setup").json()
        self.assertEqual(second["url"], first["url"])
        self.assertEqual(
            self.counter.calls[-1], ("fixed_setup", {"model": "openai/gpt-5.5", "thinking_level": "low"}, set())
        )
        (row,) = self.rows()
        self.assertEqual(row["problem"], "fixed_setup")

    def test_same_file_twice(self):
        content = session()
        first = self.upload(content, folder_was_empty="true")
        self.counter.reasons = ["not_solved"]  # would change the verdict if scored again
        again = self.upload(content, folder_was_empty="false")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json(), first.json())
        self.assertEqual(len(self.counter.calls), 2)  # from the first upload only
        (row,) = self.rows()
        self.assertEqual((row["status"], row["folder_was_empty"]), ("ranked", 1))
        # Another student's identical file is their own entry.
        bob = self.upload(content, key=self.bob_key).json()
        self.assertNotEqual(bob["url"], first.json()["url"])
        self.assertEqual(len(self.rows()), 2)

    def test_folder_reused(self):
        self.assertEqual(self.upload(session("s-1", "/work/a")).json()["reasons"], [])
        second = self.upload(session("s-2", "/work/a")).json()
        self.assertEqual((second["status"], second["reasons"]), ("unranked", ["folder_reused"]))
        self.assertEqual(self.counter.calls[-1][2], {"/work/a"})
        # Resubmitting the first session is still no reuse, though a later one used its folder.
        again = self.upload(session("s-1", "/work/a", turns=2)).json()
        self.assertEqual((again["status"], again["reasons"]), ("ranked", []))
        self.assertEqual(self.counter.calls[-1][2], set())
        # Resubmitting the second still is one.
        again = self.upload(session("s-2", "/work/a", turns=2)).json()
        self.assertEqual(again["reasons"], ["folder_reused"])
        # A new session sees every folder; another student's folders are not this one's.
        self.upload(session("s-3", "/work/b"))
        self.assertEqual(self.counter.calls[-1][2], {"/work/a"})
        self.assertEqual(self.upload(session("s-4", "/work/a"), key=self.bob_key).json()["reasons"], [])

    def test_folder_was_empty_is_stored(self):
        values = ("true", "false", None, "yes", "TRUE")
        for n, value in enumerate(values):
            fields = {} if value is None else {"folder_was_empty": value}
            body = self.upload(session(f"s-{n}", f"/work/{n}"), **fields).json()
            # No effect on ranking.
            self.assertEqual((body["status"], body["reasons"]), ("ranked", []))
        self.assertEqual([row["folder_was_empty"] for row in self.rows()], [1, 0, None, None, None])

    def test_url_opens(self):
        self.counter.reasons = ["usage_not_recorded"]
        content = session("session-id-1234", "/home/alice/secret-folder")
        reply = self.upload(content, folder_was_empty="true").json()
        url = urlsplit(reply["url"])
        self.assertEqual(f"{url.scheme}://{url.netloc}", BASE_URL)
        # The submission page (test_submission_page.py tests what it shows).
        response = self.client.get(url.path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/html; charset=utf-8")
        self.assertIn("Submission by alice", response.text)
        (row,) = self.rows()
        for private in (
            "/home/alice/secret-folder", "session-id-1234", row["sha256"], "alice_hackattic", "prompt 0",
            "folder_was_empty",
        ):
            self.assertNotIn(private, response.text)
        for path in ("/submissions/999", "/submissions/0", "/submissions/-1", "/submissions/abc",
                     "/submissions/", f"/submissions/{2**64}"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)


class ConfiguredCounterTest(UploadTestCase):
    """Against the counter submissions.py imports (server.counter, plan 003)."""

    def test_reply_is_the_counters_result(self):
        content = session()
        expected = submissions.score(content.decode(), "help_me_unpack", AGREED, set())
        response = self.upload(content)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual((body["reasons"], body["metrics"]), (expected["reasons"], expected["metrics"]))
        unranked = submissions.UNRANKING_REASONS & set(expected["reasons"])
        self.assertEqual(body["status"], "unranked" if unranked else "ranked")
        page = self.client.get(urlsplit(body["url"]).path)
        self.assertEqual((page.status_code, page.headers["content-type"]), (200, "text/html; charset=utf-8"))

    def test_not_a_pi_log(self):
        for content in (b"", b"hello\n", b'{"type": "message"}\n'):
            with self.subTest(content=content):
                self.assert_rejected(self.upload(content), 400, "not_pi_log")
        self.assertEqual(self.rows(), [])


if __name__ == "__main__":
    unittest.main()
