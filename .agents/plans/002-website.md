---
name: 002-website
description: Registration, upload API, leaderboard and submission pages in server/.
status: created
created: 2026-10-10
updated: 2026-10-10
---

# Website

## Progress

- [ ] **Phase 1 — Accounts and upload**
  - [ ] 1.1 Pick the stack and add its test command to `tools/check.sh`
  - [ ] 1.2 Register page: username + Hackattic username → show secret key once
  - [ ] 1.3 `GET /api/v1/me` checks a key (used by `/golf-login`)
  - [ ] 1.4 `POST /api/v1/submissions` per `docs/spec.md`: check key, store file, call counter, store result
- [ ] **Phase 2 — Pages**
  - [ ] 2.1 Leaderboard: one board per problem, ranked rows first, unranked below with reasons
  - [ ] 2.2 Submission page: username, model, numbers, solved; never prompts or raw log
- [ ] **Phase 3 — Docker and deployment** (moved here from plan 004)
  - [ ] 3.1 `server/Dockerfile`: one image with the website and the counter
  - [ ] 3.2 Database and uploads in a mounted volume; survive a container restart
  - [ ] 3.3 Deploy with HTTPS at agent-golf.justuju.in
  - [ ] 3.4 Keys and uploads never appear in server logs
- [ ] **Phase 4 — Verification and handoff**
  - [ ] 4.1 Upload each file in `samples/` with a test key; rows appear correctly
  - [ ] 4.2 Tell Prateek the live URL so the plugin defaults to it
  - [ ] 4.3 Gate passes; tick this plan and add to its Changelog (`HANDOFF.md` only when merging to `main`)

## Goal

Students can register, upload, and see the board. Done when uploading `samples/pass.jsonl` with a valid key shows a ranked row.

## Context

- Contract and rules: `docs/spec.md` (do not change without telling the others).
- Counter: `server/counter/` (plan 003). Until it lands, call a stub that returns fixed numbers in the spec's shape.
- Suggested stack (change in 1.1 if you prefer): Python + FastAPI + SQLite; plain server-rendered HTML.

## Steps

### Phase 1 — Accounts and upload

#### 1.2 Register
- Files: `server/`
- Do: username `[a-z0-9_]{3,32}` unique (lowercased); key = random UUID; store only SHA-256(key); 409 on duplicate username.
- Acceptance: registering twice with the same name fails; the key never appears in the database or logs.

#### 1.4 Upload
- Files: `server/`
- Do: bearer key → user; reject non-JSONL or oversized files (limit 20 MB); same Pi session id from the same user replaces the earlier row; identical file returns the existing entry.
- Acceptance: test uploads of `samples/*.jsonl` return the reply shape in `docs/spec.md`.

### Phase 2 — Pages

#### 2.1 Leaderboard
- Files: `server/`
- Do: sort ranked rows by `(total_tokens, prompts, chars_typed)`; equal scores share a rank; each student shows only their best ranked session.
- Acceptance: with the three samples uploaded, only `pass` and `script` are ranked.

### Phase 3 — Docker and deployment

#### 3.1 Dockerfile
- Files: `server/Dockerfile`, `server/.dockerignore`
- Do: copy the whole `server/` folder (so `server/counter/` is always included); install from a pinned requirements file; run as a non-root user; one port.
- Acceptance: `docker build -t agent-golf server/ && docker run -p 8000:8000 -v agent-golf-data:/data agent-golf` serves the register page locally.

#### 3.2 Persistent data
- Files: `server/` config
- Do: database file and uploaded logs live under `/data` (a Docker volume), never inside the image.
- Acceptance: register a user, restart the container, the user and their submissions are still there.

#### 3.3 Deploy
- Files: deployment notes in `server/README.md`
- Do: deploy the container to a host of your choice; HTTPS before any key is issued; use the host's real DNS target, do not guess it.
- Acceptance: `https://agent-golf.justuju.in/` loads and registration works.

## Validation

- `bash tools/check.sh` passes.
- Register → upload → leaderboard works locally with the sample logs.
- The same works on the live site, from the Docker container.

## Decisions

| Decision | Rationale | Rejected alternative |
|---|---|---|
| Store only key hashes | A leaked database does not leak keys | Plain-text keys |
| Website owner also deploys, using Docker | One person owns the server end to end; the counter ships inside the same image | Separate deploy owner (was plan 004) |

## Changelog

- 2026-10-10 — created
- 2026-10-10 — Anup owns this plan; Docker and website deployment added (moved from plan 004)
