import assert from "node:assert/strict";
import { createServer } from "node:http";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";
import { browseProblems, MAX_PROBLEM_BODY_BYTES } from "../problems.ts";
import { DEFAULT_API_ORIGIN } from "../config.ts";
import { startPi } from "./rpc-helper.mjs";

const DATA = {
  rules_version: "mvp-1", rules: ["Use a fresh session.", "Print Hackattic input and solve reply."],
  problems: [{ slug: "help_me_unpack", title: "Help me unpack", challenge_url: "https://hackattic.com/challenges/help_me_unpack", instructions: ["Print the input and reply."], model: "any", thinking_level: "any" }],
};
const KEY = "private-browser-test-key";

async function fixture(t) {
  const directory = await mkdtemp(join(tmpdir(), "golf-problems-"));
  const requests = [];
  let reply = (response) => { response.writeHead(200, { "Content-Type": "application/json" }); response.end(JSON.stringify(DATA)); };
  const server = createServer(async (request, response) => {
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    requests.push({ url: request.url, method: request.method, headers: request.headers, body: Buffer.concat(chunks) });
    reply(response);
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const editors = [];
  const selections = [];
  let select = async () => undefined;
  const ctx = {
    hasUI: true, mode: "rpc",
    get sessionManager() { throw new Error("browser must not access sessions"); },
    ui: {
      editor: async (title, prefill) => { editors.push({ title, prefill }); return "DISCARDED_EDIT"; },
      select: async (title, options) => { selections.push({ title, options }); return select(options); },
    },
  };
  t.after(async () => {
    server.closeAllConnections();
    await new Promise((resolve) => server.close(resolve));
    await rm(directory, { recursive: true, force: true });
  });
  return { directory, server, origin, requests, ctx, editors, selections, options: { baseUrl: origin },
    setSelect: (fn) => { select = fn; }, setReply: (fn) => { reply = fn; },
    respond: (data, status = 200, type = "application/json") => { reply = (response) => { response.writeHead(status, { "Content-Type": type }); response.end(typeof data === "string" ? data : JSON.stringify(data)); }; },
  };
}

function publicOnly(f) {
  assert.equal(f.requests.length, 1);
  const request = f.requests[0];
  assert.equal(request.url, "/api/v1/problems");
  assert.equal(request.method, "GET");
  assert.equal(request.headers.authorization, undefined);
  assert.equal(request.headers.cookie, undefined);
  assert.equal(request.body.length, 0);
}

test("public browser shows rules, details and any setup; edits are discarded", async (t) => {
  const f = await fixture(t);
  let count = 0;
  f.setSelect(async (options) => count++ === 0 ? options[0] : undefined);
  const result = await browseProblems("", f.ctx, f.options);
  assert.equal(result.type, "info");
  assert.match(f.editors[0].prefill, /Rules version: mvp-1/);
  assert.ok(f.editors[0].prefill.includes(DATA.rules[0]));
  assert.match(f.editors[1].prefill, /any model, one per session/);
  assert.match(f.editors[1].prefill, /any thinking level/);
  assert.ok(f.editors[1].prefill.includes(DATA.problems[0].challenge_url));
  assert.ok(f.editors[1].prefill.includes(DATA.problems[0].instructions[0]));
  assert.ok(f.editors.every((view) => !view.prefill.includes("DISCARDED_EDIT")));
  assert.ok(f.editors.every((view) => view.prefill.includes("Upload checks remain authoritative")));
  assert.match(f.selections[0].title, /choose to view details/);
  assert.ok(!/Enter|Esc/.test(f.selections[0].title), "native selector owns actual keybinding hints");
  publicOnly(f);
});

test("cancelling rules closes browsing without showing the problem selector", async (t) => {
  const f = await fixture(t);
  f.ctx.ui.editor = async () => undefined;
  assert.match((await browseProblems("", f.ctx, f.options)).message, /Problem browsing closed/);
  assert.equal(f.selections.length, 0);
  publicOnly(f);
});

test("RPC details cancellation returns to list rather than closing or uploading", async (t) => {
  const f = await fixture(t);
  let selections = 0;
  f.setSelect(async (options) => selections++ === 0 ? options[0] : undefined);
  f.ctx.ui.editor = async (title) => title.startsWith("Problem details") ? undefined : "continue";
  await browseProblems("", f.ctx, f.options);
  assert.equal(f.selections.length, 2);
  publicOnly(f);
});

test("default origin uses a credential-free request without real production networking", async (t) => {
  const f = await fixture(t);
  const originalFetch = globalThis.fetch;
  const originalOrigin = process.env.AGENT_GOLF_API_BASE_URL;
  const calls = [];
  delete process.env.AGENT_GOLF_API_BASE_URL;
  globalThis.fetch = async (url, init) => { calls.push({ url, init }); return Response.json(DATA); };
  try {
    assert.equal((await browseProblems("", f.ctx)).type, "info");
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, `${DEFAULT_API_ORIGIN}/api/v1/problems`);
    assert.deepEqual(calls[0].init.headers, { Accept: "application/json" });
    assert.equal(calls[0].init.credentials, "omit");
    assert.equal(calls[0].init.body, undefined);
    assert.equal(calls[0].init.redirect, "error");
  } finally {
    globalThis.fetch = originalFetch;
    if (originalOrigin === undefined) delete process.env.AGENT_GOLF_API_BASE_URL;
    else process.env.AGENT_GOLF_API_BASE_URL = originalOrigin;
  }
});

test("fixed per-problem setup is displayed literally without changing it", async (t) => {
  const f = await fixture(t);
  f.respond({ ...DATA, problems: [{ ...DATA.problems[0], model: "provider/model", thinking_level: "low" }] });
  let count = 0;
  f.setSelect(async (options) => count++ === 0 ? options[0] : undefined);
  await browseProblems("", f.ctx, f.options);
  assert.match(f.editors[1].prefill, /Model: provider\/model/);
  assert.match(f.editors[1].prefill, /Thinking level: low/);
});

test("empty catalogue still shows rules and does not open a selector", async (t) => {
  const f = await fixture(t);
  f.respond({ ...DATA, problems: [] });
  assert.equal((await browseProblems("", f.ctx, f.options)).type, "info");
  assert.equal(f.editors.length, 1);
  assert.match(f.editors[0].prefill, /No problems are currently listed/);
  assert.equal(f.selections.length, 0);
  publicOnly(f);
});

test("cancelling the selector or an unknown selection never binds an attempt", async (t) => {
  const f = await fixture(t);
  for (const selection of [undefined, "untrusted selection"]) {
    f.setSelect(async () => selection);
    assert.match((await browseProblems("", f.ctx, f.options)).message, /No attempt or setup was changed/);
  }
  assert.equal(f.editors.length, 2);
});

test("argument, missing UI and invalid origin checks make no request", async (t) => {
  const f = await fixture(t);
  assert.match((await browseProblems("slug", f.ctx, f.options)).message, /Usage/);
  assert.match((await browseProblems("", { hasUI: false, ui: f.ctx.ui }, f.options)).message, /UI support/);
  assert.equal((await browseProblems("", f.ctx, { baseUrl: "" })).type, "error");
  assert.equal(f.requests.length, 0);
});

test("malformed shapes, fields, duplicate slugs and non-exact challenge URLs fail closed", async (t) => {
  const f = await fixture(t);
  const p = DATA.problems[0];
  const variants = [null, {}, { ...DATA, rules_version: "" }, { ...DATA, rules: "rules" }, { ...DATA, problems: {} },
    ...["slug", "title", "challenge_url", "instructions", "model", "thinking_level"].map((field) => ({ ...DATA, problems: [{ ...p, [field]: undefined }] })),
    ...["https://evil.example", p.challenge_url + "/", p.challenge_url + "?access_token=x", p.challenge_url.replace("help_me_unpack", "other"), p.challenge_url.replace("https:", "http:")].map((url) => ({ ...DATA, problems: [{ ...p, challenge_url: url }] })),
    { ...DATA, problems: [p, p] }, { ...DATA, problems: [{ ...p, model: "not-provider/model name" }] },
    { ...DATA, problems: [{ ...p, instructions: [1] }] }, { ...DATA, problems: [{ ...p, thinking_level: "" }] },
  ];
  for (const body of variants) {
    f.respond(body);
    assert.equal((await browseProblems("", f.ctx, f.options)).type, "error");
  }
  assert.equal(f.editors.length, 0);
});

test("all response strings are checked for terminal controls, bidi tricks and character limits", async (t) => {
  const f = await fixture(t);
  for (const text of ["\x1b[31m", "\x9b31m", "a\u202eb", "a\u2066b", "\r", "\ud800", "a".repeat(1001), "🙂".repeat(1001)]) {
    for (const body of [{ ...DATA, rules: [text] }, { ...DATA, ignored: text }]) {
      f.respond(body);
      assert.equal((await browseProblems("", f.ctx, f.options)).type, "error");
    }
  }
  assert.equal(f.editors.length, 0);
  f.respond({ ...DATA, rules: ["🙂".repeat(1000), "Plain **text**, not rendered Markdown.\nNext line."] });
  assert.equal((await browseProblems("", f.ctx, f.options)).type, "info");
  assert.ok(f.editors[0].prefill.includes("Plain **text**, not rendered Markdown."));
});

test("body cap is byte-based and enforced on chunked replies without Content-Length", async (t) => {
  const f = await fixture(t);
  const json = JSON.stringify(DATA);
  f.respond(json + " ".repeat(MAX_PROBLEM_BODY_BYTES - Buffer.byteLength(json)));
  assert.equal((await browseProblems("", f.ctx, f.options)).type, "info");
  f.setReply((response) => {
    response.writeHead(200, { "Content-Type": "application/json" });
    response.write(json + " ".repeat(40_000));
    response.end(" ".repeat(30_000));
  });
  assert.equal((await browseProblems("", f.ctx, f.options)).type, "error");
  assert.equal(f.editors.length, 1);
  f.respond(json + " ".repeat(MAX_PROBLEM_BODY_BYTES));
  assert.equal((await browseProblems("", f.ctx, f.options)).type, "error");
});

test("invalid UTF-8, JSON, content types and non-200 bodies are not displayed", async (t) => {
  const f = await fixture(t);
  for (const [body, status, type] of [[KEY, 500, "text/plain"], [KEY, 401, "application/json"], [DATA, 200, "text/html"], ["{", 200, "application/json"]]) {
    f.respond(body, status, type);
    const result = await browseProblems("", f.ctx, f.options);
    assert.match(result.message, /Problem list unavailable/);
    assert.equal(result.message.includes(KEY), false);
  }
  f.setReply((response) => { response.writeHead(200, { "Content-Type": "application/json" }); response.end(Buffer.from([0xff])); });
  assert.equal((await browseProblems("", f.ctx, f.options)).type, "error");
  assert.equal(f.editors.length, 0);
});

test("redirects are refused without contacting their destination", async (t) => {
  const f = await fixture(t);
  const target = await fixture(t);
  f.setReply((response) => { response.writeHead(302, { Location: `${target.origin}/api/v1/problems` }); response.end(); });
  assert.equal((await browseProblems("", f.ctx, f.options)).type, "error");
  assert.equal(target.requests.length, 0);
});

test("timeouts/offline server fail without retries and release the browser guard", async (t) => {
  const f = await fixture(t);
  f.setReply(() => {});
  assert.equal((await browseProblems("", f.ctx, { ...f.options, timeoutMs: 80 })).type, "error");
  assert.equal(f.requests.length, 1);
  f.server.closeAllConnections();
  await new Promise((resolve) => f.server.close(resolve));
  assert.equal((await browseProblems("", f.ctx, f.options)).type, "error");
  assert.equal(f.requests.length, 1);
});

test("timeout covers a stalled response body after headers arrive", async (t) => {
  const f = await fixture(t);
  f.setReply((response) => {
    response.writeHead(200, { "Content-Type": "application/json" });
    response.write("{");
  });
  assert.equal((await browseProblems("", f.ctx, { ...f.options, timeoutMs: 80 })).type, "error");
  assert.equal(f.requests.length, 1);
  assert.equal(f.editors.length, 0);
});

test("UI failures hide exception text and release the transient browser guard", async (t) => {
  const f = await fixture(t);
  const editor = f.ctx.ui.editor;
  f.ctx.ui.editor = async () => { throw new Error(KEY); };
  const result = await browseProblems("", f.ctx, f.options);
  assert.equal(result.type, "error");
  assert.equal(result.message.includes(KEY), false);
  f.ctx.ui.editor = editor;
  assert.equal((await browseProblems("", f.ctx, f.options)).type, "info");
  assert.equal(f.requests.length, 2);
});

test("only one browser opens at a time; closing releases the guard", async (t) => {
  const f = await fixture(t);
  let entered;
  const ready = new Promise((resolve) => { entered = resolve; });
  let release;
  f.ctx.ui.editor = () => { entered(); return new Promise((resolve) => { release = resolve; }); };
  const first = browseProblems("", f.ctx, f.options);
  await ready;
  assert.match((await browseProblems("", f.ctx, f.options)).message, /Another problem browser/);
  release(undefined);
  await first;
  assert.equal(f.requests.length, 1);
});

for (const kind of ["populated", "empty", "unavailable"]) {
  test(`real Pi browser ${kind}: UI only, no credentials or session/model changes`, async (t) => {
    const f = await fixture(t);
    if (kind === "empty") f.respond({ ...DATA, problems: [] });
    if (kind === "unavailable") f.respond(KEY, 503, "text/plain");
    const timestamp = new Date().toISOString();
    const sessionFile = join(f.directory, "session.jsonl");
    await writeFile(sessionFile, [
      { type: "session", version: 3, id: "attempt", cwd: f.directory, timestamp },
      { type: "custom", customType: "agent-golf-folder-check", id: "folder", parentId: null, timestamp, data: { schema: 1, state: "empty", policy: "zero-directory-entries", checked_at: timestamp } },
      { type: "message", id: "user", parentId: "folder", timestamp, message: { role: "user", content: "Synthetic attempt", timestamp: Date.now() } },
    ].map((entry) => JSON.stringify(entry)).join("\n") + "\n");
    const credentialDir = join(f.directory, ".config", "agent-golf");
    await mkdir(credentialDir, { recursive: true, mode: 0o700 });
    const credentialFile = join(credentialDir, "credentials.json");
    await writeFile(credentialFile, JSON.stringify({ schema: 1, credentials: { [f.origin]: { key: KEY, username: "student_1" } } }), { mode: 0o600 });
    let selections = 0;
    let client;
    client = startPi({ cwd: f.directory, sessionFile, sessionDir: join(f.directory, "sessions"),
      env: { HOME: f.directory, PI_CODING_AGENT_DIR: join(f.directory, "pi-config"), AGENT_GOLF_API_BASE_URL: f.origin },
      onRecord: (record) => {
        if (record.type !== "extension_ui_request") return;
        if (record.method === "editor") client.respondUI(record.id, "DISCARDED_EDIT");
        if (record.method === "select") client.respondUI(record.id, selections++ === 0 ? record.options[0] : undefined);
      },
    });
    try {
      const entries = (await client.request("get_entries")).entries;
      const messages = (await client.request("get_messages")).messages;
      const state = await client.request("get_state");
      const bytes = await readFile(sessionFile);
      const credentials = await readFile(credentialFile);
      assert.equal((await client.request("prompt", { message: "/golf-problems" })).disposition, "handled");
      publicOnly(f);
      const views = client.seen.filter((record) => record.method === "editor");
      assert.equal(views.length, kind === "populated" ? 2 : kind === "empty" ? 1 : 0);
      if (kind !== "unavailable") assert.ok(views[0].prefill.includes("Rules version: mvp-1"));
      if (kind === "populated") assert.match(views[1].prefill, /any model, one per session/);
      assert.deepEqual((await client.request("get_entries")).entries, entries);
      assert.deepEqual((await client.request("get_messages")).messages, messages);
      assert.deepEqual(await client.request("get_state"), state);
      assert.deepEqual(await readFile(sessionFile), bytes);
      assert.deepEqual(await readFile(credentialFile), credentials);
      assert.equal((await client.request("get_session_stats")).tokens.total, 0);
      assert.equal(client.seen.some((record) => record.type === "agent_start" || record.type === "message_start" || record.method === "set_editor_text"), false);
      assert.equal(JSON.stringify(client.seen).includes(KEY), false);
      assert.ok(client.seen.some((record) => record.method === "notify" && record.message.includes(kind === "unavailable" ? "Problem list unavailable" : "Problem browsing closed")));
    } finally { await client.close(); }
  });
}
