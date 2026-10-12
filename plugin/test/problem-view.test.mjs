import assert from "node:assert/strict";
import { execFileSync, execFile } from "node:child_process";
import { promisify } from "node:util";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { test } from "node:test";
import { createProblemView, showProblemView } from "../problem-view.ts";

// The interactive-Pi smoke test (tui-browser-smoke.py) is opt-in: it needs a real Pi that gets
// ready within the script's 8-second wait, which not every machine does, and the default gate
// must pass anyway. Run it before each release: AGENT_GOLF_TUI_TESTS=1 bash tools/check.sh
// (RELEASING.md). The script exits 77, reported here as a skip, when pi is not on PATH.
const TUI_SKIP = process.platform === "win32" ? true
  : process.env.AGENT_GOLF_TUI_TESTS === "1" ? false
  : "set AGENT_GOLF_TUI_TESTS=1 to run the interactive Pi TUI smoke test (needs pi on PATH)";
const TUI_NO_PI = 77;

test("real interactive Pi browser uses custom navigation without submit hints", { skip: TUI_SKIP, timeout: 45_000 }, async (t) => {
  try {
    const { stdout } = await promisify(execFile)("python3", [resolve("test/tui-browser-smoke.py"), resolve("index.ts")], { timeout: 40_000 });
    assert.match(stdout, /REAL TUI PASS/);
  } catch (error) {
    if (error.code !== TUI_NO_PI) throw error;
    t.skip(error.stderr.trim());
  }
});

const root = execFileSync("npm", ["root", "-g"], { encoding: "utf8" }).trim();
const lib = await import(pathToFileURL(join(root, "@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-tui/dist/index.js")).href);
function fixture(body = Array.from({ length: 60 }, (_, i) => `Rule ${i}: plain text π 中文 🙂`).join("\n"), action = "view problems", cancel = "close") {
  const completed = [];
  const tui = { terminal: { rows: 24 }, requestRender() {} };
  const bindings = {
    getKeys: (name) => [name.endsWith("confirm") ? "enter" : "esc"],
    matches: (data, name) => lib.matchesKey(data, name.endsWith("confirm") ? lib.Key.enter : lib.Key.escape),
  };
  let color = "34";
  const theme = { fg: (_name, text) => `\x1b[${color}m${text}\x1b[0m` };
  const view = createProblemView(lib, tui, theme, bindings, (value) => completed.push(value),
    "Rules", body, action, cancel);
  return { view, tui, bindings, completed, changeTheme: () => { color = "32"; } };
}

test("read-only viewer renders bounded Unicode lines and explicit navigation, never submit", () => {
  const f = fixture();
  for (const rows of [9, 24, 60]) {
    f.tui.terminal.rows = rows;
    for (const width of [1, 8, 24, 80]) {
      const lines = f.view.render(width);
      assert.ok(lines.length <= Math.max(1, rows - 5));
      assert.ok(lines.every((line) => lib.visibleWidth(line) <= width));
      assert.ok(!lines.join("\n").includes("submit"));
    }
  }
  assert.match(f.view.render(80).join("\n"), /enter: view problems.*esc: close/);
});

test("narrow navigation remains complete, details combine identical actions and tiny terminals request resize", () => {
  const rules = fixture();
  const plain = (lines) => lines.join(" ").replace(/\x1b\[[0-9;]*m/g, "").replace(/\s+/g, " ");
  const narrow = plain(rules.view.render(24));
  assert.match(narrow, /enter: view problems.*esc: close/);
  assert.match(narrow, /↑\/↓ scroll/);
  const details = fixture("Read details", "back to problems", "back to problems");
  assert.match(plain(details.view.render(30)), /enter\/esc: back to problems/);
  assert.equal((plain(details.view.render(30)).match(/back to problems/g) ?? []).length, 1);
  const tiny = plain(rules.view.render(8));
  assert.ok(!tiny.includes("view problems"));
  rules.tui.terminal.rows = 7;
  assert.ok(rules.view.render(24).length <= 2);
  assert.match(plain(rules.view.render(24)), /Resize terminal/);
  rules.tui.terminal.rows = 24;
  assert.match(plain(rules.view.render(80)), /Rule 0:/);
});

test("scrolling, paging, bounds, resize and theme invalidation preserve content", () => {
  const f = fixture();
  const first = f.view.render(80);
  f.view.handleInput("\x1b[B");
  assert.notDeepEqual(f.view.render(80), first);
  f.view.handleInput("\x1b[6~");
  assert.match(f.view.render(80).join("\n"), /Rule 17:/);
  f.view.handleInput("\x1b[F");
  assert.match(f.view.render(80).join("\n"), /Rule 59:/);
  for (let i = 0; i < 100; i++) f.view.handleInput("\x1b[B");
  assert.match(f.view.render(80).join("\n"), /Rule 59:/);
  f.tui.terminal.rows = 12;
  assert.ok(f.view.render(15).every((line) => lib.visibleWidth(line) <= 15));
  f.view.handleInput("\x1b[H");
  assert.match(f.view.render(80).join("\n"), /Rule 0:/);
  f.changeTheme(); f.view.invalidate();
  assert.ok(f.view.render(80)[0].includes("\x1b[32m"));
});

test("typing/paste cannot edit, completion happens once and cancellation is explicit", () => {
  for (const [key, result] of [["\r", true], ["\x1b", false], ["\x03", false]]) {
    const f = fixture("Read-only rules");
    const before = f.view.render(80);
    f.view.handleInput("EDITED_CONTENT");
    f.view.handleInput("\x1b[200~PASTED_CONTENT\x1b[201~");
    assert.deepEqual(f.view.render(80), before);
    f.view.handleInput(key); f.view.handleInput("\r");
    assert.deepEqual(f.completed, [result]);
  }
});

test("navigation hints follow configured confirm/cancel bindings", () => {
  const f = fixture();
  f.bindings.getKeys = (name) => [name.endsWith("confirm") ? "ctrl+o" : "ctrl+x"];
  f.bindings.matches = (data, name) => lib.matchesKey(data, lib.Key.ctrl(name.endsWith("confirm") ? "o" : "x"));
  assert.match(f.view.render(80).join("\n"), /ctrl\+o: view problems.*ctrl\+x: close/);
  f.view.handleInput("\x0f");
  assert.deepEqual(f.completed, [true]);
});

test("RPC fallback explains navigation and returns cancellation without invoking custom TUI", async () => {
  const views = [];
  const ctx = { mode: "rpc", ui: {
    custom() { throw new Error("RPC must not use terminal UI"); },
    editor: async (title, prefill) => { views.push({ title, prefill }); return undefined; },
  } };
  assert.equal(await showProblemView(ctx, "Rules", "Read rules", "view problems", "close"), false);
  assert.match(views[0].title, /Enter: view problems; Esc: close \(not an upload\)/);
  assert.match(views[0].prefill, /Enter navigates; it does not upload/);
});
