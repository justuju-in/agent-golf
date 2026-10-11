import { spawn } from "node:child_process";
import { join } from "node:path";

export function startWebsite(directory, env, port = 0) {
  const child = spawn(join(directory, ".venv", "bin", "python"), [
    "-m", "uvicorn", "server.app:app", "--host", "127.0.0.1", "--port", String(port), "--no-access-log",
  ], { cwd: directory, env, stdio: ["ignore", "pipe", "pipe"] });
  const closed = new Promise((resolveClose) => child.once("close", resolveClose));
  const origin = new Promise((resolveOrigin, reject) => {
    let output = "";
    const timer = setTimeout(() => reject(new Error("Local website did not become ready")), 15_000);
    const finish = (callback, value) => { clearTimeout(timer); callback(value); };
    const inspect = (chunk) => {
      output = (output + chunk.toString()).slice(-16_384);
      const match = /http:\/\/127\.0\.0\.1:([1-9][0-9]*)/.exec(output);
      if (match) finish(resolveOrigin, match[0]);
    };
    child.stdout.on("data", inspect);
    child.stderr.on("data", inspect);
    child.once("error", () => finish(reject, new Error("Local website failed to start")));
    child.once("close", () => finish(reject, new Error("Local website stopped")));
  });
  return {
    origin,
    stop: async () => {
      if (child.exitCode === null && child.signalCode === null) child.kill("SIGTERM");
      const timer = setTimeout(() => child.kill("SIGKILL"), 2_000);
      timer.unref();
      try { await closed; } finally { clearTimeout(timer); }
    },
  };
}
