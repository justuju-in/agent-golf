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
| `AGENT_GOLF_DATA_DIR` | `server/data/` (beside this file, whatever the current directory; ignored by git) | SQLite database, later also uploaded logs. Created at startup if missing. |
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
