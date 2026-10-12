---
name: 002-website
description: Registration, key check, upload and problem-list API, leaderboard pages, Docker and deployment in server/ (never server/counter/).
status: started
created: 2026-10-10
updated: 2026-10-11
---

# Website

## Progress

- [x] **Phase 1 — Agreements**
  - [x] 1.1 Contract and process on `main`: upload status codes, reason codes, counter return and `NotPiLogError`, HANDOFF rule, gate on Python 3.12 (`d412128`, `278dc35`)
  - [x] 1.2 Second round on `main`: per-problem setup and problem config, problem list contract, generic "solved" check, usage reason codes, `agent-golf.justuju.in` (`d32ff18`, `d5062d5`)
- [x] **Phase 2 — API, against a stand-in counter**
  - [x] 2.1 Stack skeleton (FastAPI, Jinja, SQLite, Python 3.12, pinned `server/requirements.txt`) and `GET /api/v1/me` exactly per `docs/spec.md`
  - [x] 2.2 Register page → key page: username + Hackattic username, key shown once, only its SHA-256 stored
  - [x] 2.3 Stand-in counter in `server/` (never `server/counter/`): the spec's `score()`, `NotPiLogError` and reason sets; gives ranked and unranked results
  - [x] 2.4 Problem config, then `POST /api/v1/submissions` per `docs/spec.md`: checks, store file, call counter with the problem's setup, store result, reply
  - [x] 2.5 `GET /api/v1/problems` per `docs/spec.md`, built from the problem config
- [x] **Phase 3 — Pages**
  - [x] 3.1 Board per problem: ranked rows, then unranked players; 30-second refresh; projector-size text
  - [x] 3.2 Submission page: username, model, numbers, solved, reasons; never prompts, folders or raw log
  - [x] 3.3 Rules page: the seven rules, each problem's instructions and setup, scoring, install and submit steps
- [ ] **Phase 4 — Real counter** (after Amit merges `counter` to `main`)
  - [x] 4.1 Bring `main` into this branch; import from `server.counter`; delete the stand-in; the three `samples/*.jsonl` give the verdicts in `samples/README.md`
  - [ ] 4.2 Upload Anup's solved real session with a test key; it shows a ranked row
- [ ] **Phase 5 — Docker and deployment at agent-golf.csbasics.in**
  - [x] 5.1 `server/Dockerfile`: one image with the website and the counter
  - [x] 5.2 Database and uploads in a mounted volume; survive a container restart
  - [x] 5.3 Merge `feature/plan-002` to `main`; update `.agents/HANDOFF.md` in that merge
  - [x] 5.4 Deploy with HTTPS at agent-golf.csbasics.in (Cloudflare Tunnel, port 8077); confirm a 19 MB upload reaches the app
  - [x] 5.5 Keys and uploads never appear in server or tunnel logs
- [ ] **Phase 6 — Verification and handoff**
  - [ ] 6.1 Upload each file in `samples/` to the live site with a test key; rows appear correctly
  - [ ] 6.2 Tell Prateek the live site is up, so the plugin's default `AGENT_GOLF_API_BASE_URL` works
  - [ ] 6.3 Gate passes; tick this plan and add to its Changelog

## Goal

Students can register, upload, and see the board. Done when a solved real session (Anup supplies it) uploaded with a test key shows a ranked row on the live site.

## Context

- Contract and rules: `docs/spec.md`. "Contract: student key validation" is Prateek's and fixed; the rest was agreed in 1.1 and 1.2. Change none of it without telling the other two.
- Counter: `server/counter/` is Amit's (plan 003, on `main` since `3a5873b`); never create or edit files there. Since 4.1, `server/submissions.py` is the one place that imports it (`score`, `NotPiLogError`, `UNRANKING_REASONS`, `WARNING_REASONS`); the stand-in from 2.3 is deleted. "Solved" is one generic check inside the counter, so the website never needs per-problem scoring code.
- Problem config (`server/`, from 2.4): one entry per Hackattic problem with slug, title, Hackattic URL, instructions, model (`provider/model` or `"any"`) and thinking level (a level or `"any"`), plus the rules text and `rules_version`. It is the single source for the problem list, the `unknown_problem` check, the `agreed` setup sent to the counter, and the board and rules pages. Adding a problem means adding an entry. Listed: `help_me_unpack` (first, so the home page shows its board) and `brute_force_zip`, both with any model and any thinking level (`"any"`/`"any"`) for Monday, as Step 0 decided for `help_me_unpack` (plan 001) and Anup decided for `brute_force_zip`.
- Models (`docs/spec.md`, 810982a and c1b61da): only models and levels that actually answered count. With `"any"` the match is skipped, but a model-`"any"` session that used more than one model gets `model_switched` (unranks). The board shows a model column only when the problem's model is `"any"`; the submission page always shows the model.
- Plugin: Prateek (plan 004) reads the server origin from `AGENT_GOLF_API_BASE_URL` (`http://localhost:8000` locally, `https://agent-golf.csbasics.in` live). The website reads the same variable to build the absolute `url` in replies.
- Data: SQLite database and uploaded logs live in `AGENT_GOLF_DATA_DIR` (default `server/data/`, ignored by `server/.gitignore`; `/data` in Docker). Review notes from workflows land in `server/.agents-review/`, ignored by the root `.gitignore`.
- Local setup: `uv venv --python 3.12 && uv pip install -r server/requirements.txt`; run `.venv/bin/uvicorn server.app:app --port 8000`. `server/README.md` keeps the exact commands.
- Look: plain, light, server-rendered pages; text `#272426`, accent `#c46c34`. JavaScript only for the copy button; the board reloads with a meta refresh.
- Public pages show only username, model, numbers and verdicts: never prompts, folder paths, raw logs, keys or Hackattic usernames.
- `metrics.total_tokens` is `null` when the counter sets `missing_usage` (unranked); pages show "unknown" for it.
- Upload size: Starlette (under FastAPI) caps non-file multipart fields at 1 MB by default, so read `session` as a file part and enforce 20 MB ourselves; check against the pinned version. Live, there is no proxy on the server: Cloudflare (Free and Pro plans) accepts request bodies up to 100 MB, so the app's own 20 MiB `file_too_large` is the limit students meet (checked in 5.4).

## Steps

### Phase 2 — API, against a stand-in counter

#### 2.1 Stack and key check
- Files: `server/requirements.txt`, `server/app.py` and modules beside it, `server/tests/`, `server/README.md`, `server/.gitignore`, `server/__init__.py` (make it identical to the one on Amit's `counter` branch so the two merge cleanly)
- Do: FastAPI app; SQLite users table (username, Hackattic username, key SHA-256, created time); exact-pinned requirements; `GET /api/v1/me` exactly per "Contract: student key validation" (200 `{"username": …}`, 401 otherwise, `Cache-Control: no-store` on both); keys parsed as UUIDs, then hashed; unittest tests with FastAPI's `TestClient`.
- Acceptance: `bash tools/check.sh` runs the new tests and passes; with the server on port 8000, `curl` with no key, a bad key and a valid key gives 401, 401, 200, each with `Cache-Control: no-store`; the key appears in neither the database nor the server output.
- Result (2026-10-10): `bash tools/check.sh` → `Ran 15 tests … OK`, `gate: ok`. Local curl 401/401/200, all `no-store`, checked by the workflow reviewer, by Kiro and by Anup; key absent from the database and server output. Also pinned `starlette==1.7.0` and `pydantic==2.14.0` (FastAPI leaves them open); `server/__init__.py` matches the `counter` branch byte for byte.

#### 2.2 Register
- Files: `server/`
- Do: form with username (`[a-z0-9_]{3,32}`, lowercased, unique) and Hackattic username (required, trimmed, at most 64 characters; `create_user` from 2.1 does not check it yet); inline errors for a taken (409) or badly formed name; key = random UUID; store only SHA-256(key). The POST response is the key page itself (no redirect, no key in any URL, `Cache-Control: no-store`): key in large type, copy button, "save it now, there is no recovery", and `/golf-login <key>` ready to paste.
- Acceptance: registering the same name twice fails; the key never appears in the database, logs or any URL; the new key passes `GET /api/v1/me`.
- Result (2026-10-11): `bash tools/check.sh` → `Ran 26 tests … OK`, `gate: ok`. Live check (Kiro): GET 200 with two labelled fields; POST `Bob` → 200 key page, `no-store`, no `Location`, stored as `bob`, key passes `/api/v1/me`; same name → 409 with no key; bad name → 400 with the script tag escaped and `aria-invalid`; blank or 65-character Hackattic name → 400; key absent from the database and server log; the only script is `/static/copy.js`. Screenshots at 1280 and 390 px looked right. The workflow run was stopped before its review, because the code was done and only verification was left.

#### 2.3 Stand-in counter
- Files: `server/standin_counter.py` and its tests (both deleted in 4.1)
- Do: `score(session_text, problem, agreed, prior_folders)`, `NotPiLogError`, `UNRANKING_REASONS` and `WARNING_REASONS` as in "Contract: counter"; `session_id` and `cwd` from the header line when present; deterministic made-up metrics from the file hash; some files ranked, some unranked with reasons, one case with `missing_usage` and `total_tokens: null`; `folder_reused` when `cwd` is in `prior_folders`; `NotPiLogError` for text that is not JSON lines. With `agreed` `"any"`, skip that match; for model `"any"`, a made-up second model gives `model_switched`.
- Acceptance: tests show a ranked result, an unranked one with reasons, `missing_usage` with a null total, `folder_reused`, `model_switched` under model `"any"`, and `NotPiLogError`.
- Result (2026-10-11): `bash tools/check.sh` → `Ran 37 tests … OK`, `gate: ok` (11 new in `server/tests/test_standin_counter.py`: all six cases above, plus a warning-only result, a fixed setup matching, the reason sets against the spec's table, and the same text always giving the same result). On Amit's two redacted samples under `"any"`/`"any"`: `real-second-redacted` is clean, `real-zip-redacted` has only the `usage_not_recorded` warning.

#### 2.4 Problem config and upload
- Files: `server/` (problem config module, upload route, tests)
- Do:
  - Problem config as in Context; `help_me_unpack` entry first, with model `"any"` and thinking level `"any"` (kept for Monday by Step 0, plan 001).
  - Rejections per the spec: unknown or missing key → 401 `bad_key`; problem not in the config → 400 `unknown_problem`; `session` over 20 MB → 413 `file_too_large`; missing `session` or not UTF-8 → 400 `not_pi_log`; counter's `NotPiLogError` → 400 `not_pi_log`; any other counter exception → 500.
  - Identical file (SHA-256) from the same user returns the existing entry. Call the counter once with no folders to learn `session_id` and `cwd`, then again with `prior_folders` = the user's other sessions' folders, both times with `agreed` from the problem's config entry. Same `session_id` from the same user replaces the earlier row and file.
  - Store `folder_was_empty` (no ranking effect); set `status` from `UNRANKING_REASONS`; reply per the spec, `url` from `AGENT_GOLF_API_BASE_URL`.
  - Until 3.2, `GET /submissions/<id>` returns the submission's public fields as plain JSON, so the reply's link opens.
- Acceptance: tests for 200 ranked, 200 unranked, 401 `bad_key`, 400 `unknown_problem`, 400 `not_pi_log`, 413 `file_too_large` and 500 for a counter crash; resubmitting the same session replaces it; the same file twice returns the existing entry. A `curl -F` upload to the local server returns the spec's body, and its link opens.
- Result (2026-10-11): `env TMPDIR=server/data/tmp bash tools/check.sh` (TMPDIR only keeps the tests' temporary files inside the project) → `Ran 62 tests … OK`, `gate: ok`; 25 new: 21 in `server/tests/test_submissions.py` (every status above, each check's order, the never-a-422 battery, malformed multipart → `not_pi_log` with nothing logged, the null/`missing_usage` pairing, a result outside the contract → 500, replacement keeping id and first-upload time even for another problem, duplicates, `folder_reused` for a new session but not a resubmission, `folder_was_empty` stored, the public JSON at `/submissions/<id>`) and 4 in `server/tests/test_problems.py`. Live check (Kiro), server on port 8000 with a scratch data dir under `server/data/tmp/` and `AGENT_GOLF_API_BASE_URL=http://localhost:8000`, Amit's two redacted samples from `origin/counter` via `curl -F`: `real-second-redacted` → 200 `{"status":"ranked","reasons":[],"metrics":{"total_tokens":15147,"prompts":4,"chars_typed":845,"tool_calls":19,"models":["standin/model-a"],"thinking_levels":["medium"],"solved":true},"url":"http://localhost:8000/submissions/1"}`, and that url → 200 JSON with only id, username, problem, status, reasons, metrics and the two times. `real-zip-redacted` from the same user, sent as the plugin does (`session.jsonl`, `application/x-ndjson`, `folder_was_empty=true`) → 200 `unranked` with `["folder_reused","usage_not_recorded"]`, correctly, since both redacted samples have the cwd `/redacted/attempt`; from a second user → 200 `ranked` with `["usage_not_recorded"]`, `/submissions/3`. The same file again → the same reply for `/submissions/1`, not scored again; no key → 401 `{"status":"rejected","reasons":["bad_key"],"metrics":null,"url":null}`; `problem=nope` → 400 `unknown_problem`; `/uploads/1.jsonl` → 404. Neither key is in the server log, the database or the stored uploads. Replies in `server/.agents-review/upload-*.txt` and `submission-*.txt`.

#### 2.5 Problem list
- Files: `server/` (route, tests)
- Do: `GET /api/v1/problems` exactly per "Contract: problem list": public, built from the problem config, lists only problems whose model and thinking level are set (`"any"` counts as set), keeps the safety limits (plain text, 64 KB body, 1,000 characters per string, `challenge_url` = `https://hackattic.com/challenges/<slug>`).
- Acceptance: tests cover the populated and empty lists and the limits; `curl http://localhost:8000/api/v1/problems` needs no key.
- Result (2026-10-11): `env TMPDIR=server/data/tmp bash tools/check.sh` → `Ran 76 tests … OK`, `gate: ok`; 14 new in `server/tests/test_problems.py`: the populated list (exact body, `application/json`, the same bytes `check()` measured), no key needed (none, a malformed one, an unknown one), the empty list (rules still there), only set problems listed, and `problems.check()` against each limit: C0 and C1 controls, bidi controls, unpaired surrogates and HTML tags refused in titles, instructions and rules; 1,000 characters fine and 1,001 refused, counted as characters; over 64 KB refused though every string is within its limit; `challenge_url` exactly `https://hackattic.com/challenges/<slug>`; slugs, models and thinking levels in the shapes the plugin accepts; problems not listed yet checked too; `create_app` refuses a bad config. Live check (Kiro): `curl -s -i http://localhost:8000/api/v1/problems` with no key → 200 `application/json`, 1,527 bytes: `rules_version` `mvp-1`, the eight rule lines, and `help_me_unpack` with model and thinking level `"any"`. Reply in `server/.agents-review/problems.txt`.

### Phase 3 — Pages

#### 3.1 Board
- Files: `server/` templates
- Do: one board per problem at `/problems/<slug>`; the home page shows the first listed problem's board and links the others. Header: problem title, its model and thinking level ("any model, one per session" for `"any"`), the scoring line. Ranked rows sorted by `(total_tokens, prompts, chars_typed)`, equal scores share a rank, each player only their best ranked session; columns rank, player, tokens, prompts, chars, tool calls, submitted, plus a model column only when the problem's model is `"any"` (hidden when the problem has one fixed model). Below, "Unranked": each player's latest unranked attempt, only if that player has no ranked row, with reasons in plain English. Footer: install → `/golf-login` → solve → `/golf-submit`. Meta refresh every 30 s; text sized for a projector.
- Acceptance: with the stand-in, mixed uploads show ranked rows in order and only the allowed unranked rows; the model column appears for an `"any"` problem and not for a fixed-model one; the page reloads itself every 30 s.
- Result (2026-10-11): `env TMPDIR=server/data/tmp bash tools/check.sh` → `Ran 95 tests … OK`, `gate: ok`; 19 new in `server/tests/test_board.py` (page tests parse the HTML with the new `server/tests/dom.py`): ranked order with shared ranks (1, 2, 2, 4, 5: tokens, then prompts, then characters; equal scores in first-submitted order), each player's best ranked session only and its link, unranked as each unranked player's latest attempt (also after a resubmission) with plain-English reasons and no warnings, the model column for the `"any"` problem and none for a fixed-model one in the same test, header (title, setup, scoring line), footer steps, `<meta http-equiv="refresh" content="30">`, both empty states, `/` = the first listed problem's board with links to the others, no problems listed, HTML 404s, nav, `th` scopes and labelled scroll regions, escaping, no folder, session id, prompt, file hash, key or Hackattic username in the HTML, relative times, and mixed uploads through the configured stand-in matching an independent ranking of the replies. Screenshots come with 3.3, once all three pages exist.

#### 3.2 Submission page
- Files: `server/` templates
- Do: `/submissions/<id>`: Ranked #N or Unranked, the four numbers large ("unknown" for a null total), model and thinking level, solved yes/no, reasons in plain English (warnings marked as such), submitted time.
- Acceptance: the `url` in an upload reply opens this page; its HTML contains no prompt text, `cwd` or Hackattic username.
- Result (2026-10-11): `env TMPDIR=server/data/tmp bash tools/check.sh` → `Ran 106 tests … OK`, `gate: ok`; 11 new in `server/tests/test_submission_page.py`: the reply's `url` opens the page (title, numbers, facts, `<time datetime>`, no refresh), all three standings ("Ranked #1" for two equal scores, "Ranked #3", "Ranked (not your best attempt)", "Unranked"), "unknown" tokens, model and thinking level on a fixed-model problem whose board hides them, several and none, solved yes/no, reasons in plain English with unranking ones first and warnings marked (a warning alone stays "Ranked #1"), `folder_reused` without the folder, no `cwd`, session id, prompt, file hash, key or Hackattic username in the HTML, HTML 404s, a problem no longer listed (its slug, no link), escaping. `test_submissions.py`'s two `/submissions/<id>` checks now expect the HTML page. Screenshots come with 3.3.

#### 3.3 Rules page
- Files: `server/` templates
- Do: the rules text from the problem config (mirrors `docs/spec.md`), each listed problem's title, Hackattic link, instructions, model and thinking level, the scoring line, and install, login and submit steps (install command from plan 004 once Prateek publishes it).
- Acceptance: linked from every page's header; shows the same problems and setups as `GET /api/v1/problems`.
- Result (2026-10-11): `env TMPDIR=server/data/tmp bash tools/check.sh` → `Ran 111 tests … OK`, `gate: ok`; 5 new in `server/tests/test_rules.py`: the rules text equals `problems.RULES`; with a fixed-model and an unset problem added, the page shows exactly the problems of `GET /api/v1/problems`, each with its title, Hackattic link, setup ("any model, one per session; any thinking level" and "openai/gpt-5.5; thinking level low"), instructions, `/golf-submit <slug>` and board link; the scoring line, the install placeholder and the login and submit steps; no problems listed; escaping. `test_board.py`'s nav test now checks Board, Rules and Register (and which is current) on the board, rules, register, submission and 404 pages. Live check (Kiro): server on port 8000 with a scratch data dir under `server/data/tmp/`, twelve uploads from eight players through the stand-in (a scratch script, keys never printed, times then backdated in the scratch database), all `200`; the board showed ranks 1, 1, 3, 4, 5 (a shared file gives the shared rank, a warning-only session stays ranked, a player's worse and unranked sessions are hidden) and Unranked "Folder reused", "Not solved", "Model switched", latest first; `/submissions/7` from a reply opened as HTML. Screenshots in `server/.agents-review/`: `board-1280.png`, `board-390.png`, `submission-page-1280.png`, `submission-page-390.png`, `submission-unranked-1280.png`, `rules-1280.png`, `rules-390.png`, `rules-1280-full.png`; server log (paths and statuses only) in `server-live-3.log`. This Chrome will not make a window narrower than about 500 px, so the 390 px shots load the page in a 390 px iframe. They led to three CSS fixes: board tables scroll sideways on phones instead of breaking models mid-word, a large number on the submission page never breaks (its box grows), and "(1 day ago)" stays on one line (that last one not re-shot).

### Phase 4 — Real counter

#### 4.1 Swap
- Files: `server/` (one import); delete `server/standin_counter.py` and its tests
- Do: after `counter` merges, bring `main` into this branch; `from server.counter import score, NotPiLogError, UNRANKING_REASONS, WARNING_REASONS`.
- Acceptance: the gate passes with both the counter's and the website's tests.
- Result (2026-10-12): merged `main` at `3a5873b` (no conflicts); the merged tree passed with 136 tests. After the swap, with `server/standin_counter.py` and its 11 tests deleted, `bash tools/check.sh` → `Ran 125 tests … OK`, `gate: ok`. `server/.dockerignore` also leaves out `**/test_*.py`; the rebuilt image has `counter/` without `test_counter.py`, and `server.app` and `server.counter` import inside it. Live check (Kiro), one test user per sample so no folder counts as reused, `agreed` `"any"`/`"any"` as `samples/README.md` says:
  - `real-zip-redacted.jsonl` as `brute_force_zip`: `200` ranked, `usage_not_recorded`, 202,053 tokens, 10 prompts, 599 characters, 15 tool calls, solved.
  - `real-second-redacted.jsonl` as `brute_force_zip`: `200` unranked, `not_solved`, 79,221 / 2 / 41 / 9.
  - `real-wrong-answer-redacted.jsonl` as `help_me_unpack`: `200` unranked, `custom_setup` and `not_solved`, 7,604 / 1 / 736 / 1.
  
  All three match `samples/README.md`, and each reply's link opened as HTML. `brute_force_zip` is not in `problems.py`, so the two ZIP samples were uploaded to a scratch server that added it to the problem list for that run only. On the real app the same upload gets `400 unknown_problem`, so students cannot submit `brute_force_zip` until it is added. The scratch database and stored logs were 0600.

### Phase 5 — Docker and deployment

#### 5.1 Dockerfile
- Files: `server/Dockerfile`, `server/.dockerignore`
- Do: Python 3.12 slim base; copy the whole `server/` folder to `/app/server` so `server.counter` imports work as in the repo; install from the pinned requirements; run as a non-root user; one port (8000).
- Acceptance: `docker build -t agent-golf server/ && docker run -p 8000:8000 -v agent-golf-data:/data agent-golf` serves the register page locally.
- Result (2026-10-11): `env TMPDIR=server/data/tmp bash tools/check.sh` → `Ran 111 tests … OK`, `gate: ok`. Docker 29.4 on OrbStack (linux/arm64): `docker build -t agent-golf server/` built all six steps on `python:3.12-slim` (Python 3.12.15); `pip freeze` in the image gives the same 20 packages and versions as the local `.venv`. `docker run --rm agent-golf id` → `uid=10001(golf) gid=10001(golf)`; `find /app` lists only the code, templates, static files and an empty `server/data/` owned by `golf`: no local database or scratch, no `tests/`, `.agents-review/` or `__pycache__`. Then `docker run -d --name agent-golf-test -p 8002:8000 -e AGENT_GOLF_API_BASE_URL=http://localhost:8002 -v agent-golf-test-data:/data agent-golf` (host port 8002, since 8000 is the dev server's): `curl http://localhost:8002/register` → `200 OK`, `text/html`, `cache-control: no-store`, the register form; `/static/style.css` and `/api/v1/problems` → 200; `docker top` shows uvicorn as uid 10001. As expected before 5.2, the database was written inside the container (`docker diff`: `A /app/server/data/agent_golf.db`), not in the volume. Test container and volume removed afterwards.

#### 5.2 Persistent data
- Files: `server/` config
- Do: `AGENT_GOLF_DATA_DIR=/data` in the image; database file and uploaded logs live in the volume, never inside the image.
- Acceptance: register a user, restart the container, the user and their submissions are still there.
- Result (2026-10-11): `env TMPDIR=server/data/tmp bash tools/check.sh` → `Ran 111 tests … OK`, `gate: ok`. The image now sets `AGENT_GOLF_DATA_DIR=/data` and `VOLUME /data`, with `/data` owned by `golf` and no `server/data/` in the image (`find /app /data`); `docker build -t agent-golf server/` ran clean. Live check (Kiro), Docker 29.4 on OrbStack, fresh volume: `docker run -d --name agent-golf-test -p 8002:8000 -e AGENT_GOLF_API_BASE_URL=http://localhost:8002 -v agent-golf-test-data:/data agent-golf` → `/register` 200, and the new volume took `/data`'s owner (`golf`), with `agent_golf.db` in it. A scratch script under `server/data/tmp/` ran `docker exec agent-golf-test python -m server.users dockeruser …` and wrote the key and an `Authorization` header file there without printing either; `curl -H @<header file>` → `/api/v1/me` 200 `{"username":"dockeruser"}`. `curl -F` upload of `real-second-redacted.jsonl` (from `origin/counter`) → 200 `ranked`, `"url":"http://localhost:8002/submissions/1"`, which opened (200 HTML, "Ranked #1"); `/data` then held `agent_golf.db` and `uploads/1.jsonl` (10,956 bytes, the sample's size), and `docker diff` showed nothing from the app in the container's own layer (only OrbStack's CA certificates). `docker restart agent-golf-test` (uvicorn shut down cleanly) → `/api/v1/me` 200 for the same key, `/submissions/1` 200, and the board's ranked row still there. Since a restart keeps the container's layer, also `docker rm -f agent-golf-test` and a new `docker run` on the same volume → `/api/v1/me` 200, `/submissions/1` 200 (same submitted time), and the same file again → the stored entry's `/submissions/1`. The key was in neither `docker logs` nor the volume's two files (`docker cp` of `/data`, searched by the script). Test container and volume removed afterwards; the `agent-golf` image kept.

#### 5.4 Deploy
- Files: deployment notes in `server/README.md` ("Live site")
- Do: our shared Docker server, behind a Cloudflare Tunnel (Anup's setup): no ports opened and no proxy on the server. Cloudflare serves HTTPS. Its connector, the `agent-golf-tunnel` container (host network), reaches the app on `127.0.0.1:8077`, because port 8000 is taken on that server. The `agent-golf` container runs `--restart unless-stopped`, the `agent-golf-data` volume at `/data`, `AGENT_GOLF_API_BASE_URL=https://agent-golf.csbasics.in` and `uvicorn … --no-access-log`. The server's address stays out of this public repo.
- Acceptance: `https://agent-golf.csbasics.in/` loads, registration works, and a 19 MB upload reaches the app (it answers with the app's own JSON, not a proxy error page).
- Result (2026-10-12): the server's `~/agent-golf` checkout pulled `0e7bc2e` (main's `9b75809` merged); the image was rebuilt and the container recreated with the same volume, port and flags. Users and submissions were unchanged (0 and 0) before and after. Through Cloudflare (`server: cloudflare`, HTTP/2):
  - `GET /api/v1/problems` → 200 with `help_me_unpack` and `brute_force_zip`.
  - Registration through the live HTTPS form → 200 key page, and that key passed `GET /api/v1/me`.
  - A 19 MiB upload (19,923,278 bytes sent) → the app's own `400 not_pi_log`, so Cloudflare passed it and the app read all of it.
  - A 21 MiB upload (22,020,430 bytes sent) → the app's own `413 file_too_large`, not Cloudflare's error page, so the app sets the limit (Cloudflare allows 100 MB).
  - Nothing from the test was stored, and its key was not in `docker logs agent-golf`. The test user `deploy_check` was then deleted. Anup's own `test_anup` and its one submission were left alone.
  - Open: plain `http://agent-golf.csbasics.in` is served without a redirect to HTTPS. Turn on Cloudflare's "Always Use HTTPS" for the zone before students register.

#### 5.5 No keys or uploads in logs
- Files: `server/` run config
- Do: uvicorn's access log prints query strings, so a key a student wrongly puts in `?key=` would be logged even though it is rejected: the live container runs `--no-access-log` (since 5.4). There is no proxy on the server; check the Cloudflare connector's log too. Keep FastAPI's telemetry export off (its redaction does not cover `key`).
- Acceptance: after a login, an upload and a `GET /api/v1/me?key=<key>` against the live site, searching the server and tunnel logs for that key finds nothing.
- Result (2026-10-12): against https://agent-golf.csbasics.in, with a fresh test user `log_check` registered through the live form (its key kept in a scratch file, never on a command line):
  - `GET /api/v1/me` with the key in the header → 200; with the key in the URL → 401.
  - An upload carrying a unique marker and a fake `access_token=` line → the app's own `400 not_pi_log`.
  - Both logs were then copied read-only (`docker logs`) and searched by a script that printed counts only. In `agent-golf` (4 lines, startup only) and `agent-golf-tunnel` (68 lines, 09:05Z to 09:50Z, no debug lines): the test key 0, the marker 0, `access_token` 0, `Authorization` 0, `Bearer` 0, `?key=` 0, `/api/v1/` 0. The connector logs no line per request.
  - Its only error lines (20) are failed requests while the app restarted during the two redeploys. They name the request's URL (`dest=`, only `/` seen). A key a student wrongly puts in a URL could reach the connector's log only during a redeploy, so keep redeploys short.
  - The test user was deleted (its key now gets 401), no upload was stored, and users and submissions are back to 0. `agent-golf-tunnel` was only read, not changed. Cloudflare's own edge logs are outside this check.

## Validation

- `bash tools/check.sh` passes.
- Register → upload → board works locally with the sample logs.
- The same works on the live site, from the Docker container.

## Decisions

| Decision | Rationale | Rejected alternative |
|---|---|---|
| Store only key hashes | A leaked database does not leak keys | Plain-text keys |
| Website owner also deploys, using Docker | One person owns the server end to end; the counter ships inside the same image | Separate deploy owner (was plan 004) |
| FastAPI + Jinja + SQLite on Python 3.12 (uv), exact-pinned `server/requirements.txt` | Small, server-rendered, one process and one database file; matches CI | Django; a JavaScript front end |
| Model and thinking level per problem, in one website problem config (slug, title, Hackattic URL, instructions, model, thinking level) | Several Hackattic problems this week, possibly with different setups; one source feeds the problem list, `unknown_problem`, `agreed` and the pages | One global setup in the spec |
| Pages: board, register, key page, submission, rules | Smallest set for tonight; admin work uses the SQLite command line | Player page; admin page |
| Home page = first listed problem's board, with links to the others | One obvious board for the projector; more problems need no new page | A problem index page |
| Live behind a Cloudflare Tunnel to `127.0.0.1:8077`, at `agent-golf.csbasics.in`; no proxy or open ports on the server | The server is shared (its own nginx holds 80/443, another app holds 8000); Cloudflare gives HTTPS, keeps the server's address private and passes uploads up to 100 MB | An nginx proxy and open ports on the server; `agent-golf.justuju.in` |
| `brute_force_zip` open from Monday with `"any"`/`"any"`, listed after `help_me_unpack` | Anup's decision; two of the three samples are ZIP sessions, and the counter scores them as `samples/README.md` says; the home page stays on `help_me_unpack` | Keeping it closed (uploads got `400 unknown_problem`) |
| Board: model column only when the problem's model is `"any"`; unranked shows each player's latest attempt, only if they have no ranked row | Matches the spec; with one fixed model the column would repeat the same value on every row; keeps the projector board short | Model column always; never a model column; every unranked attempt |
| Submission page always shows the model and thinking level | Each attempt's setup is visible even when the board hides it | Board only |
| Projector: meta refresh every 30 s, larger text | The board is shown in the room; no JavaScript needed | Manual refresh; live updates |
| Plain light pages, `#272426` text, `#c46c34` accent | No time for Claude Design today | Claude Design mock first |
| Stand-in counter in `server/`, swapped in 4.1 | The website ships before the counter; `server/counter/` is Amit's | Waiting for the real counter |
| Only `NotPiLogError` means `not_pi_log`; any other counter exception is a 500 | A counter bug must not look like a bad file | Catching a bare `ValueError` |
| `status` from the counter's `UNRANKING_REASONS` | One list of unranking codes, in the counter | A second copy of the list in the website |
| Two counter calls per upload (learn `session_id`, then score with `prior_folders`) | Keeps all Pi parsing inside the counter | Website parses the session header itself |
| `folder_was_empty` stored, not scored | Agreed with the team; no reason code | Warning code |
| Identical files deduplicated per user | Trusted students; the stored fingerprint still reveals cross-user copies | Rejecting cross-user duplicates |
| Branch `feature/plan-002` | Matches plan 004's branch and the planning skill | `website` |

## Changelog

- 2026-10-10 — created
- 2026-10-10 — Anup owns this plan; Docker and website deployment added (moved from plan 004)
- 2026-10-10 — 1.1 done on `main` (`d412128`, `278dc35`). Restructured: agreements, API against a stand-in counter, pages, real-counter swap, Docker and deploy; stack, page and board decisions recorded
- 2026-10-10 — Added 1.2 (second spec round, done on `main` as `d32ff18`, `d5062d5`) and 2.5 (`GET /api/v1/problems`); per-problem setup in a website problem config; domain is `agent-golf.justuju.in`; deploy must pass a 19 MB upload
- 2026-10-10 — 2.1 done: FastAPI skeleton and `GET /api/v1/me`, tested locally by Anup. Later, not today: the tests print a Starlette deprecation warning about httpx; leave it, no dependency upgrades today.
- 2026-10-11 — 2.2 done: register form and key page (Jinja templates, one CSS file, copy-button JS only); `create_user` now checks the Hackattic username (required, trimmed, at most 64 characters, no control characters).
- 2026-10-11 — Merged `main` (810982a, c1b61da). The problem config allows `"any"` (`help_me_unpack` is `"any"`/`"any"` until Step 0); the stand-in follows `model_switched`; the board shows a model column only for model-`"any"` problems, as the spec says; the submission page always shows the model; 2.4 serves a plain JSON `/submissions/<id>` until 3.2.
- 2026-10-11 — 2.3 done: `server/standin_counter.py` with the spec's names; numbers and verdicts made up from the file's SHA-256 (half clean; the rest not solved, no usage, a mid-session model and level switch, or a warning), `session_id` and `cwd` from the header. Made-up models are named `standin/…`, so its output is never mistaken for real scoring.
- 2026-10-11 — 2.4 done, resumed after an app restart cut the first run short: problem config in `server/problems.py` (problems with an unset model or thinking level are neither listed nor accepted) and the upload in `server/submissions.py`, with the counter imported in that one place. The form is parsed after the key check with no FastAPI form parameters, so there is no 422; an unreadable form is `not_pi_log`. The counter's result is checked against the contract before it is stored (otherwise a 500, like a crash), and only the spec's seven metrics are kept. Submission ids are never reused (`AUTOINCREMENT`), so ids follow first uploads for `prior_folders`. python-multipart's warnings are silenced, because they quote bytes of a malformed upload.
- 2026-10-11 — 2.5 done: `GET /api/v1/problems` serves `problems.problem_list_json()`, the rules and every set problem. `problems.check()` runs in `create_app`, so a config that breaks the list's limits stops the server from starting. Beyond the spec's limits it also refuses what the plugin on `feature/plan-004` would refuse (bidi controls, unpaired surrogates, slug, model and thinking-level shapes), so the list it serves never shows as "unavailable".
- 2026-10-11 — 3.1 done: ranking in `server/board.py`, page text (setups, reason labels, counts, "5 min ago") in `server/pages.py`, `templates/board.html`, and an HTML 404 page for unknown boards. Small choices: among equal scores, and between a player's equally good sessions, the first submitted comes first; the Unranked rows list only the reasons that unranked them (warnings are on the submission page); "submitted" is the session's latest upload; the footer shows `/golf-submit <slug>`, as the plugin on `feature/plan-004` needs the slug. Nav: Board and Register (Rules comes with 3.3).
- 2026-10-11 — 3.2 done: `/submissions/<id>` is now the HTML page (`templates/submission.html`), replacing 2.4's JSON, and still reads only `submissions.public()`; its standing comes from the board (`board.rank`). Unranking reasons come before warnings; a problem dropped from the config shows its slug.
- 2026-10-11 — 3.3 done: `/rules` (`templates/rules.html`) from the problem config, the nav now has Board, Rules and Register on every page, and the board's install step links to `/rules#install`. Install steps stay a placeholder until plan 004 publishes the plugin. Screenshot fixes in the same commit (see 3.3's Result). Later, not today: boards reload with a meta refresh, as agreed, which can move a screen-reader user back to the top every 30 s (WCAG 2.2.1); a link to a board without the refresh would solve it if needed.
- 2026-10-11 — 5.1 done: `server/Dockerfile` (`python:3.12-slim`, requirements installed in their own layer before the code, code owned by root, runs as `golf` uid 10001 on port 8000) and `server/.dockerignore` (`data/`, `.agents-review/`, bytecode, `tests/`). `server/README.md` has the build and run commands. Local Docker checks use host port 8002, never 8000 or 8001.
- 2026-10-11 — 5.2 done: `AGENT_GOLF_DATA_DIR=/data` and `VOLUME /data` in the image, `/data` owned by `golf`; 5.1's in-container `server/data/` is gone, and `groupadd`/`useradd` lost `--system`, which only made useradd warn about uid 10001. A new named volume takes that owner; a bind mount must be writable by uid 10001 (in `server/README.md`, with `docker exec … python -m server.users` for scripted test users). Checked with a container restart and with a new container on the same volume.
- 2026-10-11 — Review fixes: stored logs are written 0600 whatever the umask (new test); `.dockerignore` also keeps out `**/*.db`, `**/*.sqlite`, `**/.env` and `**/uploads/` (checked with a decoy build context); `server/README.md` runs the container with `-p 127.0.0.1:8000:8000`; model names on the board no longer wrap at hyphens (checked at 390 px). Gate: `Ran 112 tests … OK`, `gate: ok`.
- 2026-10-11 — Terminal look (branch `design/terminal-ui`, picked by Anup from three directions in Claude Design): dark background, JetBrains Mono self-hosted under `server/static/fonts/` (SIL OFL, `OFL.txt`), green accent, amber for problems; comment-style headings, a `$ golf board <slug>` line, the rank-1 row highlighted, unranked reasons and submission status marked. Templates changed only in markup hooks (classes, the header wordmark); no route, text or test changed. Checked at 1440 and 390 px: no page wider than the screen; the board table scrolls sideways on phones. Gate: `Ran 112 tests … OK`, plugin 89 pass, `gate: ok`.
- 2026-10-11 — Merged `design/terminal-ui` (`a23af62`, a fast-forward). The database file is now 0600 too: `db.init_db` creates it 0600 before SQLite opens it and sets an existing one to 0600 at startup, so Anup's older `server/data/agent_golf.db` becomes 0600 the next time the server starts; SQLite gives its journal files the same mode. Two new tests in `test_config.py`. Gate: `Ran 114 tests … OK`, `gate: ok`.
- 2026-10-11 — Step 0 kept `help_me_unpack` at `"any"`/`"any"` for Monday (recorded in plan 001); the placeholder comment in `server/problems.py` is gone. The done-test is now a solved real session, supplied by Anup and uploaded with a test key, instead of `samples/pass.jsonl`. Next: wait for Amit's counter on `main` (4.1) and Anup's host details (5.4).
- 2026-10-12 — 4.1 done: merged `main` with Amit's counter (`3a5873b`); `server/submissions.py` imports from `server.counter`; the stand-in and its tests are deleted; `**/test_*.py` added to `.dockerignore`. The three samples give the verdicts in `samples/README.md`. 4.2 is now Anup's solved real session, which replaces the old sample check. Next: 4.2 (Anup's session) and 5.4 (Anup's host details).
- 2026-10-12 — `brute_force_zip` added to `server/problems.py` (`"any"`/`"any"`, after `help_me_unpack`), with a config test and an upload test. Six tests that assumed `help_me_unpack` was the only problem now either list their own problems or spell out both. Live check: `real-zip-redacted.jsonl` as `brute_force_zip` → `200` ranked, `usage_not_recorded`, 202,053 tokens, as `samples/README.md` says; the home page links the new board, which shows the row with its model. Gate: `Ran 127 tests … OK`, `gate: ok`.
- 2026-10-12 — 5.4 done: live at https://agent-golf.csbasics.in through a Cloudflare Tunnel (Anup's setup), container on `127.0.0.1:8077`. Merged `main` twice: `9b75809` (Amit's session-wide solved evidence, now deployed) and `8d63ed7` (the domain in `docs/spec.md`). The domain is now `agent-golf.csbasics.in` in this plan's current text and in `server/README.md` (new "Live site" section with the deploy commands); older Changelog lines keep the old name. Open: plain HTTP is served without a redirect (Cloudflare "Always Use HTTPS"), and 5.5's tunnel-log check.
- 2026-10-12 — Rules page: the install placeholder is replaced by the install step (`pi install npm:agent-golf@preview`), the start commands for each attempt (the plugin pointed at the site's own `AGENT_GOLF_API_BASE_URL`, with no other extensions, skills, context files, MCP or prompt templates) and the in-Pi steps. Rules 8 to 11 were added: token via `HACKATTIC_TOKEN`, the agent's commands print both replies, no `!` commands, no other add-ons. They are in `server/problems.py` and, word for word, in `docs/spec.md` "Rules for students" (a test keeps the two equal), so `rules_version` is now `mvp-2`. Rule 11 says "the start command on the rules page", not "above", because the rules also appear in the spec and in Pi's `/golf-problems`.
- 2026-10-12 — Redeployed `5e2b2b8` (rules page). Live `/rules` shows the install and start steps, `/api/v1/problems` lists both problems with `rules_version` `mvp-2`, and the user count was unchanged by the redeploy. Then, as Anup asked, deleted the test user `test_anup`, its one submission and its stored log, and nothing else. Both boards show "No submissions yet", and plain HTTP now gets a 301 to HTTPS.
- 2026-10-12 — 5.3 done: `feature/plan-002` merged into `main` (`--no-ff`) with `.agents/HANDOFF.md` rewritten in that merge commit, without the server's address. Gate on the merged tree: `Ran 132 tests … OK`, `gate: ok`. `feature/plan-002` was then moved to the same commit.
- 2026-10-12 — 5.5 done: no test key, `access_token` or upload content in the app's or the tunnel connector's log after a live login, a URL-key request and a marker upload. The connector logs failed requests' URLs during a redeploy only. The test user was deleted, and the live data is empty again.