import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawn } from "node:child_process";
import { test } from "node:test";

import plugin, {
  FOLDER_CHECK_CUSTOM_TYPE,
  getFolderWasEmptyUploadValue,
  recordFolderCheckForSession,
} from "../index.ts";

function makeSession(entries = [], header = { type: "session", id: "s", cwd: "/tmp", timestamp: new Date().toISOString() }) {
  const stored = [...entries];
  return {
    appended: [],
    pi: {
      appendEntry(customType, data) {
        const entry = {
          type: "custom",
          customType,
          data,
          id: `e${stored.length + 1}`,
          parentId: stored.at(-1)?.id ?? null,
          timestamp: new Date().toISOString(),
        };
        stored.push(entry);
        this.appended.push(entry);
      },
      appended: [],
    },
    ctx: {
      cwd: header.cwd,
      sessionManager: {
        getEntries: () => [...stored],
        getHeader: () => header,
      },
    },
    entries: stored,
  };
}

function existingObservation(state = "empty") {
  return {
    type: "custom",
    customType: FOLDER_CHECK_CUSTOM_TYPE,
    id: "obs",
    parentId: null,
    timestamp: new Date().toISOString(),
    data: {
      schema: 1,
      state,
      checked_at: new Date().toISOString(),
      policy: "zero-directory-entries",
    },
  };
}

async function withTempDir(fn) {
  const dir = await mkdtemp(join(tmpdir(), "agent-golf-folder-check-"));
  try {
    return await fn(dir);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

test("plugin registers login and submission commands", async () => {
  const commands = new Map();
  const events = new Map();
  plugin({
    on(name, handler) {
      events.set(name, handler);
    },
    registerCommand(name, definition) {
      commands.set(name, definition);
    },
    appendEntry() {},
  });

  assert.equal(typeof events.get("session_start"), "function");
  assert.equal(commands.has("golf-login"), true);
  assert.equal(commands.has("golf-submit"), true);

  const notifications = [];
  const ctx = {
    ui: { notify: (message, type) => notifications.push({ message, type }) },
    sessionManager: { getHeader: () => null, getEntries: () => [] },
  };
  await commands.get("golf-login").handler("", ctx);
  await commands.get("golf-submit").handler("", ctx);

  assert.deepEqual(notifications, [
    { message: "Usage: /golf-login <key>", type: "info" },
    { message: "Usage: /golf-submit <problem> (for example: help_me_unpack)", type: "info" },
  ]);
});

test("empty fresh directory records empty", async () => {
  await withTempDir(async (dir) => {
    const session = makeSession([], { type: "session", id: "s", cwd: dir, timestamp: new Date().toISOString() });
    await recordFolderCheckForSession(session.pi, { reason: "startup" }, session.ctx);

    assert.equal(session.pi.appended.length, 1);
    assert.equal(session.pi.appended[0].data.state, "empty");
    assert.equal(getFolderWasEmptyUploadValue(session.ctx.sessionManager.getHeader(), session.ctx.sessionManager.getEntries()), "true");
  });
});

test("hidden file makes a fresh directory nonempty", async () => {
  await withTempDir(async (dir) => {
    await writeFile(join(dir, ".hidden"), "x");
    const session = makeSession([], { type: "session", id: "s", cwd: dir, timestamp: new Date().toISOString() });
    await recordFolderCheckForSession(session.pi, { reason: "startup" }, session.ctx);

    assert.equal(session.pi.appended[0].data.state, "nonempty");
    assert.equal(getFolderWasEmptyUploadValue(session.ctx.sessionManager.getHeader(), session.ctx.sessionManager.getEntries()), "false");
  });
});

test("files created after startup do not change the initial observation", async () => {
  await withTempDir(async (dir) => {
    const session = makeSession([], { type: "session", id: "s", cwd: dir, timestamp: new Date().toISOString() });
    await recordFolderCheckForSession(session.pi, { reason: "startup" }, session.ctx);
    await writeFile(join(dir, "later.txt"), "x");
    await recordFolderCheckForSession(session.pi, { reason: "reload" }, session.ctx);

    assert.equal(session.pi.appended.length, 1);
    assert.equal(session.pi.appended[0].data.state, "empty");
  });
});

test("resume or reload preserves an existing observation", async () => {
  const observed = existingObservation("nonempty");
  const session = makeSession([observed]);

  await recordFolderCheckForSession(session.pi, { reason: "resume" }, session.ctx);
  await recordFolderCheckForSession(session.pi, { reason: "reload" }, session.ctx);

  assert.equal(session.pi.appended.length, 0);
  assert.equal(getFolderWasEmptyUploadValue(session.ctx.sessionManager.getHeader(), session.ctx.sessionManager.getEntries()), "false");
});

test("existing session without evidence records unknown", async () => {
  const prior = { type: "message", id: "m1", parentId: null, timestamp: new Date().toISOString(), message: { role: "user", content: "hi", timestamp: Date.now() } };
  const session = makeSession([prior]);

  await recordFolderCheckForSession(session.pi, { reason: "startup" }, session.ctx);

  assert.equal(session.pi.appended[0].data.state, "unknown");
  assert.equal(session.pi.appended[0].data.reason, "not-fresh:startup");
  assert.equal(getFolderWasEmptyUploadValue(session.ctx.sessionManager.getHeader(), session.ctx.sessionManager.getEntries()), undefined);
});

test("known initialization entries allow a fresh observation", async () => {
  await withTempDir(async (dir) => {
    const session = makeSession([
      { type: "model_change", provider: "test", modelId: "test" },
      { type: "thinking_level_change", thinkingLevel: "off" },
      { type: "session_info", name: "Fresh attempt" },
    ], { type: "session", id: "s", cwd: dir, timestamp: new Date().toISOString() });

    await recordFolderCheckForSession(session.pi, { reason: "startup" }, session.ctx);
    assert.equal(session.pi.appended[0].data.state, "empty");
  });
});

for (const prior of [
  { type: "message", message: { role: "bashExecution", command: "rm -f solution.py", output: "", exitCode: 0 } },
  { type: "message", message: { role: "toolResult", toolName: "bash", content: [] } },
  { type: "usage", usage: { totalTokens: 1 } },
  { type: "compaction", summary: "Earlier work" },
  { type: "custom", customType: "another-extension", data: {} },
]) {
  test(`prior ${prior.message?.role ?? prior.type} activity cannot certify an empty cwd`, async () => {
    await withTempDir(async (dir) => {
      const session = makeSession([prior], { type: "session", id: "old", cwd: dir, timestamp: "2026-10-01T00:00:00.000Z" });
      await recordFolderCheckForSession(session.pi, { reason: "startup" }, session.ctx);
      assert.equal(session.pi.appended[0].data.state, "unknown");
      assert.equal(session.pi.appended[0].data.reason, "not-fresh:startup");
      assert.equal(getFolderWasEmptyUploadValue(session.ctx.sessionManager.getHeader(), session.entries), undefined);
    });
  });
}

test("forked or inherited sessions cannot get fresh-attempt certification", async () => {
  await withTempDir(async (dir) => {
    const forkHeader = { type: "session", id: "fork", cwd: dir, timestamp: new Date().toISOString(), parentSession: "/old/session.jsonl" };
    const session = makeSession([], forkHeader);

    await recordFolderCheckForSession(session.pi, { reason: "fork" }, session.ctx);

    assert.equal(session.pi.appended[0].data.state, "unknown");
    assert.equal(session.pi.appended[0].data.reason, "inherited-session");
    assert.equal(getFolderWasEmptyUploadValue(forkHeader, session.ctx.sessionManager.getEntries()), undefined);

    const inheritedEmpty = makeSession([existingObservation("empty")], forkHeader);
    assert.equal(getFolderWasEmptyUploadValue(forkHeader, inheritedEmpty.ctx.sessionManager.getEntries()), undefined);
  });
});

test("read failure records unknown", async () => {
  const missing = join(tmpdir(), `missing-agent-golf-${process.pid}-${Date.now()}`);
  const session = makeSession([], { type: "session", id: "s", cwd: missing, timestamp: new Date().toISOString() });

  await recordFolderCheckForSession(session.pi, { reason: "startup" }, session.ctx);

  assert.equal(session.pi.appended[0].data.state, "unknown");
  assert.match(session.pi.appended[0].data.reason, /^read-failed/);
  assert.equal(getFolderWasEmptyUploadValue(session.ctx.sessionManager.getHeader(), session.ctx.sessionManager.getEntries()), undefined);
});

test("session switching does not reuse another session's observation", async () => {
  await withTempDir(async (emptyDir) => {
    await withTempDir(async (nonemptyDir) => {
      await writeFile(join(nonemptyDir, "file.txt"), "x");
      const a = makeSession([], { type: "session", id: "a", cwd: emptyDir, timestamp: new Date().toISOString() });
      const b = makeSession([], { type: "session", id: "b", cwd: nonemptyDir, timestamp: new Date().toISOString() });

      await recordFolderCheckForSession(a.pi, { reason: "startup" }, a.ctx);
      await recordFolderCheckForSession(b.pi, { reason: "resume" }, b.ctx);

      assert.equal(a.pi.appended[0].data.state, "empty");
      assert.equal(b.pi.appended[0].data.state, "unknown");
      assert.equal(b.pi.appended[0].data.reason, "not-fresh:resume");
    });
  });
});

async function runPiProbe({ cwd, pluginPath, probePath, sessionDir, configDir, sessionFile, resultPath }) {
  const child = spawn(
    "pi",
    [
      "--mode", "rpc", "--offline", "--no-extensions", "--no-mcp",
      "--no-skills", "--no-prompt-templates", "--no-context-files",
      "--session-dir", sessionDir,
      ...(sessionFile ? ["--session", sessionFile] : []),
      "--extension", pluginPath, "--extension", probePath,
    ],
    {
      cwd,
      env: { ...process.env, PI_CODING_AGENT_DIR: configDir, PI_TELEMETRY: "0" },
      stdio: ["pipe", "pipe", "pipe"],
    },
  );

  let stderr = "";
  let closed = false;
  let spawnError;
  const closePromise = new Promise((resolveClose) => {
    child.once("close", () => {
      closed = true;
      resolveClose();
    });
  });
  child.once("error", (error) => { spawnError = error; });
  child.stdout.resume();
  child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });

  try {
    const deadline = Date.now() + 15_000;
    while (!existsSync(resultPath) && !closed && !spawnError && Date.now() < deadline) {
      await new Promise((resolveWait) => setTimeout(resolveWait, 50));
    }
    assert.equal(spawnError, undefined, `Unable to start Pi: ${spawnError?.message}`);
    assert.equal(existsSync(resultPath), true, `Pi probe failed or timed out: ${stderr}`);
    return JSON.parse(await readFile(resultPath, "utf8"));
  } finally {
    child.stdin.end();
    if (!closed) child.kill("SIGTERM");
    const forceKill = setTimeout(() => { if (!closed) child.kill("SIGKILL"); }, 2_000);
    forceKill.unref();
    try { await closePromise; } finally { clearTimeout(forceKill); }
  }
}

test("isolated Pi smoke: metadata is session state and excluded from model context", async () => {
  await withTempDir(async (dir) => {
    const probePath = join(dir, "probe.ts");
    const resultPath = join(dir, "probe-result.json");
    const sessionDir = join(dir, "sessions");
    const cwd = join(dir, "empty-cwd");
    const pluginPath = resolve("index.ts");
    await mkdir(sessionDir);
    await mkdir(cwd);
    await writeFile(
      probePath,
      `import { writeFileSync } from "node:fs";\n\nexport default function (pi) {\n  pi.on("session_start", async (_event, ctx) => {\n    const entries = ctx.sessionManager.getEntries();\n    const folderEntries = entries.filter((entry) => entry.type === "custom" && entry.customType === "agent-golf-folder-check");\n    const projection = ctx.sessionManager.buildSessionProjection();\n    writeFileSync(${JSON.stringify(resultPath)}, JSON.stringify({\n      folderEntryCount: folderEntries.length,\n      folderState: folderEntries[0]?.data?.state,\n      projectedMessages: projection.messages.length,\n      usageEntries: entries.filter((entry) => entry.type === "usage").length,\n      assistantMessages: entries.filter((entry) => entry.type === "message" && entry.message?.role === "assistant").length\n    }));\n  });\n}\n`,
    );

    const configDir = join(dir, "config");
    const result = await runPiProbe({ cwd, pluginPath, probePath, sessionDir, configDir, resultPath });
    assert.deepEqual(result, {
      folderEntryCount: 1,
      folderState: "empty",
      projectedMessages: 0,
      usageEntries: 0,
      assistantMessages: 0,
    });

    // CLI --session uses startup, not the in-process resume event. Verify a
    // persisted bash-only session cannot be certified from today's empty cwd.
    const sessionFile = join(sessionDir, "old-session.jsonl");
    await writeFile(sessionFile, [
      { type: "session", version: 3, id: "old-session", cwd, timestamp: "2026-10-01T00:00:00.000Z" },
      { type: "message", id: "bash1", parentId: null, timestamp: "2026-10-01T00:00:01.000Z", message: {
        role: "bashExecution", command: "rm -f solution.py", output: "", exitCode: 0,
        cancelled: false, truncated: false, timestamp: 1790812801000,
      } },
    ].map((entry) => JSON.stringify(entry)).join("\n") + "\n");
    await rm(resultPath);
    const reopened = await runPiProbe({ cwd, pluginPath, probePath, sessionDir, configDir, sessionFile, resultPath });
    assert.equal(reopened.folderEntryCount, 1);
    assert.equal(reopened.folderState, "unknown");
    assert.equal(reopened.usageEntries, 0);
    assert.equal(reopened.assistantMessages, 0);
  });
});
