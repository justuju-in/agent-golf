---
name: 002-website
description: Registration, key check, upload and problem-list API, leaderboard pages, Docker and deployment in server/ (never server/counter/).
status: started
created: 2026-10-10
updated: 2026-10-10
---

# Website

## Progress

- [ ] **Phase 1 — Agreements**
  - [x] 1.1 Contract and process on `main`: upload status codes, reason codes, counter return and `NotPiLogError`, HANDOFF rule, gate on Python 3.12 (`d412128`, `278dc35`)
  - [x] 1.2 Second round on `main`: per-problem setup and problem config, problem list contract, generic "solved" check, usage reason codes, `agent-golf.justuju.in` (`d32ff18`, `d5062d5`)
- [ ] **Phase 2 — API, against a stand-in counter**
  - [x] 2.1 Stack skeleton (FastAPI, Jinja, SQLite, Python 3.12, pinned `server/requirements.txt`) and `GET /api/v1/me` exactly per `docs/spec.md`
  - [x] 2.2 Register page → key page: username + Hackattic username, key shown once, only its SHA-256 stored
  - [x] 2.3 Stand-in counter in `server/` (never `server/counter/`): the spec's `score()`, `NotPiLogError` and reason sets; gives ranked and unranked results
  - [x] 2.4 Problem config, then `POST /api/v1/submissions` per `docs/spec.md`: checks, store file, call counter with the problem's setup, store result, reply
  - [ ] 2.5 `GET /api/v1/problems` per `docs/spec.md`, built from the problem config
- [ ] **Phase 3 — Pages**
  - [ ] 3.1 Board per problem: ranked rows, then unranked players; 30-second refresh; projector-size text
  - [ ] 3.2 Submission page: username, model, numbers, solved, reasons; never prompts, folders or raw log
  - [ ] 3.3 Rules page: the seven rules, each problem's instructions and setup, scoring, install and submit steps
- [ ] **Phase 4 — Real counter** (after Amit merges `counter` to `main`)
  - [ ] 4.1 Bring `main` into this branch; import from `server.counter`; delete the stand-in
  - [ ] 4.2 Upload each file in `samples/` with a test key; rows and verdicts match `samples/README.md`
- [ ] **Phase 5 — Docker and deployment at agent-golf.justuju.in**
  - [ ] 5.1 `server/Dockerfile`: one image with the website and the counter
  - [ ] 5.2 Database and uploads in a mounted volume; survive a container restart
  - [ ] 5.3 Merge `feature/plan-002` to `main`; update `.agents/HANDOFF.md` in that merge
  - [ ] 5.4 Deploy with HTTPS at agent-golf.justuju.in; confirm a 19 MB upload reaches the app
  - [ ] 5.5 Keys and uploads never appear in server or proxy logs
- [ ] **Phase 6 — Verification and handoff**
  - [ ] 6.1 Upload each file in `samples/` to the live site with a test key; rows appear correctly
  - [ ] 6.2 Tell Prateek the live site is up, so the plugin's default `AGENT_GOLF_API_BASE_URL` works
  - [ ] 6.3 Gate passes; tick this plan and add to its Changelog

## Goal

Students can register, upload, and see the board. Done when uploading `samples/pass.jsonl` with a valid key shows a ranked row on the live site.

## Context

- Contract and rules: `docs/spec.md`. "Contract: student key validation" is Prateek's and fixed; the rest was agreed in 1.1 and 1.2. Change none of it without telling the other two.
- Counter: `server/counter/` is Amit's (branch `counter`, plan 003); never create or edit files there. Until it merges, the website calls the stand-in from 2.3, which has the same names (`score`, `NotPiLogError`, `UNRANKING_REASONS`, `WARNING_REASONS`); 4.1 swaps the import. "Solved" is one generic check inside the counter, so the website never needs per-problem scoring code.
- Problem config (`server/`, from 2.4): one entry per Hackattic problem with slug, title, Hackattic URL, instructions, model (`provider/model` or `"any"`) and thinking level (a level or `"any"`), plus the rules text and `rules_version`. It is the single source for the problem list, the `unknown_problem` check, the `agreed` setup sent to the counter, and the board and rules pages. Adding a problem means adding an entry. For now `help_me_unpack` is `"any"`/`"any"` so uploads aren't refused; a comment says Step 0 (plan 001) sets the real values.
- Models (`docs/spec.md`, 810982a and c1b61da): only models and levels that actually answered count. With `"any"` the match is skipped, but a model-`"any"` session that used more than one model gets `model_switched` (unranks). The board shows a model column only when the problem's model is `"any"`; the submission page always shows the model.
- Plugin: Prateek (plan 004) reads the server origin from `AGENT_GOLF_API_BASE_URL` (`http://localhost:8000` locally, `https://agent-golf.justuju.in` live). The website reads the same variable to build the absolute `url` in replies.
- Data: SQLite database and uploaded logs live in `AGENT_GOLF_DATA_DIR` (default `server/data/`, ignored by `server/.gitignore`; `/data` in Docker). Review notes from workflows land in `server/.agents-review/`, ignored by the root `.gitignore`.
- Local setup: `uv venv --python 3.12 && uv pip install -r server/requirements.txt`; run `.venv/bin/uvicorn server.app:app --port 8000`. `server/README.md` keeps the exact commands.
- Look: plain, light, server-rendered pages; text `#272426`, accent `#c46c34`. JavaScript only for the copy button; the board reloads with a meta refresh.
- Public pages show only username, model, numbers and verdicts: never prompts, folder paths, raw logs, keys or Hackattic usernames.
- `metrics.total_tokens` is `null` when the counter sets `missing_usage` (unranked); pages show "unknown" for it.
- Upload size: Starlette (under FastAPI) caps non-file multipart fields at 1 MB by default, so read `session` as a file part and enforce 20 MB ourselves; check against the pinned version. The proxy in 5.4 must allow a little over 20 MB per request (nginx defaults to 1 MB), or students hit the proxy's error first.

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
  - Problem config as in Context; `help_me_unpack` entry first, with model `"any"` and thinking level `"any"` for now and a comment that Step 0 sets the real values.
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

### Phase 3 — Pages

#### 3.1 Board
- Files: `server/` templates
- Do: one board per problem at `/problems/<slug>`; the home page shows the first listed problem's board and links the others. Header: problem title, its model and thinking level ("any model, one per session" for `"any"`), the scoring line. Ranked rows sorted by `(total_tokens, prompts, chars_typed)`, equal scores share a rank, each player only their best ranked session; columns rank, player, tokens, prompts, chars, tool calls, submitted, plus a model column only when the problem's model is `"any"` (hidden when the problem has one fixed model). Below, "Unranked": each player's latest unranked attempt, only if that player has no ranked row, with reasons in plain English. Footer: install → `/golf-login` → solve → `/golf-submit`. Meta refresh every 30 s; text sized for a projector.
- Acceptance: with the stand-in, mixed uploads show ranked rows in order and only the allowed unranked rows; the model column appears for an `"any"` problem and not for a fixed-model one; the page reloads itself every 30 s.

#### 3.2 Submission page
- Files: `server/` templates
- Do: `/submissions/<id>`: Ranked #N or Unranked, the four numbers large ("unknown" for a null total), model and thinking level, solved yes/no, reasons in plain English (warnings marked as such), submitted time.
- Acceptance: the `url` in an upload reply opens this page; its HTML contains no prompt text, `cwd` or Hackattic username.

#### 3.3 Rules page
- Files: `server/` templates
- Do: the rules text from the problem config (mirrors `docs/spec.md`), each listed problem's title, Hackattic link, instructions, model and thinking level, the scoring line, and install, login and submit steps (install command from plan 004 once Prateek publishes it).
- Acceptance: linked from every page's header; shows the same problems and setups as `GET /api/v1/problems`.

### Phase 4 — Real counter

#### 4.1 Swap
- Files: `server/` (one import); delete `server/standin_counter.py` and its tests
- Do: after `counter` merges, bring `main` into this branch; `from server.counter import score, NotPiLogError, UNRANKING_REASONS, WARNING_REASONS`.
- Acceptance: the gate passes with both the counter's and the website's tests.

### Phase 5 — Docker and deployment

#### 5.1 Dockerfile
- Files: `server/Dockerfile`, `server/.dockerignore`
- Do: Python 3.12 slim base; copy the whole `server/` folder to `/app/server` so `server.counter` imports work as in the repo; install from the pinned requirements; run as a non-root user; one port (8000).
- Acceptance: `docker build -t agent-golf server/ && docker run -p 8000:8000 -v agent-golf-data:/data agent-golf` serves the register page locally.

#### 5.2 Persistent data
- Files: `server/` config
- Do: `AGENT_GOLF_DATA_DIR=/data` in the image; database file and uploaded logs live in the volume, never inside the image.
- Acceptance: register a user, restart the container, the user and their submissions are still there.

#### 5.4 Deploy
- Files: deployment notes in `server/README.md`
- Do: Justuju server or a small VPS (any Docker host with a persistent volume and HTTPS); HTTPS before any key is issued; point `agent-golf.justuju.in` at the host's real DNS target, do not guess it; set `AGENT_GOLF_API_BASE_URL=https://agent-golf.justuju.in`; the proxy allows a little over 20 MB per request.
- Acceptance: `https://agent-golf.justuju.in/` loads, registration works, and a 19 MB upload reaches the app (it answers with the app's own JSON, not a proxy error page).

#### 5.5 No keys or uploads in logs
- Files: `server/` run config, proxy config
- Do: uvicorn's access log prints query strings, so a key a student wrongly puts in `?key=` is logged even though it is rejected: turn the access log off or strip query strings, in the proxy too. Keep FastAPI's telemetry export off (its redaction does not cover `key`).
- Acceptance: after a login, an upload and a `GET /api/v1/me?key=<key>` against the live site, searching the server and proxy logs for that key finds nothing.

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