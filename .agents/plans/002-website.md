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
- [ ] **Phase 3 — Verification and handoff**
  - [ ] 3.1 Upload each file in `samples/` with a test key; rows appear correctly
  - [ ] 3.2 Gate passes; update `.agents/HANDOFF.md`

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

## Validation

- `bash tools/check.sh` passes.
- Register → upload → leaderboard works locally with the sample logs.

## Decisions

| Decision | Rationale | Rejected alternative |
|---|---|---|
| Store only key hashes | A leaked database does not leak keys | Plain-text keys |

## Changelog

- 2026-10-10 — created
