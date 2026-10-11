// Opt-in transport/UI integration, NOT a real Hackattic solve or scoring validation.
// AGENT_GOLF_E2E_WEBSITE_DIR=/prepared/latest-website npm --prefix plugin test
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import { mkdtemp, mkdir, readFile, readdir, rm, stat, writeFile } from "node:fs/promises";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { promisify } from "node:util";
import { test } from "node:test";
import { startPi } from "./rpc-helper.mjs";
import { startWebsite } from "./website-helper.mjs";

const execute = promisify(execFile);
const websiteDir = process.env.AGENT_GOLF_E2E_WEBSITE_DIR;
const packageSource = process.env.AGENT_GOLF_E2E_PACKAGE_SOURCE;

async function unusedLoopbackPort() {
  const socket = createServer();
  await new Promise((done, reject) => socket.once("error", reject).listen(0, "127.0.0.1", done));
  const port = socket.address().port;
  await new Promise((done, reject) => socket.close((error) => error ? reject(error) : done()));
  return port;
}

test("packed plugin + real website: registration, browsing, cancel, upload, dedup and public privacy (not scoring proof)", {
  skip: websiteDir ? false : "set AGENT_GOLF_E2E_WEBSITE_DIR to a prepared website with catalogue/submission endpoints",
  timeout: 60_000,
}, async () => {
  const directory = await mkdtemp(join(tmpdir(), "golf-website-e2e-"));
  let website;
  let client;
  try {
    const checkout = resolve(websiteDir);
    if (packageSource) assert.match(packageSource, /^npm:agent-golf@(?:preview|\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?)$/, "registry verification must select this package explicitly");
    const port = await unusedLoopbackPort();
    const origin = `http://127.0.0.1:${port}`;
    const dataDir = join(directory, "data");
    const env = { ...process.env, AGENT_GOLF_DATA_DIR: dataDir, AGENT_GOLF_API_BASE_URL: origin };
    website = startWebsite(checkout, env, port);
    assert.equal(await website.origin, origin);
    const get = (path) => fetch(`${origin}${path}`, { redirect: "error", signal: AbortSignal.timeout(10_000) });
    const registered = await fetch(`${origin}/register`, {
      method: "POST", body: new URLSearchParams({ username: "plugin_e2e_test", hackattic_username: "private_hackattic_e2e" }),
      redirect: "error", signal: AbortSignal.timeout(10_000),
    });
    assert.equal(registered.status, 200);
    assert.equal(registered.headers.get("cache-control"), "no-store");
    const registration = await registered.text();
    const key = registration.match(/\/golf-login ([0-9a-f-]{36})/)?.[1];
    assert.ok(key, "registration page provides a disposable key");
    const catalogue = await (await get("/api/v1/problems")).json();
    assert.ok(catalogue.problems.some((problem) => problem.slug === "help_me_unpack"));

    const { stdout } = await execute("npm", ["pack", "--json", "--pack-destination", directory], { cwd: resolve("."), timeout: 30_000 });
    const [packed] = JSON.parse(stdout);
    const unpacked = join(directory, "unpacked");
    await mkdir(unpacked);
    await execute("tar", ["-xzf", join(directory, packed.filename), "-C", unpacked]);
    const home = join(directory, "home");
    const config = join(directory, "pi-config");
    const cwd = join(directory, "empty-attempt");
    await mkdir(home);
    await mkdir(cwd);
    const piEnv = { ...process.env, HOME: home, PI_CODING_AGENT_DIR: config, PI_TELEMETRY: "0", AGENT_GOLF_API_BASE_URL: origin };
    await execute("pi", ["install", packageSource ?? join(unpacked, "package"), "--no-approve"], { cwd, env: piEnv, timeout: 20_000 });
    const sessionFile = join(directory, "synthetic.jsonl");
    const timestamp = new Date().toISOString();
    const seed = [
      { type: "session", version: 3, id: randomUUID(), cwd, timestamp },
      { type: "custom", customType: "agent-golf-folder-check", id: "folder", parentId: null, timestamp,
        data: { schema: 1, state: "empty", policy: "zero-directory-entries", checked_at: timestamp } },
      { type: "message", id: "abandoned", parentId: "folder", timestamp,
        message: { role: "user", content: "E2E_PRIVATE_PROMPT_CANARY abandoned π branch", timestamp: Date.now() } },
      { type: "message", id: "active", parentId: "folder", timestamp,
        message: { role: "user", content: "E2E_PRIVATE_PROMPT_CANARY active branch", timestamp: Date.now() } },
    ];
    // Synthetic and deliberately unsolved; never publish it or treat a stand-in verdict as proof.
    const seedBytes = Buffer.from(seed.map((entry) => JSON.stringify(entry)).join("\r\n") + "\r\n");
    await writeFile(sessionFile, seedBytes, { mode: 0o600 });
    let selections = 0;
    let confirm = false;
    client = startPi({
      cwd, env: piEnv, sessionFile, sessionDir: join(directory, "sessions"), installedPackages: true,
      onRecord: (record) => {
        if (record.type !== "extension_ui_request") return;
        if (record.method === "editor") client.respondUI(record.id, "DISCARDED_EDIT");
        if (record.method === "select") client.respondUI(record.id, selections++ === 0 ? record.options[0] : undefined);
        if (record.method === "confirm") client.respondUI(record.id, confirm);
      },
    });
    const before = JSON.stringify((await client.request("get_entries")).entries);
    const messages = JSON.stringify((await client.request("get_messages")).messages);
    // Pi itself may append initialization (e.g. thinking level) on resume.
    // Commands must preserve the settled real session, not an earlier fixture snapshot.
    const bytes = await readFile(sessionFile);
    assert.ok(bytes.subarray(0, seedBytes.length).equals(seedBytes), "initial branch bytes retained on resume");
    const command = async (message, expected) => {
      const start = client.seen.length;
      assert.equal((await client.request("prompt", { message })).disposition, "handled");
      assert.ok(client.seen.slice(start).some((record) => record.method === "notify" && record.message.includes(expected)), "expected command notification");
    };
    await command(`/golf-login ${key}`, "Logged in as plugin_e2e_test");
    await command("/golf-problems", "Problem browsing closed");
    const views = client.seen.filter((record) => record.method === "editor");
    assert.equal(views.length, 2);
    assert.ok(views[0].prefill.includes(`Rules version: ${catalogue.rules_version}`));
    assert.ok(views[1].prefill.includes("help_me_unpack"));
    await command("/golf-submit help_me_unpack", "cancelled");
    assert.equal((await readdir(dataDir)).includes("uploads"), false, "cancelled upload stores nothing");
    confirm = true;
    await command("/golf-submit unknown_problem_e2e", "Submission rejected: unknown_problem");
    await command("/golf-submit help_me_unpack", "Submission ");
    const files = await readdir(join(dataDir, "uploads"));
    assert.equal(files.length, 1);
    const upload = join(dataDir, "uploads", files[0]);
    assert.deepEqual(await readFile(upload), bytes, "complete CRLF/Unicode bytes and abandoned branch retained");
    assert.equal((await stat(upload)).mode & 0o777, 0o600);
    await command("/golf-submit help_me_unpack", "Submission ");
    assert.deepEqual(await readdir(join(dataDir, "uploads")), files, "identical resubmit deduplicates");
    const { stdout: state } = await execute(join(checkout, ".venv", "bin", "python"), ["-c", `
import json, os, sqlite3
from pathlib import Path
conn = sqlite3.connect(Path(os.environ['AGENT_GOLF_DATA_DIR']) / 'agent_golf.db')
row = conn.execute('SELECT id, status, metrics, folder_was_empty FROM submissions').fetchone()
print(json.dumps({'id': row[0], 'status': row[1], 'metrics': json.loads(row[2]), 'folder': row[3], 'rows': conn.execute('SELECT COUNT(*) FROM submissions').fetchone()[0], 'key_hash': conn.execute('SELECT key_hash FROM users').fetchone()[0]}))
`], { cwd: checkout, env, timeout: 10_000 });
    const stored = JSON.parse(state);
    assert.equal(stored.rows, 1);
    assert.equal(stored.folder, 1);
    assert.ok(stored.key_hash === createHash("sha256").update(key).digest("hex"), "server keeps key hash only");
    assert.ok(client.seen.some((record) => record.method === "notify" && record.message.includes(`Submission ${stored.status}.`) && record.message.includes(`Tokens: ${stored.metrics.total_tokens ?? "unknown"};`) && record.message.includes(`${origin}/submissions/${stored.id}`)), "server reply is displayed unchanged");
    for (const path of ["/", "/rules", "/problems/help_me_unpack", `/submissions/${stored.id}`]) {
      const response = await get(path);
      assert.equal(response.status, 200);
      const page = await response.text();
      assert.ok(!page.includes(key) && !page.includes("E2E_PRIVATE_PROMPT_CANARY") && !page.includes(cwd) && !page.includes("private_hackattic_e2e"), "public page excludes private values");
    }
    assert.equal((await get(`/uploads/${files[0]}`)).status, 404);
    assert.deepEqual(await readFile(sessionFile), bytes);
    assert.ok(JSON.stringify((await client.request("get_entries")).entries) === before);
    assert.ok(JSON.stringify((await client.request("get_messages")).messages) === messages);
    assert.equal((await client.request("get_session_stats")).tokens.total, 0);
    assert.equal(client.seen.some((record) => record.type === "agent_start" || record.type === "message_start"), false);
    assert.ok(!JSON.stringify(client.seen).includes(key), "key never appears in Pi output/session");
  } finally {
    try { await client?.close(); }
    finally { try { await website?.stop(); } finally { await rm(directory, { recursive: true, force: true }); } }
  }
});
