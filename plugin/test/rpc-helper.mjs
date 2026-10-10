import { spawn } from "node:child_process";
import { resolve } from "node:path";

export function startPi({ cwd, env, sessionDir, sessionFile, onRecord = () => {} }) {
  const child = spawn("pi", [
    "--mode", "rpc", "--offline", "--no-extensions", "--no-mcp", "--no-skills",
    "--no-prompt-templates", "--no-context-files", "--extension", resolve("index.ts"),
    "--session-dir", sessionDir, ...(sessionFile ? ["--session", sessionFile] : []),
  ], { cwd, env: { ...process.env, ...env, PI_TELEMETRY: "0" }, stdio: ["pipe", "pipe", "pipe"] });
  const pending = new Map();
  const seen = [];
  let buffer = "";
  let stderr = "";
  let closed = false;
  let serial = 0;
  const failPending = (error) => {
    for (const request of pending.values()) { clearTimeout(request.timer); request.reject(error); }
    pending.clear();
  };
  const closePromise = new Promise((resolveClose) => {
    child.once("close", () => {
      closed = true;
      failPending(new Error(`Pi closed before responding: ${stderr}`));
      resolveClose();
    });
  });
  child.on("error", failPending);
  child.stdin.on("error", failPending);
  child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
  const send = (record) => child.stdin.write(JSON.stringify(record) + "\n");
  child.stdout.setEncoding("utf8");
  child.stdout.on("data", (chunk) => {
    buffer += chunk;
    let boundary;
    while ((boundary = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 1);
      if (!line.trim()) continue;
      try {
        const record = JSON.parse(line);
        seen.push(record);
        onRecord(record);
        const request = pending.get(record.id);
        if (record.type === "response" && request) {
          clearTimeout(request.timer);
          pending.delete(record.id);
          if (record.success) request.resolve(record.data);
          else request.reject(new Error("Pi command failed"));
        }
      } catch (error) { failPending(error); }
    }
  });
  return {
    seen,
    respondUI: (id, confirmed) => send({ type: "extension_ui_response", id, confirmed }),
    request: (type, fields = {}) => new Promise((resolveRequest, reject) => {
      if (closed) return reject(new Error("Pi already closed"));
      const id = String(++serial);
      const timer = setTimeout(() => { pending.delete(id); reject(new Error("Pi request timed out")); }, 15_000);
      pending.set(id, { resolve: resolveRequest, reject, timer });
      send({ id, type, ...fields });
    }),
    close: async () => {
      child.stdin.end();
      if (!closed) child.kill("SIGTERM");
      const forceKill = setTimeout(() => { if (!closed) child.kill("SIGKILL"); }, 2_000);
      forceKill.unref();
      try { await closePromise; } finally { clearTimeout(forceKill); }
    },
  };
}
