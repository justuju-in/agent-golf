// Opt-in: Anup's website checkout with its pinned requirements installed.
// AGENT_GOLF_WEBSITE_DIR=/absolute/website-checkout npm --prefix plugin test
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { randomUUID } from "node:crypto";
import { mkdtemp, mkdir, readFile, readdir, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { promisify } from "node:util";
import { test } from "node:test";
import { startPi } from "./rpc-helper.mjs";
import { startWebsite } from "./website-helper.mjs";

const execute = promisify(execFile);
const websiteDir = process.env.AGENT_GOLF_WEBSITE_DIR;

test("real website /me: Pi login, invalid key, offline server and missing-key guidance", {
  skip: websiteDir ? false : "set AGENT_GOLF_WEBSITE_DIR to a prepared website checkout",
  timeout: 45_000,
}, async () => {
  const directory = await mkdtemp(join(tmpdir(), "golf-website-login-"));
  let website;
  let client;
  try {
    const checkout = resolve(websiteDir);
    const env = { ...process.env, AGENT_GOLF_DATA_DIR: join(directory, "data"), AGENT_GOLF_API_BASE_URL: "http://127.0.0.1" };
    let key;
    try {
      const result = await execute(join(checkout, ".venv", "bin", "python"), [
        "-m", "server.users", "plugin_login_test", "local_smoke",
      ], { cwd: checkout, env, timeout: 10_000 });
      key = result.stdout.trim();
    } catch {
      // Never dump CLI output or exceptions that could contain the generated key.
      throw new Error("Disposable website user creation failed");
    }
    assert.ok(/^[0-9a-f-]{36}$/.test(key), "CLI must return a disposable UUID key");
    website = startWebsite(checkout, env);
    const origin = await website.origin;
    const response = await fetch(`${origin}/api/v1/me`, { headers: { Authorization: `Bearer ${key}` }, redirect: "error", signal: AbortSignal.timeout(10_000) });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("cache-control"), "no-store");
    const body = await response.json();
    assert.ok(body.username === "plugin_login_test");
    assert.ok(!JSON.stringify(body).includes(key), "website must not echo the key");
    const badKey = randomUUID();
    const rejected = await fetch(`${origin}/api/v1/me`, { headers: { Authorization: `Bearer ${badKey}` }, redirect: "error", signal: AbortSignal.timeout(10_000) });
    assert.equal(rejected.status, 401);
    assert.equal(rejected.headers.get("cache-control"), "no-store");
    await rejected.body?.cancel();

    const cwd = join(directory, "attempt");
    await mkdir(cwd);
    const sessionDir = join(directory, "sessions");
    client = startPi({
      cwd, sessionDir,
      env: { HOME: directory, PI_CODING_AGENT_DIR: join(directory, "pi-config"), AGENT_GOLF_API_BASE_URL: origin },
    });
    const before = (await client.request("get_entries")).entries;
    const messages = (await client.request("get_messages")).messages;
    const command = async (text, pattern) => {
      const start = client.seen.length;
      assert.equal((await client.request("prompt", { message: text })).disposition, "handled");
      assert.ok(client.seen.slice(start).some((record) => record.method === "notify" && pattern.test(record.message)), "expected actionable notification");
    };
    await command("/golf-submit help_me_unpack", /No key saved for this server\. Run \/golf-login <key> first/);
    await command(`/golf-login ${key}`, /Logged in as plugin_login_test/);
    const credentialFile = join(directory, ".config", "agent-golf", "credentials.json");
    const saved = await readFile(credentialFile);
    const credential = JSON.parse(saved).credentials[origin];
    assert.ok(credential.key === key && credential.username === "plugin_login_test", "key saved for exact local origin");
    assert.equal((await stat(credentialFile)).mode & 0o777, 0o600);
    assert.equal((await stat(join(directory, ".config", "agent-golf"))).mode & 0o777, 0o700);
    await command(`/golf-login ${badKey}`, /Invalid student key.*\/golf-login <key>/);
    assert.ok((await readFile(credentialFile)).equals(saved), "bad-key login preserves saved bytes");
    await website.stop();
    await command(`/golf-login ${key}`, /server unreachable.*retry \/golf-login/);
    assert.ok((await readFile(credentialFile)).equals(saved), "offline login preserves saved bytes");
    assert.ok(JSON.stringify((await client.request("get_entries")).entries) === JSON.stringify(before), "login leaves session entries unchanged");
    assert.ok(JSON.stringify((await client.request("get_messages")).messages) === JSON.stringify(messages), "login leaves model messages unchanged");
    assert.equal((await client.request("get_session_stats")).tokens.total, 0);
    assert.equal(client.seen.some((record) => record.type === "agent_start" || record.type === "message_start"), false);
    assert.ok(!JSON.stringify(client.seen).includes(key) && !JSON.stringify(client.seen).includes(badKey), "keys absent from Pi output");
    // Fresh custom-only sessions may stay in memory; inspect persisted files too.
    for (const filename of await readdir(sessionDir)) {
      if (filename.endsWith(".jsonl")) {
        const log = await readFile(join(sessionDir, filename), "utf8");
        assert.ok(!log.includes(key) && !log.includes(badKey), "keys absent from session files");
      }
    }
  } finally {
    try { await client?.close(); }
    finally {
      try { await website?.stop(); }
      finally { await rm(directory, { recursive: true, force: true }); }
    }
  }
});
