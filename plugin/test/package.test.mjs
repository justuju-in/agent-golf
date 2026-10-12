import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { mkdtemp, mkdir, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { promisify } from "node:util";
import { test } from "node:test";
import { startPi } from "./rpc-helper.mjs";

const execute = promisify(execFile);
const FILES = ["LICENSE", "README.md", "config.ts", "index.ts", "login.ts", "package.json", "problem-view.ts", "problems.ts", "submit.ts", "user-bash.ts"].sort();
// The interactive-Pi smoke test (tui-browser-smoke.py) is opt-in: it needs a real Pi that gets
// ready within the script's 8-second wait, which not every machine does, and the default gate
// must pass anyway. Run it before each release: AGENT_GOLF_TUI_TESTS=1 bash tools/check.sh
// (RELEASING.md). The script exits 77, reported here as a skip, when pi is not on PATH.
const TUI_SKIP = process.platform === "win32" ? true
  : process.env.AGENT_GOLF_TUI_TESTS === "1" ? false
  : "set AGENT_GOLF_TUI_TESTS=1 to run the interactive Pi TUI smoke test (needs pi on PATH)";
const TUI_NO_PI = 77;

test("npm artifact contains only public runtime files and installs independently of the repo", { timeout: 60_000 }, async (t) => {
  const directory = await mkdtemp(join(tmpdir(), "golf-package-"));
  let client;
  try {
    const { stdout } = await execute("npm", ["pack", "--json", "--pack-destination", directory], { cwd: resolve("."), timeout: 30_000 });
    const [packed] = JSON.parse(stdout);
    assert.equal(packed.name, "agent-golf");
    assert.deepEqual(packed.files.map((file) => file.path).sort(), FILES);
    const tarball = join(directory, packed.filename);
    const { stdout: listing } = await execute("tar", ["-tzf", tarball]);
    assert.deepEqual(listing.trim().split("\n").sort(), FILES.map((file) => `package/${file}`).sort());
    const unpacked = join(directory, "unpacked");
    await mkdir(unpacked);
    await execute("tar", ["-xzf", tarball, "-C", unpacked]);
    const root = join(unpacked, "package");
    const manifest = JSON.parse(await readFile(join(root, "package.json"), "utf8"));
    assert.equal(manifest.name, "agent-golf");
    assert.match(manifest.version, /^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$/);
    assert.equal(manifest.version, packed.version);
    assert.equal(manifest.homepage, "https://agent-golf.csbasics.in");
    assert.equal(manifest.license, "MIT");
    assert.equal(manifest.engines.node, ">=22.19.0");
    assert.deepEqual(manifest.pi, { extensions: ["./index.ts"], skills: [], prompts: [], themes: [] });
    assert.deepEqual(manifest.publishConfig, { access: "public", registry: "https://registry.npmjs.org/" });
    assert.deepEqual(manifest.peerDependencies, { "@earendil-works/pi-coding-agent": "*", "@earendil-works/pi-tui": "*" });
    assert.equal(Object.keys(manifest.dependencies ?? {}).length, 0);
    assert.ok(!manifest.private);
    assert.ok(!(await readFile(join(root, "README.md"), "utf8")).includes(".agents/"));
    assert.match(await readFile(join(root, "LICENSE"), "utf8"), /MIT License/);
    for (const file of FILES.filter((file) => file.endsWith(".ts"))) {
      assert.deepEqual(await readFile(join(root, file)), await readFile(file));
    }

    const home = join(directory, "home");
    const config = join(directory, "pi-config");
    const cwd = join(directory, "attempt");
    await mkdir(home);
    await mkdir(cwd);
    const env = { ...process.env, HOME: home, PI_CODING_AGENT_DIR: config, PI_TELEMETRY: "0" };
    await execute("pi", ["install", root, "--no-approve"], { cwd, env, timeout: 20_000 });
    const settings = JSON.parse(await readFile(join(config, "settings.json"), "utf8"));
    assert.ok(settings.packages.some((entry) => resolve(config, typeof entry === "string" ? entry : entry.source) === root), "installed package source resolves to the extracted artifact");
    // Load via installed package settings, NOT --extension pointing at our repo.
    client = startPi({ cwd, env, sessionDir: join(directory, "sessions"), installedPackages: true });
    const before = (await client.request("get_entries")).entries;
    const messages = (await client.request("get_messages")).messages;
    for (const [command, usage] of [["/golf-login", "Usage: /golf-login"], ["/golf-submit", "Usage: /golf-submit"], ["/golf-problems extra", "Usage: /golf-problems"]]) {
      assert.equal((await client.request("prompt", { message: command })).disposition, "handled");
      assert.ok(client.seen.some((record) => record.method === "notify" && record.message.includes(usage)));
    }
    assert.deepEqual((await client.request("get_entries")).entries, before);
    assert.deepEqual((await client.request("get_messages")).messages, messages);
    assert.equal((await client.request("get_session_stats")).tokens.total, 0);
    assert.equal(client.seen.some((record) => record.type === "agent_start" || record.type === "message_start"), false);
    await t.test("packed artifact also loads its custom TUI dependency through interactive Pi", { skip: TUI_SKIP }, async (tui) => {
      try {
        const { stdout } = await execute("python3", [resolve("test/tui-browser-smoke.py"), join(root, "index.ts")], { timeout: 40_000 });
        assert.match(stdout, /REAL TUI PASS/, "packed artifact also loads its custom TUI dependency through Pi");
      } catch (error) {
        if (error.code !== TUI_NO_PI) throw error;
        tui.skip(error.stderr.trim());
      }
    });
  } finally {
    try { await client?.close(); } finally { await rm(directory, { recursive: true, force: true }); }
  }
});
