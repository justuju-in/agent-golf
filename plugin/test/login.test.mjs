import assert from "node:assert/strict";
import { createServer } from "node:http";
import { mkdtemp, mkdir, readFile, readdir, rm, stat, symlink, writeFile, chmod } from "node:fs/promises";
import { join } from "node:path";
import { startPi } from "./rpc-helper.mjs";
import { tmpdir } from "node:os";
import { test } from "node:test";
import { getApiOrigin, loginStudent } from "../login.ts";

const KEY = "00000000-0000-4000-8000-000000000001";
const OTHER_KEY = "00000000-0000-4000-8000-000000000002";

async function fixture(t) {
  const directory = await mkdtemp(join(tmpdir(), "golf-login-test-"));
  const credentialDir = join(directory, "agent-golf");
  const file = join(credentialDir, "credentials.json");
  const requests = [];
  let reply = (_request, response) => {
    response.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" });
    response.end(JSON.stringify({ username: "student_1" }));
  };
  const server = createServer((request, response) => {
    requests.push({ path: request.url, method: request.method, authorization: request.headers.authorization });
    reply(request, response);
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  t.after(async () => {
    server.closeAllConnections();
    await new Promise((resolve) => server.close(resolve));
    await rm(directory, { recursive: true, force: true });
  });
  return {
    directory, credentialDir, file, requests, origin, server,
    options: { baseUrl: origin, credentialDir },
    setReply: (handler) => { reply = handler; },
  };
}

function assertSecretFree(result) {
  assert.equal(JSON.stringify(result).includes(KEY), false);
  assert.equal(JSON.stringify(result).includes(OTHER_KEY), false);
}

async function saved(f) {
  return JSON.parse(await readFile(f.file, "utf8"));
}

test("API origin is canonical and restricts insecure or credential-bearing URLs", () => {
  assert.equal(getApiOrigin(" https://EXAMPLE.com:443/ "), "https://example.com");
  for (const origin of ["http://localhost:8000", "http://127.0.0.1:8000", "http://[::1]:8000"]) {
    assert.equal(getApiOrigin(origin), origin);
  }
  for (const origin of [undefined, "", "not-a-url", "http://example.com", "ftp://localhost", "https://user:password@example.com", "https://example.com/api", "https://example.com?key=x", "https://example.com#x", "http://localhost.example.com"]) {
    assert.throws(() => getApiOrigin(origin));
  }
});

test("missing key/origin or invalid origin performs no request or credential write", async (t) => {
  const f = await fixture(t);
  for (const [args, options] of [["", f.options], ["two keys", f.options], [KEY, { ...f.options, baseUrl: "" }], [KEY, { ...f.options, baseUrl: "http://example.com" }]]) {
    assertSecretFree(await loginStudent(args, options));
  }
  assert.equal(f.requests.length, 0);
  await assert.rejects(readFile(f.file), { code: "ENOENT" });
});

test("valid login sends Bearer key to /me and saves private per-origin credentials", async (t) => {
  const f = await fixture(t);
  const result = await loginStudent(KEY, f.options);
  assert.equal(result.type, "info");
  assert.equal(result.message, `Logged in as student_1 on ${f.origin}.`);
  assertSecretFree(result);
  assert.deepEqual(f.requests, [{ method: "GET", path: "/api/v1/me", authorization: `Bearer ${KEY}` }]);
  assert.deepEqual(await saved(f), { schema: 1, credentials: { [f.origin]: { key: KEY, username: "student_1" } } });
  assert.equal((await stat(f.credentialDir)).mode & 0o777, 0o700);
  assert.equal((await stat(f.file)).mode & 0o777, 0o600);
  assert.deepEqual(await readdir(f.credentialDir), ["credentials.json"]);
});

test("successful replacement fixes file permissions and preserves other origins", async (t) => {
  const a = await fixture(t);
  const b = await fixture(t);
  await Promise.all([
    loginStudent(KEY, a.options),
    loginStudent(OTHER_KEY, { ...b.options, credentialDir: a.credentialDir }),
  ]);
  await chmod(a.file, 0o644);
  await chmod(a.credentialDir, 0o755);
  await loginStudent(OTHER_KEY, a.options);
  const data = await saved(a);
  assert.equal(data.credentials[a.origin].key, OTHER_KEY);
  assert.equal(data.credentials[b.origin].key, OTHER_KEY);
  assert.equal((await stat(a.file)).mode & 0o777, 0o600);
  assert.equal((await stat(a.credentialDir)).mode & 0o777, 0o700);
});

test("401, server failures and malformed success replies preserve saved bytes and hide secrets", async (t) => {
  const f = await fixture(t);
  await loginStudent(KEY, f.options);
  const before = await readFile(f.file);
  const cases = [
    [401, "text/plain", OTHER_KEY],
    [500, "text/plain", OTHER_KEY],
    [204, "text/plain", ""],
    [200, "text/html", OTHER_KEY],
    [200, "application/json", OTHER_KEY],
    [200, "application/json", JSON.stringify({ key: OTHER_KEY })],
    [200, "application/json", JSON.stringify({ username: OTHER_KEY })],
    [200, "application/json", JSON.stringify({ username: 123 })],
  ];
  for (const [status, type, body] of cases) {
    f.setReply((_request, response) => { response.writeHead(status, { "Content-Type": type }); response.end(body); });
    const result = await loginStudent(OTHER_KEY, f.options);
    assert.equal(result.type, "error");
    assertSecretFree(result);
    assert.deepEqual(await readFile(f.file), before);
  }
});

test("redirect is refused and does not forward a key to another server", async (t) => {
  const f = await fixture(t);
  const target = await fixture(t);
  await loginStudent(KEY, f.options);
  const before = await readFile(f.file);
  f.setReply((_request, response) => { response.writeHead(307, { Location: `${target.origin}/api/v1/me` }); response.end(); });
  const result = await loginStudent(OTHER_KEY, f.options);
  assert.equal(result.type, "error");
  assertSecretFree(result);
  assert.equal(target.requests.length, 0);
  assert.deepEqual(await readFile(f.file), before);
});

test("timeout and unreachable server preserve saved credentials", async (t) => {
  const f = await fixture(t);
  await loginStudent(KEY, f.options);
  const before = await readFile(f.file);
  f.setReply(() => {});
  const timeout = await loginStudent(OTHER_KEY, { ...f.options, timeoutMs: 80 });
  assert.equal(timeout.type, "error");
  assertSecretFree(timeout);
  assert.deepEqual(await readFile(f.file), before);
  f.server.closeAllConnections();
  await new Promise((resolve) => f.server.close(resolve));
  const offline = await loginStudent(OTHER_KEY, f.options);
  assert.equal(offline.type, "error");
  assertSecretFree(offline);
  assert.deepEqual(await readFile(f.file), before);
});

test("corrupt credential file is not overwritten after a valid server reply", async (t) => {
  const f = await fixture(t);
  await mkdir(f.credentialDir, { mode: 0o700 });
  await writeFile(f.file, "broken-json", { mode: 0o600 });
  const result = await loginStudent(KEY, f.options);
  assert.equal(result.type, "error");
  assertSecretFree(result);
  assert.equal(await readFile(f.file, "utf8"), "broken-json");
  assert.deepEqual(await readdir(f.credentialDir), ["credentials.json"]);
});

test("credential file and directory symlinks are refused without altering their targets", async (t) => {
  const f = await fixture(t);
  await mkdir(f.credentialDir, { mode: 0o700 });
  const target = join(f.directory, "target");
  await writeFile(target, "untouched");
  await symlink(target, f.file);
  assert.equal((await loginStudent(KEY, f.options)).type, "error");
  assert.equal(await readFile(target, "utf8"), "untouched");
  const directoryLink = join(f.directory, "linked-directory");
  await symlink(f.credentialDir, directoryLink);
  assert.equal((await loginStudent(KEY, { ...f.options, credentialDir: directoryLink })).type, "error");
});

test("real Pi login command validates and saves without model calls or session secrets", async (t) => {
  const f = await fixture(t);
  const cwd = join(f.directory, "attempt");
  await mkdir(cwd);
  const client = startPi({
    cwd, sessionDir: join(f.directory, "sessions"),
    env: { HOME: f.directory, PI_CODING_AGENT_DIR: join(f.directory, "pi-config"), AGENT_GOLF_API_BASE_URL: f.origin },
  });
  const { request, seen } = client;
  try {
    const before = (await request("get_entries")).entries;
    assert.equal((await request("prompt", { message: `/golf-login ${KEY}` })).disposition, "handled");
    const credentialFile = join(f.directory, ".config", "agent-golf", "credentials.json");
    assert.equal(JSON.parse(await readFile(credentialFile, "utf8")).credentials[f.origin].key, KEY);
    const savedBytes = await readFile(credentialFile);
    f.setReply((_request, response) => { response.writeHead(401); response.end(OTHER_KEY); });
    assert.equal((await request("prompt", { message: `/golf-login ${OTHER_KEY}` })).disposition, "handled");
    assert.deepEqual(await readFile(credentialFile), savedBytes);
    assert.deepEqual((await request("get_entries")).entries, before);
    assert.deepEqual((await request("get_messages")).messages, []);
    assert.equal((await request("get_session_stats")).tokens.total, 0);
    assert.equal(seen.some((record) => record.type === "agent_start" || record.type === "message_start"), false);
    assert.equal(seen.some((record) => record.method === "notify" && record.message === `Logged in as student_1 on ${f.origin}.`), true);
    assert.equal(JSON.stringify(seen).includes(KEY), false);
    assert.equal(JSON.stringify(seen).includes(OTHER_KEY), false);
  } finally {
    await client.close();
  }
});
