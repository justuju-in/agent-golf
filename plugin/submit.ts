import { readFile } from "node:fs/promises";
import type { ExtensionContext } from "@earendil-works/pi-coding-agent";
import { readStoredCredential, type LoginResult } from "./login.ts";
import { getApiOrigin, resolveApiOrigin } from "./config.ts";
import { hasPendingUserBash } from "./user-bash.ts";

export interface SubmitOptions {
  baseUrl?: string;
  credentialDir?: string;
  timeoutMs?: number;
  folderWasEmpty?: "true" | "false";
}

type SubmitContext = Pick<ExtensionContext, "ui" | "hasUI" | "isIdle" | "sessionManager">;

const REASONS = new Set([
  "not_solved", "model_mismatch", "thinking_level_mismatch", "model_switched", "folder_reused", "missing_usage",
  "custom_setup", "inconsistent_log", "usage_not_recorded", "bad_key", "not_pi_log", "unknown_problem", "file_too_large",
]);

function error(message: string): LoginResult {
  return { message, type: "error" };
}

function formatReply(value: unknown, httpStatus: number, key: string): LoginResult | undefined {
  if (!value || typeof value !== "object") return undefined;
  const data = value as Record<string, unknown>;
  if (!Array.isArray(data.reasons) || !data.reasons.every((reason) => typeof reason === "string" && REASONS.has(reason))) return undefined;
  const reasons = data.reasons.length ? data.reasons.join(", ") : "none";
  if (httpStatus !== 200) {
    if (data.status !== "rejected" || data.metrics !== null || data.url !== null) return undefined;
    const allowed = httpStatus === 401 ? ["bad_key"] : httpStatus === 413 ? ["file_too_large"] : ["not_pi_log", "unknown_problem"];
    if (!data.reasons.length || !data.reasons.every((reason) => allowed.includes(reason))) return undefined;
    return error(`Submission rejected: ${reasons}.${httpStatus === 401 ? " Run /golf-login with a valid key for this server." : ""}`);
  }
  if (data.status !== "ranked" && data.status !== "unranked") return undefined;
  if (!data.metrics || typeof data.metrics !== "object" || typeof data.url !== "string") return undefined;
  const metrics = data.metrics as Record<string, unknown>;
  const unknownTokens = data.reasons.includes("missing_usage");
  // Validate the contract's null/reason pair, not the score or ranking verdict.
  if (unknownTokens !== (metrics.total_tokens === null)) return undefined;
  for (const name of ["total_tokens", "prompts", "chars_typed", "tool_calls"]) {
    if (name === "total_tokens" && unknownTokens) continue;
    if (typeof metrics[name] !== "number" || !Number.isSafeInteger(metrics[name]) || metrics[name] < 0) return undefined;
  }
  for (const name of ["models", "thinking_levels"]) {
    if (!Array.isArray(metrics[name]) || !metrics[name].every((item) => typeof item === "string" && !/[\x00-\x1f\x7f]/.test(item))) return undefined;
  }
  if (typeof metrics.solved !== "boolean") return undefined;
  let url: URL;
  try {
    url = new URL(data.url);
    getApiOrigin(url.origin);
    if (url.username || url.password || /[\x00-\x1f\x7f]/.test(data.url)) return undefined;
  } catch {
    return undefined;
  }
  const message = [
    `Submission ${data.status}. Reasons: ${reasons}.`,
    `Tokens: ${unknownTokens ? "unknown" : metrics.total_tokens}; prompts: ${metrics.prompts}; characters: ${metrics.chars_typed}; tool calls: ${metrics.tool_calls}; solved: ${metrics.solved}.`,
    `Models: ${(metrics.models as string[]).join(", ")}; thinking levels: ${(metrics.thinking_levels as string[]).join(", ")}.`,
    url.href,
  ].join("\n");
  if (message.includes(key)) return undefined;
  return { message, type: "info" };
}

// One upload at a time within this extension runtime; no model interaction.
let submitting = false;

export async function submitSession(args: string, ctx: SubmitContext, options: SubmitOptions = {}): Promise<LoginResult> {
  const problem = args.trim();
  if (!/^[a-z0-9]+(?:_[a-z0-9]+)*$/.test(problem)) return { message: "Usage: /golf-submit <problem> (for example: help_me_unpack)", type: "info" };
  if (submitting) return error("Another submission is already in progress. Wait for it to finish.");
  submitting = true;
  try {
    if (!ctx.hasUI) return error("Submission requires a confirmation dialog. Use interactive Pi or an RPC client with UI support.");
    if (!ctx.isIdle()) return error("Pi is busy. Finish the current response before submitting.");
    if (hasPendingUserBash(ctx.sessionManager.getEntries())) return error("A user Bash command is still running or its result has not been recorded. Wait for it to finish before submitting.");
    let origin: string;
    try {
      origin = resolveApiOrigin(options.baseUrl);
    } catch {
      return error("Invalid server origin override. Set AGENT_GOLF_API_BASE_URL to a valid HTTPS server origin (loopback HTTP is allowed for local testing).");
    }
    let credential;
    try {
      credential = await readStoredCredential(origin, options.credentialDir);
    } catch {
      return error("Stored credentials could not be read securely. Run /golf-login again; check the private credential file if the problem persists.");
    }
    if (!credential) return error("No key saved for this server. Run /golf-login <key> first.");

    const sessionId = ctx.sessionManager.getSessionId();
    const sessionFile = ctx.sessionManager.getSessionFile();
    const leafId = ctx.sessionManager.getLeafId();
    if (!sessionFile) return error("No persisted session file is available. Submit from the saved session where you solved the problem.");
    let bytes: Buffer;
    try {
      bytes = await readFile(sessionFile);
    } catch {
      return error("The current session file is unavailable or unreadable. Nothing was uploaded.");
    }
    if (!bytes.length) return error("The current session file is empty. Nothing was uploaded.");
    const stillCurrent = () => ctx.isIdle() && !hasPendingUserBash(ctx.sessionManager.getEntries()) && ctx.sessionManager.getSessionId() === sessionId &&
      ctx.sessionManager.getSessionFile() === sessionFile && ctx.sessionManager.getLeafId() === leafId;
    if (!stillCurrent()) return error("Pi or the session changed while preparing submission. Try again when idle.");
    const confirmed = await ctx.ui.confirm("Submit to Agent Golf?", [
      `Problem: ${problem}`,
      `Server: ${origin}`,
      `Session file size: ${bytes.length} bytes`,
      "This uploads the complete raw session, including abandoned branches. It may contain Hackattic tokens, prompts, and local paths. Only proceed if you trust this server.",
    ].join("\n"));
    if (!confirmed) return { message: "Submission cancelled. Nothing was uploaded.", type: "info" };
    if (!stillCurrent()) return error("Pi or the session changed during confirmation. Nothing was uploaded; try again when idle.");
    const currentBytes = await readFile(sessionFile);
    if (!bytes.equals(currentBytes) || !stillCurrent()) return error("The session changed during confirmation. Nothing was uploaded; try again.");

    const form = new FormData();
    form.append("problem", problem);
    form.append("session", new Blob([new Uint8Array(bytes)], { type: "application/x-ndjson" }), "session.jsonl");
    if (options.folderWasEmpty !== undefined) form.append("folder_was_empty", options.folderWasEmpty);
    try {
      const response = await fetch(`${origin}/api/v1/submissions`, {
        method: "POST", headers: { Authorization: `Bearer ${credential.key}`, Accept: "application/json" },
        body: form, redirect: "error", signal: AbortSignal.timeout(options.timeoutMs ?? 60_000),
      });
      if (![200, 400, 401, 413].includes(response.status)) {
        await response.body?.cancel();
        return error("Submission failed: server error. This does not mean your file or key is invalid.");
      }
      if (!/^application\/json(?:\s*;|$)/i.test(response.headers.get("content-type") ?? "")) {
        await response.body?.cancel();
        return error("The server returned an invalid submission response. Check the website before retrying.");
      }
      const result = formatReply(await response.json(), response.status, credential.key);
      return result ?? error("The server returned an invalid submission response. Check the website before retrying.");
    } catch {
      // Never display exceptions or arbitrary response bodies: they may contain keys/logs.
      return error("Submission failed: server unreachable, request timed out, redirect refused, or invalid response. The upload may have reached the server; check the website before retrying.");
    }
  } catch {
    return error("Submission stopped because the session or local file became unavailable. No automatic retry was made.");
  } finally {
    submitting = false;
  }
}
