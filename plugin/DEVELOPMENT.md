# Plugin development (private)

This guide is excluded from npm. Student usage is in [README.md](README.md); maintainer publishing steps are in [RELEASING.md](RELEASING.md).

Pi extension adding `/golf-login`, `/golf-submit` and `/golf-problems`. It only uploads the raw session file and never calls the model. Plan: [`../.agents/plans/004-plugin-and-deploy.md`](../.agents/plans/004-plugin-and-deploy.md).

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

Run `/golf-problems` to browse public contest rules and problem setup. It first opens the rules in a temporary plain-text view, then lets you choose a problem for its URL, instructions, model and thinking level. Closing a detail view returns to the list; cancel the list to exit. Empty lists still show the rules. Interactive Pi uses custom read-only views with explicit navigation hints and keyboard scrolling. RPC retains multi-line editor dialogs with explanatory navigation titles; edits are discarded. No browsing output is inserted into your prompt or session. `any` setup is shown as "any model, one per session" / "any thinking level". Browsing sends no key, cookie or log, changes no setup, and does not bind or start an attempt. The catalogue is advisory; submission checks are authoritative. Replies are bounded to 64 KB and strings to 1,000 Unicode characters, with terminal-control/unsafe URL checks and no markup rendering.

Run `/golf-submit help_me_unpack` from your saved attempt session. Pi must be idle, and all user Bash commands (`!` / RPC `bash`) must have recorded their results. A confirmation shows the server, problem and file size, and warns that the complete raw log may contain tokens, prompts and local paths. Cancelling sends nothing. If the session changes while confirmation is open, submission is refused; try again when idle.

User Bash starts are tracked with custom session metadata containing only a SHA-256 command hash, outside model context. A start stays pending until a matching Bash result is recorded; the guard is reconstructed from session entries after reload. If a start has no recorded result (for example, another extension blocks execution), submission fails closed rather than guessing that the attempt is complete.

Submission uploads unchanged JSONL bytes (including abandoned branches), using only the credential saved for the configured origin. Known folder observations are sent as the optional `folder_was_empty` field; unknown/inherited observations are omitted. The plugin displays the server's status, reasons, metrics and link without computing scores. A null total paired with `missing_usage` is shown as `Tokens: unknown`, never zero. `usage_not_recorded` and `model_switched` are displayed with the server's verdict; the plugin does not decide eligibility or change the chosen model. It refuses redirects, makes no automatic retries, and warns about uncertain delivery after a network failure. Check the website before retrying.

Run `bash tools/check.sh` to exercise login, submission and problem browsing against temporary mock servers and isolated Pi sessions. Tests use disposable keys and temporary credential directories; no real API or credentials are required. Node 22.19+ and `pi` on PATH are required. The Unix interactive-browser smoke test also uses Python 3's standard-library PTY/HTTP support; Windows skips that test. Viewer tests cover Unicode widths, wrapped navigation at narrow widths, scrolling/resize, configured navigation keys, cancellation and read-only behavior. Extremely small terminals show a resize prompt rather than misleading clipped actions. PTY tests wait for explicit extension readiness and expected screens with bounded deadlines, not fixed startup sleeps.

### Optional real website login test

From the repo root, prepare Anup's website in a separate worktree (never merge its implementation into the plugin branch):

```bash
git fetch origin
git worktree add --detach ../agent-golf-website-test origin/feature/plan-002
python3.12 -m venv ../agent-golf-website-test/.venv
../agent-golf-website-test/.venv/bin/python -m pip install -r ../agent-golf-website-test/server/requirements.txt
AGENT_GOLF_WEBSITE_DIR="$(realpath ../agent-golf-website-test)" bash tools/check.sh
```

The opt-in test creates a disposable user through the website CLI, starts the real API on an ephemeral loopback port, and exercises Pi login success, invalid-key and offline-server failures, plus missing-key submission guidance. It checks private credential permissions, preservation after failures, zero model calls and unchanged session state. Keys are captured privately, not printed. The server is stopped and temporary data/credentials are deleted afterward. Normal gate runs skip this test when `AGENT_GOLF_WEBSITE_DIR` is absent; they still run all mock and isolated Pi tests.

The prepared website checkout remains available for reruns. Remove it when finished:

```bash
git worktree remove --force ../agent-golf-website-test
```

### Optional packed-plugin / real website integration

Prepare a current website checkout with its exact pinned requirements as above; it must include registration, catalogue and submission endpoints. Enable both integration tests from the repo root:

```bash
AGENT_GOLF_WEBSITE_DIR="$(realpath ../agent-golf-website-test)" \
AGENT_GOLF_E2E_WEBSITE_DIR="$(realpath ../agent-golf-website-test)" \
bash tools/check.sh
```

The second opt-in test packs the public plugin, extracts it outside the repo, installs it in isolated Pi settings and exercises real website registration, login, rule/problem views, cancelled/unknown-problem uploads, byte-for-byte upload and resubmission deduplication. It checks stored folder metadata, server key hashing, private upload permissions, public-page exclusions, unchanged session state and zero model calls. Synthetic CRLF/Unicode session bytes include an abandoned branch; Pi's normal resume initialization is allowed before the command-state snapshot. No real Hackattic account or solve is used. Everything generated is private and removed after the test.

After publication, verify the real registry installation with the same isolated workflow:

```bash
AGENT_GOLF_WEBSITE_DIR="$(realpath ../agent-golf-website-test)" \
AGENT_GOLF_E2E_WEBSITE_DIR="$(realpath ../agent-golf-website-test)" \
AGENT_GOLF_E2E_PACKAGE_SOURCE=npm:agent-golf@0.1.0 \
bash tools/check.sh
```

Without the last variable the test installs the extracted local artifact; with it, Pi downloads the explicit public package/version instead. It accepts only this package's explicit versions or preview tag. Test preview-channel installation separately with `AGENT_GOLF_E2E_PACKAGE_SOURCE=npm:agent-golf@preview`.

This is transport/UI/privacy validation, **not scoring or ranked-attempt proof**. Website scoring may still be the stand-in; inspect its counter import and validate the integrated real counter against the current spec separately. Do not advertise competition readiness based only on this test. Normal runs skip this test without `AGENT_GOLF_E2E_WEBSITE_DIR`.
