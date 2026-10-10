import assert from "node:assert/strict";
import { createServer } from "node:http";
import { mkdtemp, readFile, rm, writeFile, chmod } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";
import { loginStudent } from "../login.ts";
import { submitSession } from "../submit.ts";
import { startPi } from "./rpc-helper.mjs";
import { hasPendingUserBash } from "../user-bash.ts";

const KEY = "00000000-0000-4000-8000-000000000003";
const BYTES = Buffer.from('{"type":"session","id":"attempt"}\r\n{"type":"message","text":"abandoned branch — नमस्ते"}\r\n');
const METRICS = { total_tokens: 42, prompts: 2, chars_typed: 17, tool_calls: 3, models: ["provider/model"], thinking_levels: ["low"], solved: true };

async function fixture(t) {
  const directory = await mkdtemp(join(tmpdir(), "golf-submit-test-"));
  const credentialDir = join(directory, "credentials");
  const sessionFile = join(directory, "session.jsonl");
  await writeFile(sessionFile, BYTES);
  const requests = [];
  let reply;
  const server = createServer(async (request, response) => {
    if (request.url === "/api/v1/me") {
      response.writeHead(200, { "Content-Type": "application/json" });
      response.end(JSON.stringify({ username: "student_1" }));
      return;
    }
    try {
      const chunks = [];
      for await (const chunk of request) chunks.push(chunk);
      const form = await new Response(Buffer.concat(chunks), { headers: { "Content-Type": request.headers["content-type"] } }).formData();
      const file = form.get("session");
      requests.push({
        path: request.url, method: request.method, authorization: request.headers.authorization,
        fields: [...form.keys()], problem: form.get("problem"), folder: form.get("folder_was_empty"),
        filename: file.name, bytes: Buffer.from(await file.arrayBuffer()),
      });
      reply(response);
    } catch {
      response.writeHead(500);
      response.end();
    }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const ranked = { status: "ranked", reasons: [], metrics: METRICS, url: `${origin}/submissions/1` };
  reply = (response) => { response.writeHead(200, { "Content-Type": "application/json" }); response.end(JSON.stringify(ranked)); };
  t.after(async () => {
    server.closeAllConnections();
    await new Promise((resolve) => server.close(resolve));
    await rm(directory, { recursive: true, force: true });
  });
  const options = { baseUrl: origin, credentialDir };
  assert.equal((await loginStudent(KEY, options)).type, "info");
  const state = { id: "attempt", file: sessionFile, leaf: "leaf", idle: true, hasUI: true };
  const confirmations = [];
  let confirm = async () => true;
  const ctx = {
    get hasUI() { return state.hasUI; },
    isIdle: () => state.idle,
    sessionManager: { getSessionId: () => state.id, getSessionFile: () => state.file, getLeafId: () => state.leaf, getEntries: () => [] },
    ui: { confirm: async (title, message) => { confirmations.push({ title, message }); return confirm(); } },
  };
  return {
    directory, credentialDir, sessionFile, origin, requests, options, state, ctx, confirmations, ranked, server,
    setConfirm: (handler) => { confirm = handler; },
    setReply: (handler) => { reply = handler; },
    respond: (status, body, type = "application/json") => {
      reply = (response) => { response.writeHead(status, { "Content-Type": type }); response.end(typeof body === "string" ? body : JSON.stringify(body)); };
    },
  };
}

function secretFree(result) { assert.equal(JSON.stringify(result).includes(KEY), false); }

for (const folder of [undefined, "true", "false"]) {
  test(`multipart upload preserves raw bytes and optional folder flag ${folder}`, async (t) => {
    const f = await fixture(t);
    const result = await submitSession("help_me_unpack", f.ctx, { ...f.options, folderWasEmpty: folder });
    assert.equal(result.type, "info");
    assert.match(result.message, /Submission ranked/);
    assert.match(result.message, /Tokens: 42; prompts: 2/);
    assert.match(result.message, /provider\/model/);
    assert.match(result.message, /submissions\/1/);
    secretFree(result);
    assert.equal(f.requests.length, 1);
    const request = f.requests[0];
    assert.equal(request.path, "/api/v1/submissions");
    assert.equal(request.method, "POST");
    assert.equal(request.authorization, `Bearer ${KEY}`);
    assert.equal(request.problem, "help_me_unpack");
    assert.equal(request.folder, folder ?? null);
    assert.deepEqual(request.fields, folder === undefined ? ["problem", "session"] : ["problem", "session", "folder_was_empty"]);
    assert.equal(request.filename, "session.jsonl");
    assert.deepEqual(request.bytes, BYTES);
    assert.deepEqual(await readFile(f.sessionFile), BYTES);
    assert.match(f.confirmations[0].message, /Hackattic tokens, prompts, and local paths/);
    assert.match(f.confirmations[0].message, /abandoned branches/);
    assert.ok(f.confirmations[0].message.includes(f.origin));
    assert.ok(f.confirmations[0].message.includes(`${BYTES.length} bytes`));
  });
}

test("cancelled confirmation makes no upload", async (t) => {
  const f = await fixture(t);
  f.setConfirm(async () => false);
  assert.match((await submitSession("help_me_unpack", f.ctx, f.options)).message, /cancelled/);
  assert.equal(f.requests.length, 0);
  assert.deepEqual(await readFile(f.sessionFile), BYTES);
});

test("invalid problem, missing origin, no UI or busy Pi cannot upload", async (t) => {
  const f = await fixture(t);
  for (const args of ["", "two problems", "../../secret", "Help-me-unpack"]) {
    assert.match((await submitSession(args, f.ctx, f.options)).message, /Usage/);
  }
  assert.equal((await submitSession("help_me_unpack", f.ctx, { ...f.options, baseUrl: "" })).type, "error");
  f.state.hasUI = false;
  assert.match((await submitSession("help_me_unpack", f.ctx, f.options)).message, /confirmation dialog/);
  f.state.hasUI = true;
  f.state.idle = false;
  assert.match((await submitSession("help_me_unpack", f.ctx, f.options)).message, /busy/);
  assert.equal(f.requests.length, 0);
  assert.equal(f.confirmations.length, 0);
});

test("credentials are required for this exact origin and must be private/readable", async (t) => {
  const f = await fixture(t);
  assert.match((await submitSession("help_me_unpack", f.ctx, { ...f.options, baseUrl: "http://localhost:8000" })).message, /No key saved/);
  const path = join(f.credentialDir, "credentials.json");
  await chmod(path, 0o644);
  assert.match((await submitSession("help_me_unpack", f.ctx, f.options)).message, /read securely/);
  await chmod(path, 0o600);
  await writeFile(path, "corrupt");
  assert.match((await submitSession("help_me_unpack", f.ctx, f.options)).message, /read securely/);
  await rm(path);
  assert.match((await submitSession("help_me_unpack", f.ctx, f.options)).message, /No key saved/);
  assert.equal(f.requests.length, 0);
  assert.equal(f.confirmations.length, 0);
});

test("absent, unreadable or empty session files cannot upload", async (t) => {
  const f = await fixture(t);
  f.state.file = undefined;
  assert.match((await submitSession("help_me_unpack", f.ctx, f.options)).message, /No persisted/);
  f.state.file = f.directory;
  assert.match((await submitSession("help_me_unpack", f.ctx, f.options)).message, /unreadable/);
  f.state.file = f.sessionFile;
  await writeFile(f.sessionFile, "");
  assert.match((await submitSession("help_me_unpack", f.ctx, f.options)).message, /empty/);
  await rm(f.sessionFile);
  assert.match((await submitSession("help_me_unpack", f.ctx, f.options)).message, /unreadable/);
  assert.equal(f.requests.length, 0);
});

for (const change of ["session", "branch", "busy", "file"]) {
  test(`changing ${change} during confirmation prevents upload`, async (t) => {
    const f = await fixture(t);
    f.setConfirm(async () => {
      if (change === "session") f.state.id = "another-session";
      if (change === "branch") f.state.leaf = "another-leaf";
      if (change === "busy") f.state.idle = false;
      if (change === "file") await writeFile(f.sessionFile, "changed");
      return true;
    });
    assert.equal((await submitSession("help_me_unpack", f.ctx, f.options)).type, "error");
    assert.equal(f.requests.length, 0);
  });
}

test("second submission is refused while the first awaits confirmation", async (t) => {
  const f = await fixture(t);
  let release;
  let entered;
  const ready = new Promise((resolve) => { entered = resolve; });
  f.setConfirm(() => { entered(); return new Promise((resolve) => { release = resolve; }); });
  const first = submitSession("help_me_unpack", f.ctx, f.options);
  await ready;
  assert.match((await submitSession("help_me_unpack", f.ctx, f.options)).message, /already in progress/);
  release(false);
  await first;
  assert.equal(f.requests.length, 0);
});

test("unranked and ranked-with-warning replies display server status and metrics unchanged", async (t) => {
  const f = await fixture(t);
  for (const [status, reasons] of [["unranked", ["not_solved"]], ["ranked", ["custom_setup"]]]) {
    f.respond(200, { ...f.ranked, status, reasons, metrics: { ...METRICS, solved: false } });
    const result = await submitSession("help_me_unpack", f.ctx, f.options);
    assert.equal(result.type, "info");
    assert.ok(result.message.includes(`Submission ${status}`));
    assert.ok(result.message.includes(reasons[0]));
    assert.match(result.message, /solved: false/);
  }
});

for (const [status, reason] of [[401, "bad_key"], [400, "not_pi_log"], [400, "unknown_problem"], [413, "file_too_large"]]) {
  test(`HTTP ${status} rejected reply displays ${reason} without altering credentials`, async (t) => {
    const f = await fixture(t);
    const path = join(f.credentialDir, "credentials.json");
    const before = await readFile(path);
    f.respond(status, { status: "rejected", reasons: [reason], metrics: null, url: null });
    const result = await submitSession("help_me_unpack", f.ctx, f.options);
    assert.equal(result.type, "error");
    assert.ok(result.message.includes(reason));
    secretFree(result);
    assert.deepEqual(await readFile(path), before);
  });
}

test("malformed or secret-bearing replies are never displayed verbatim", async (t) => {
  const f = await fixture(t);
  const bodies = [
    KEY, {}, { ...f.ranked, status: "rejected" }, { ...f.ranked, reasons: [KEY] },
    { ...f.ranked, metrics: { ...METRICS, total_tokens: -1 } },
    { ...f.ranked, metrics: { ...METRICS, models: [KEY] } },
    { ...f.ranked, url: "javascript:alert(1)" },
    { ...f.ranked, url: `${f.origin}/submissions/${KEY}` },
  ];
  for (const body of bodies) {
    f.respond(200, body);
    const result = await submitSession("help_me_unpack", f.ctx, f.options);
    assert.equal(result.type, "error");
    secretFree(result);
  }
  f.respond(200, KEY, "text/html");
  secretFree(await submitSession("help_me_unpack", f.ctx, f.options));
});

test("server faults and redirects are not reported as bad files; no redirect forwarding", async (t) => {
  const f = await fixture(t);
  const target = await fixture(t);
  f.respond(500, KEY, "text/plain");
  const fault = await submitSession("help_me_unpack", f.ctx, f.options);
  assert.match(fault.message, /server error/);
  secretFree(fault);
  f.setReply((response) => { response.writeHead(307, { Location: `${target.origin}/api/v1/submissions` }); response.end(); });
  const redirected = await submitSession("help_me_unpack", f.ctx, f.options);
  assert.equal(redirected.type, "error");
  secretFree(redirected);
  assert.equal(target.requests.length, 0);
});

test("timeout and unreachable server warn about uncertain delivery and do not retry", async (t) => {
  const f = await fixture(t);
  f.setReply(() => {});
  const timedOut = await submitSession("help_me_unpack", f.ctx, { ...f.options, timeoutMs: 80 });
  assert.equal(timedOut.type, "error");
  assert.match(timedOut.message, /may have reached/);
  secretFree(timedOut);
  assert.equal(f.requests.length, 1);
  f.server.closeAllConnections();
  await new Promise((resolve) => f.server.close(resolve));
  assert.equal((await submitSession("help_me_unpack", f.ctx, f.options)).type, "error");
  assert.equal(f.requests.length, 1);
});

for (const confirmed of [false, true]) {
  test(`real Pi submission confirmation=${confirmed}: no model activity or session mutation`, async (t) => {
    const f = await fixture(t);
    await loginStudent(KEY, { ...f.options, credentialDir: join(f.directory, ".config", "agent-golf") });
    const timestamp = new Date().toISOString();
    const seed = [
      { type: "session", version: 3, id: "attempt", cwd: f.directory, timestamp },
      { type: "custom", customType: "agent-golf-folder-check", id: "folder", parentId: null, timestamp,
        data: { schema: 1, state: "empty", policy: "zero-directory-entries", checked_at: timestamp } },
      { type: "message", id: "user", parentId: "folder", timestamp,
        message: { role: "user", content: "Synthetic attempt for testing", timestamp: Date.now() } },
    ];
    await writeFile(f.sessionFile, seed.map((entry) => JSON.stringify(entry)).join("\r\n") + "\r\n");
    let client;
    client = startPi({
      cwd: f.directory, sessionFile: f.sessionFile, sessionDir: join(f.directory, "sessions"),
      env: { HOME: f.directory, PI_CODING_AGENT_DIR: join(f.directory, "pi-config"), AGENT_GOLF_API_BASE_URL: f.origin },
      onRecord: (record) => {
        if (record.type === "extension_ui_request" && record.method === "confirm") client.respondUI(record.id, confirmed);
      },
    });
    try {
      const before = (await client.request("get_entries")).entries;
      const bytes = await readFile(f.sessionFile);
      const messages = (await client.request("get_messages")).messages;
      assert.equal((await client.request("prompt", { message: "/golf-submit help_me_unpack" })).disposition, "handled");
      assert.equal(f.requests.length, confirmed ? 1 : 0);
      if (confirmed) {
        assert.deepEqual(f.requests[0].bytes, bytes);
        assert.equal(f.requests[0].folder, "true");
      }
      assert.deepEqual((await client.request("get_entries")).entries, before);
      assert.deepEqual((await client.request("get_messages")).messages, messages);
      assert.deepEqual(await readFile(f.sessionFile), bytes);
      assert.equal((await client.request("get_session_stats")).tokens.total, 0);
      assert.equal(client.seen.some((record) => record.type === "agent_start" || record.type === "message_start"), false);
      assert.equal(JSON.stringify(client.seen).includes(KEY), false);
      assert.equal(client.seen.some((record) => record.method === "notify" && record.message.includes(confirmed ? "Submission ranked" : "cancelled")), true);
    } finally {
      await client.close();
    }
  });
}

for (const timing of ["before submission", "during confirmation"]) {
  test(`real Pi: outstanding user Bash ${timing} blocks upload until result is recorded`, async (t) => {
    const f = await fixture(t);
    await loginStudent(KEY, { ...f.options, credentialDir: join(f.directory, ".config", "agent-golf") });
    const timestamp = new Date().toISOString();
    await writeFile(f.sessionFile, [
      { type: "session", version: 3, id: "attempt", cwd: f.directory, timestamp },
      { type: "message", id: "user", parentId: null, timestamp,
        message: { role: "user", content: "Synthetic attempt", timestamp: Date.now() } },
    ].map((entry) => JSON.stringify(entry)).join("\n") + "\n");
    const releasePath = join(f.directory, "release-bash");
    const command = `printf 'BASH_STARTED\\n'; while [ ! -f '${releasePath}' ]; do sleep 0.05; done; printf 'FINAL_SOLVE_REPLY: correct\\n'`;
    let started;
    const bashStarted = new Promise((resolve) => { started = resolve; });
    let shell;
    let confirmationId;
    let stage = "block";
    let client;
    client = startPi({
      cwd: f.directory, sessionFile: f.sessionFile, sessionDir: join(f.directory, "sessions"),
      env: { HOME: f.directory, PI_CODING_AGENT_DIR: join(f.directory, "pi-config"), AGENT_GOLF_API_BASE_URL: f.origin },
      onRecord: (record) => {
        if (record.type === "extension_ui_request" && record.method === "confirm") {
          if (stage === "block" && timing === "during confirmation") {
            confirmationId = record.id;
            shell = client.request("bash", { command });
            shell.catch(() => {});
          } else {
            client.respondUI(record.id, true);
          }
        }
        if (record.type === "bash_execution_update" && record.delta.includes("BASH_STARTED")) {
          started();
          if (confirmationId) client.respondUI(confirmationId, true);
        }
      },
    });
    try {
      await client.request("get_entries");
      if (timing === "before submission") {
        shell = client.request("bash", { command, excludeFromContext: true });
        shell.catch(() => {});
        await Promise.race([bashStarted, new Promise((_, reject) => {
          const timer = setTimeout(() => reject(new Error("Bash did not start")), 5_000);
          timer.unref();
        })]);
        const entries = (await client.request("get_entries")).entries;
        assert.equal(hasPendingUserBash(entries), true);
        assert.equal((await client.request("get_state")).isStreaming, false);
      }
      const notificationsBefore = client.seen.length;
      assert.equal((await client.request("prompt", { message: "/golf-submit help_me_unpack" })).disposition, "handled");
      assert.equal(f.requests.length, 0, "must not upload before Bash completion");
      const pendingEntries = (await client.request("get_entries")).entries;
      assert.equal(hasPendingUserBash(pendingEntries), true);
      assert.equal(pendingEntries.some((entry) => entry.type === "message" && entry.message.role === "bashExecution"), false);
      assert.equal(client.seen.slice(notificationsBefore).some((record) => record.method === "notify" && record.notifyType === "error"), true);
      if (timing === "before submission") {
        assert.equal(client.seen.slice(notificationsBefore).some((record) => record.method === "confirm"), false);
      }
      await writeFile(releasePath, "done");
      await shell;
      const completeEntries = (await client.request("get_entries")).entries;
      assert.equal(hasPendingUserBash(completeEntries), false);
      const bash = completeEntries.find((entry) => entry.type === "message" && entry.message.role === "bashExecution");
      assert.ok(bash.message.output.includes("FINAL_SOLVE_REPLY: correct"));
      stage = "retry";
      assert.equal((await client.request("prompt", { message: "/golf-submit help_me_unpack" })).disposition, "handled");
      assert.equal(f.requests.length, 1);
      const uploaded = f.requests[0].bytes.toString("utf8").trim().split("\n").map((line) => JSON.parse(line));
      const uploadedBash = uploaded.find((entry) => entry.type === "message" && entry.message.role === "bashExecution");
      assert.ok(uploadedBash.message.output.includes("FINAL_SOLVE_REPLY: correct"));
      assert.equal((await client.request("get_session_stats")).tokens.total, 0);
      assert.equal(client.seen.some((record) => record.type === "agent_start"), false);
    } finally {
      await writeFile(releasePath, "done");
      await client.close();
      await shell?.catch(() => {});
    }
  });
}
