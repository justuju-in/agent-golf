# plugin

Pi extension adding `/golf-login` and `/golf-submit`. It only uploads the raw session file and never calls the model. Plan: [`../.agents/plans/004-plugin-and-deploy.md`](../.agents/plans/004-plugin-and-deploy.md).

## Development

From the repo root, load the extension with an explicitly configured server origin:

```bash
AGENT_GOLF_API_BASE_URL=http://localhost:8000 pi --extension ./plugin/index.ts
```

The server must implement `GET /api/v1/me` from the [spec](../docs/spec.md). The production address is not finalized; there is no default origin yet. Only HTTPS or loopback HTTP origins are accepted, and login redirects are refused.

Run `/golf-login <student-key>` in Pi. After validation, credentials are stored separately per origin in `~/.config/agent-golf/credentials.json` (directory 0700, file 0600). This file contains the original key so the client can authenticate; do not share or commit it. Failed login leaves existing credentials intact. Credential writes are atomic and serialized within one Pi process, not coordinated across separate Pi processes.

`/golf-submit` is still a stub; nothing is uploaded yet.

Run `bash tools/check.sh` to exercise login against temporary mock servers and an isolated Pi session. Tests use disposable keys and temporary credential directories; no real API or credentials are required. Node 22.19+ and `pi` on PATH are required.

Student install steps go here once publishing is implemented.
