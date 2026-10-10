import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";
import { DEFAULT_API_ORIGIN, resolveApiOrigin } from "../config.ts";
import { loginStudent } from "../login.ts";
import { submitSession } from "../submit.ts";

const KEY = "00000000-0000-4000-8000-000000000004";

function context(file) {
  return {
    hasUI: true, isIdle: () => true,
    sessionManager: { getSessionId: () => "s", getSessionFile: () => file, getLeafId: () => "leaf", getEntries: () => [] },
    ui: { confirm: async () => true },
  };
}

async function withMockFetch(fn) {
  const directory = await mkdtemp(join(tmpdir(), "golf-origin-test-"));
  const originalFetch = globalThis.fetch;
  const originalOrigin = process.env.AGENT_GOLF_API_BASE_URL;
  delete process.env.AGENT_GOLF_API_BASE_URL;
  try {
    await fn(directory);
  } finally {
    globalThis.fetch = originalFetch;
    if (originalOrigin === undefined) delete process.env.AGENT_GOLF_API_BASE_URL;
    else process.env.AGENT_GOLF_API_BASE_URL = originalOrigin;
    await rm(directory, { recursive: true, force: true });
  }
}

function reply(url) {
  if (url.endsWith("/me")) return Response.json({ username: "student_1" });
  return Response.json({
    status: "ranked", reasons: [],
    metrics: { total_tokens: 42, prompts: 2, chars_typed: 17, tool_calls: 3, models: ["provider/model"], thinking_levels: ["low"], solved: true },
    url: `${DEFAULT_API_ORIGIN}/submissions/1`,
  });
}

test("confirmed production origin is the default; explicit override wins over environment", () => {
  assert.equal(DEFAULT_API_ORIGIN, "https://agent-golf.justuju.in");
  assert.equal(resolveApiOrigin(undefined, {}), DEFAULT_API_ORIGIN);
  assert.equal(resolveApiOrigin(undefined, { AGENT_GOLF_API_BASE_URL: "http://localhost:8000" }), "http://localhost:8000");
  assert.equal(resolveApiOrigin("https://EXAMPLE.com:443/", { AGENT_GOLF_API_BASE_URL: "http://localhost:8000" }), "https://example.com");
  assert.throws(() => resolveApiOrigin("", {}));
  assert.throws(() => resolveApiOrigin(undefined, { AGENT_GOLF_API_BASE_URL: "" }));
  assert.throws(() => resolveApiOrigin(undefined, { AGENT_GOLF_API_BASE_URL: "http://example.com" }));
});

test("login and submit share the default without contacting any real server", async () => {
  await withMockFetch(async (directory) => {
    const calls = [];
    globalThis.fetch = async (url, init) => { calls.push({ url, init }); return reply(url); };
    const credentialDir = join(directory, "credentials");
    assert.equal((await loginStudent(KEY, { credentialDir })).type, "info");
    const sessionFile = join(directory, "session.jsonl");
    await writeFile(sessionFile, '{"type":"session","id":"s"}\n');
    assert.equal((await submitSession("help_me_unpack", context(sessionFile), { credentialDir })).type, "info");
    assert.deepEqual(calls.map((call) => call.url), [`${DEFAULT_API_ORIGIN}/api/v1/me`, `${DEFAULT_API_ORIGIN}/api/v1/submissions`]);
    assert.ok(calls.every((call) => call.init.headers.Authorization === `Bearer ${KEY}`));
    const saved = JSON.parse(await readFile(join(credentialDir, "credentials.json"), "utf8"));
    assert.equal(saved.credentials[DEFAULT_API_ORIGIN].key, KEY);
  });
});

test("environment override still applies to both commands and credential origin", async () => {
  await withMockFetch(async (directory) => {
    const origin = "http://localhost:8000";
    process.env.AGENT_GOLF_API_BASE_URL = origin;
    const calls = [];
    globalThis.fetch = async (url) => { calls.push(url); return reply(url); };
    const credentialDir = join(directory, "credentials");
    assert.equal((await loginStudent(KEY, { credentialDir })).type, "info");
    const sessionFile = join(directory, "session.jsonl");
    await writeFile(sessionFile, '{"type":"session","id":"s"}\n');
    assert.equal((await submitSession("help_me_unpack", context(sessionFile), { credentialDir })).type, "info");
    assert.deepEqual(calls, [`${origin}/api/v1/me`, `${origin}/api/v1/submissions`]);
    const saved = JSON.parse(await readFile(join(credentialDir, "credentials.json"), "utf8"));
    assert.equal(saved.credentials[origin].key, KEY);
    assert.equal(saved.credentials[DEFAULT_API_ORIGIN], undefined);
  });
});

test("invalid override fails closed without sending a key to the default server", async () => {
  await withMockFetch(async (directory) => {
    process.env.AGENT_GOLF_API_BASE_URL = "";
    let calls = 0;
    globalThis.fetch = async () => { calls++; throw new Error("must not fetch"); };
    const options = { credentialDir: join(directory, "credentials") };
    assert.equal((await loginStudent(KEY, options)).type, "error");
    assert.equal((await submitSession("help_me_unpack", context(), options)).type, "error");
    assert.equal(calls, 0);
  });
});

test("default origin does not reuse or migrate credentials saved for another server", async () => {
  await withMockFetch(async (directory) => {
    const credentialDir = join(directory, "credentials");
    globalThis.fetch = async (url) => reply(url);
    assert.equal((await loginStudent(KEY, { baseUrl: "https://old.example", credentialDir })).type, "info");
    const path = join(credentialDir, "credentials.json");
    const before = await readFile(path);
    let calls = 0;
    globalThis.fetch = async () => { calls++; throw new Error("must not fetch"); };
    const result = await submitSession("help_me_unpack", context(), { credentialDir });
    assert.match(result.message, /No key saved for this server/);
    assert.equal(calls, 0);
    assert.equal(result.message.includes(KEY), false);
    assert.deepEqual(await readFile(path), before);
  });
});
