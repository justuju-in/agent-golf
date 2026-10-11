# server

Website, upload API (plan 002) and the counter in `counter/` (plan 003). Contract: [`../docs/spec.md`](../docs/spec.md).

## Run locally

From the repo root, with `uv`:

```bash
uv venv --python 3.12                       # once
uv pip install -r server/requirements.txt   # again whenever requirements.txt changes
.venv/bin/uvicorn server.app:app --port 8000
```

| Variable | Default | Meaning |
|---|---|---|
| `AGENT_GOLF_DATA_DIR` | `server/data/` (beside this file, whatever the current directory; ignored by git) | SQLite database, and uploaded logs in `uploads/` (never served). Created at startup if missing. |
| `AGENT_GOLF_API_BASE_URL` | `http://localhost:8000` | Public origin, for absolute links in upload replies. Live: `https://agent-golf.justuju.in`. |

## Register

With the server running, open http://localhost:8000/register. The page that answers the form shows the key once, with `/golf-login <key>` ready to paste; only its SHA-256 is stored, so it cannot be shown again. Reloading that page sends the form again and gets "already taken".

## Test user (scripted)

For scripted test users, the command line does the same from the repo root, with the same `AGENT_GOLF_DATA_DIR` as the server, and prints the key once:

```bash
KEY=$(.venv/bin/python -m server.users alice alice_hackattic)
curl -i -H "Authorization: Bearer $KEY" http://localhost:8000/api/v1/me   # 200 {"username":"alice"}
```

For the plugin's `/golf-login <key>`, point its `AGENT_GOLF_API_BASE_URL` at `http://localhost:8000`. Never commit a key.

## Upload (as `/golf-submit` does)

```bash
curl -s -i -H "Authorization: Bearer $KEY" -F problem=help_me_unpack -F session=@path/to/session.jsonl \
  http://localhost:8000/api/v1/submissions
```

Add `-F folder_was_empty=true` (or `false`) to send what the plugin records; it is stored and has no effect on ranking. The reply is "Contract: website → plugin" in [`../docs/spec.md`](../docs/spec.md): `200` with `ranked` or `unranked`, or `401`, `400` or `413` with `rejected` and a reason; `500` means a counter bug. Its `url` opens the submission's page. The same file again returns the stored entry; the same session again replaces it, keeping its `url`. The raw file is kept in `uploads/` in the data directory, readable only by the server's user (mode 0600), and never served.

Until step 4.1, scoring is the stand-in in `standin_counter.py`: made-up numbers and verdicts, models named `standin/…`. Problems and their setup live in `problems.py`; only problems whose model and thinking level are set are accepted.

## Pages

- `/` is the board of the first listed problem in `problems.py`; every listed problem has its own at `/problems/<slug>`, and each board links the others. Ranked: each player's best ranked session, fewest tokens first (ties: fewer prompts, then fewer characters; equal scores share a rank), with a model column only when the problem's model is `"any"`. Unranked: the latest attempt of each player with no ranked session, with the reasons that unranked it. Boards reload themselves every 30 seconds, for the projector.
- `/submissions/<id>` (the `url` in upload replies): "Ranked #N" when it is the player's row on its board, "Ranked (not your best attempt)" when another of their sessions is, otherwise "Unranked"; tokens ("unknown" when not counted), prompts, characters and tool calls; the models and thinking levels that answered; solved; reasons in plain English, warnings marked; the submitted time.
- `/rules`: the rules from `problems.py` (which mirror `docs/spec.md`), each listed problem's Hackattic link, setup and instructions (the same problems as `GET /api/v1/problems`), the scoring line, and the login and submit steps. The install steps are a placeholder until the plugin is published.

Pages show only usernames, models, numbers and verdicts: never prompts, folders, session ids, raw logs, keys or Hackattic usernames.

## Problem list (as `/golf-problems` reads it)

```bash
curl -s -i http://localhost:8000/api/v1/problems   # public: no key
```

The reply is "Contract: problem list" in [`../docs/spec.md`](../docs/spec.md): the rules, `rules_version`, and every problem in `problems.py` whose model and thinking level are set (`"any"` counts as set). At startup the app checks the config against the list's limits (plain text, at most 1,000 characters per string and 64 KB in all, `challenge_url` exactly `https://hackattic.com/challenges/<slug>`) and refuses to start if `problems.py` breaks one.

## Docker

One image holds the website and the counter. From the repo root:

```bash
docker build -t agent-golf server/
docker run -d --name agent-golf -p 127.0.0.1:8000:8000 -v agent-golf-data:/data agent-golf
```

Then open http://localhost:8000/register. `127.0.0.1:` keeps the container's plain-HTTP port on this machine only; on the live host the HTTPS proxy is the only way in, so never publish it as `-p 8000:8000`. The image copies `server/` to `/app/server`, leaving out what `.dockerignore` lists (`data/`, `tests/`, review notes, bytecode, and any `*.db`, `*.sqlite`, `.env` or `uploads/`), installs `requirements.txt`, and runs `uvicorn server.app:app` on port 8000 as the non-root user `golf` (uid 10001), which can write only `/data`. Add `-e AGENT_GOLF_API_BASE_URL=…` when the site is reached at another origin than `http://localhost:8000`.

The image sets `AGENT_GOLF_DATA_DIR=/data`, a volume, so the database and uploaded logs are never in the image or in the container itself. The named volume `agent-golf-data` keeps them across `docker restart` and across a new container from a new image; `docker volume rm agent-golf-data` deletes them. A new named volume starts empty and owned by `golf`; a bind mount (`-v /some/dir:/data`) must be writable by uid 10001. Without `-v`, Docker makes an anonymous volume that a new container does not reuse.

A scripted test user, as above but inside the container, so in its `/data`:

```bash
KEY=$(docker exec agent-golf python -m server.users alice alice_hackattic)
```
