# plugin

Pi extension adding `/golf-login` and `/golf-submit`. It only uploads the raw session file and never calls the model. Plan: [`../.agents/plans/004-plugin-and-deploy.md`](../.agents/plans/004-plugin-and-deploy.md).

## Development

From the repo root, load the extension with the confirmed default API origin, `https://agent-golf.justuju.in`:

```bash
pi --extension ./plugin/index.ts
```

For local testing, override the origin explicitly:

```bash
AGENT_GOLF_API_BASE_URL=http://localhost:8000 pi --extension ./plugin/index.ts
```

The server must implement the endpoints in the [spec](../docs/spec.md). Both login and submit use the same origin configuration. Only HTTPS or loopback HTTP origins are accepted, and redirects are refused. An empty or invalid override is an error: it never silently falls back to production. Loading the extension alone makes no HTTP requests.

Run `/golf-login <student-key>` in Pi. After validation, credentials are stored separately per origin in `~/.config/agent-golf/credentials.json` (directory 0700, file 0600). This file contains the original key so the client can authenticate; do not share or commit it. Failed login leaves existing credentials intact. Changing the configured origin never reuses or migrates another origin's key; log in for the new origin. Credential writes are atomic and serialized within one Pi process, not coordinated across separate Pi processes.

Run `/golf-submit help_me_unpack` from your saved attempt session. Pi must be idle, and all user Bash commands (`!` / RPC `bash`) must have recorded their results. A confirmation shows the server, problem and file size, and warns that the complete raw log may contain tokens, prompts and local paths. Cancelling sends nothing. If the session changes while confirmation is open, submission is refused; try again when idle.

User Bash starts are tracked with custom session metadata containing only a SHA-256 command hash, outside model context. A start stays pending until a matching Bash result is recorded; the guard is reconstructed from session entries after reload. If a start has no recorded result (for example, another extension blocks execution), submission fails closed rather than guessing that the attempt is complete.

Submission uploads unchanged JSONL bytes (including abandoned branches), using only the credential saved for the configured origin. Known folder observations are sent as the optional `folder_was_empty` field; unknown/inherited observations are omitted. The plugin displays the server's status, reasons, metrics and link without computing scores. It refuses redirects, makes no automatic retries, and warns about uncertain delivery after a network failure. Check the website before retrying.

Run `bash tools/check.sh` to exercise login and submission against temporary mock servers and isolated Pi sessions. Tests use disposable keys and temporary credential directories; no real API or credentials are required. Node 22.19+ and `pi` on PATH are required.

Student install steps go here once publishing is implemented.
