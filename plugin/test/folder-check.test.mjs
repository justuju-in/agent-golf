import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
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

test("plugin preserves command stubs", async () => {
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
  const ctx = { ui: { notify: (message, type) => notifications.push({ message, type }) } };
  await commands.get("golf-login").handler("", ctx);
  await commands.get("golf-login").handler("secret-key", ctx);
  await commands.get("golf-submit").handler("", ctx);
  await commands.get("golf-submit").handler("help_me_unpack", ctx);

  assert.deepEqual(notifications, [
    { message: "Usage: /golf-login <key>", type: "info" },
    { message: "Agent Golf login is not implemented yet. No key was saved.", type: "info" },
    { message: "Usage: /golf-submit <problem>", type: "info" },
    { message: "Agent Golf submission is not implemented yet. Nothing was uploaded.", type: "info" },
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

    const child = spawn(
      "pi",
      [
        "--mode",
        "rpc",
        "--offline",
        "--no-extensions",
        "--no-skills",
        "--no-prompt-templates",
        "--no-context-files",
        "--session-dir",
        sessionDir,
        "--extension",
        pluginPath,
        "--extension",
        probePath,
      ],
      { cwd, stdio: ["ignore", "pipe", "pipe"] },
    );

    let stderr = "";
    let exited = false;
    const exitPromise = new Promise((resolveExit) => {
      child.once("exit", (code, signal) => {
        exited = true;
        resolveExit({ code, signal });
      });
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    try {
      const deadline = Date.now() + 15_000;
      while (!existsSync(resultPath) && !exited && Date.now() < deadline) {
        await new Promise((resolveWait) => setTimeout(resolveWait, 100));
      }
      assert.equal(existsSync(resultPath), true, stderr);
      const result = JSON.parse(await (await import("node:fs/promises")).readFile(resultPath, "utf8"));

      assert.deepEqual(result, {
        folderEntryCount: 1,
        folderState: "empty",
        projectedMessages: 0,
        usageEntries: 0,
        assistantMessages: 0,
      });
    } finally {
      if (!exited) child.kill("SIGTERM");
      await exitPromise;
    }
  });
});
