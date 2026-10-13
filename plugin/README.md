# Agent Golf for Pi

Pi commands for the Agent Golf coding-agent leaderboard. Login, browsing and submission never call a model or compute scores locally.

**0.1.2:** fixes `/golf-submit` on Windows ("Stored credentials could not be read securely") and shows `any` model setup as "any model". Uses https://agent-golf.csbasics.in.

## Install and update

Requires Node.js 22.19+ and the Pi coding agent (tested with Pi 1.1.0).

```bash
pi install npm:agent-golf
```

Unversioned installations follow `latest`. The `preview` channel also receives this URL update; existing preview users can keep that installation source.

Start a new Pi process, or run `/reload` in an existing one. To update an unpinned installation:

```bash
pi update --extensions
```

Restart Pi or `/reload` afterward. An exact version such as `npm:agent-golf@0.1.0` is pinned; updating does not advance it to a different version. Remove the old pinned source (`pi remove npm:agent-golf@0.1.0`), then install `npm:agent-golf@0.1.2` explicitly to replace that pin. The `npm:agent-golf@preview` installation follows the preview channel; it does not automatically switch to `latest`.

**Updating from 0.1.0:** the default server origin changed. Unset any old `AGENT_GOLF_API_BASE_URL` override, update/restart Pi, and run `/golf-login` with your student key valid on the new website. Old-origin credentials are preserved but never migrated or sent to the new origin.

## Commands

### `/golf-problems`

Browse public contest rules, challenge URLs, instructions and each problem's model/thinking setup. Rules open first, followed by a problem selector. Close a detail view to return to the list; cancel the list to exit. An empty list still shows the rules.

Interactive Pi uses read-only, scrollable text views: Enter on rules opens the problem list, Esc closes browsing, and Enter/Esc on details returns to the list. Arrow keys, Page Up/Down and Home/End scroll; navigation hints use your configured confirm/cancel keys. RPC clients retain temporary text-editor dialogs with explicit navigation titles; all edits are discarded. Nothing is inserted into your prompt or session. `any` setup is displayed as "any model" or "any thinking level".

Browsing sends no key, cookie or session log, makes no model calls, and never starts/binds an attempt or changes your setup. The catalogue is advisory; server submission checks are authoritative. Replies are bounded to 64 KB and strings to 1,000 Unicode characters, with terminal-safety and exact Hackattic URL checks.

### `/golf-login <student-key>`

Use the key provided by the Agent Golf website. Validation succeeds before anything is saved. Invalid keys and network/server failures preserve any existing saved credentials.

Credentials are stored separately per server origin in `~/.config/agent-golf/credentials.json`, with directory mode 0700 and file mode 0600. This file contains the original key so the client can authenticate: never share or commit it. Writes are atomic within one Pi process, but are not locked across separate Pi processes. Changing origins never reuses or migrates another server's key.

### `/golf-submit <problem-slug>`

For example:

```text
/golf-submit help_me_unpack
```

Submit from the saved session where you solved the problem. Pi must be idle and all user Bash commands must have recorded their results. Confirm the problem, server, byte size and privacy warning before upload; cancelling sends nothing.

**Privacy:** submission uploads the complete unchanged raw JSONL, including abandoned branches. It may contain prompts, local paths, Hackattic access tokens and other sensitive material. Only submit to a server you trust. The website must keep raw logs private; public leaderboard rows should show only permitted identity, metrics and verdicts.

If the session or file changes during confirmation, submission is refused. Folder observations, when known, are sent as informational metadata, not proof that an attempt is eligible. Unknown/forked observations are omitted. User Bash starts are tracked by command hashes outside model context; missing recorded results block submission rather than guessing completion.

The server owns scores and status. A null total with `missing_usage` is displayed as `Tokens: unknown`, never zero. Warnings and model-switch reasons are displayed without client-side reranking.

## Server configuration

Default API origin: **https://agent-golf.csbasics.in**.

For a trusted local server:

```bash
AGENT_GOLF_API_BASE_URL=http://127.0.0.1:8000 pi
```

Both authentication and browsing/submission use this origin. Only HTTPS and loopback HTTP are accepted; no credentials, API path, query or fragment belong in the origin. Empty/invalid overrides fail closed and never fall back silently to production. Redirects are refused. Loading the extension alone makes no HTTP requests.

## Troubleshooting

- **No key saved:** run `/golf-login <student-key>` for the configured server.
- **Invalid key:** retry with your registered key; existing credentials remain unchanged.
- **Problem list unavailable:** check the configured origin and server availability; the endpoint may not yet be available.
- **Pi busy or pending Bash:** wait for the response/Bash result to finish recording.
- **No persisted session file:** submit from the saved attempt, not a fresh custom-only session that has not flushed to disk.
- **Upload/network error:** the upload may already have reached the server. Check the website before retrying. The plugin never retries automatically.

Removing the package with `pi remove npm:agent-golf` (use the source you installed, e.g. `npm:agent-golf@preview`) does not remove your credential file. Delete that file separately only if you intend to discard saved logins.

## License

MIT for this plugin. This package contains no website/backend implementation or private repository material.
