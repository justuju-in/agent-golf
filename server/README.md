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

Add `-F folder_was_empty=true` (or `false`) to send what the plugin records; it is stored and has no effect on ranking. The reply is "Contract: website → plugin" in [`../docs/spec.md`](../docs/spec.md): `200` with `ranked` or `unranked`, or `401`, `400` or `413` with `rejected` and a reason; `500` means a counter bug. Its `url` opens the submission (plain JSON until the page in plan 002 step 3.2). The same file again returns the stored entry; the same session again replaces it, keeping its `url`. The raw file is kept in `uploads/` in the data directory and never served.

Until step 4.1, scoring is the stand-in in `standin_counter.py`: made-up numbers and verdicts, models named `standin/…`. Problems and their setup live in `problems.py`; only problems whose model and thinking level are set are accepted.
