import { createHash } from "node:crypto";
import type { SessionEntry } from "@earendil-works/pi-coding-agent";

export const USER_BASH_START = "agent-golf-user-bash-start";

export function userBashStartMetadata(command: string) {
  return { schema: 1, command_sha256: createHash("sha256").update(command).digest("hex") };
}

// user_bash fires before execution; the Bash result is appended only after it
// finishes (or after deferred results are flushed). Scan the whole session,
// not just the active branch, to match starts with their recorded results.
// Custom markers persist across reloads and never enter model context.
export function hasPendingUserBash(entries: readonly SessionEntry[]): boolean {
  const pending = new Map<string, number>();
  for (const entry of entries) {
    if (entry.type === "custom" && entry.customType === USER_BASH_START) {
      const data = entry.data as { schema?: unknown; command_sha256?: unknown } | null;
      if (!data || data.schema !== 1 || typeof data.command_sha256 !== "string" || !/^[a-f0-9]{64}$/.test(data.command_sha256)) return true;
      pending.set(data.command_sha256, (pending.get(data.command_sha256) ?? 0) + 1);
    } else if (entry.type === "message" && entry.message.role === "bashExecution") {
      const digest = userBashStartMetadata(entry.message.command).command_sha256;
      const count = pending.get(digest) ?? 0;
      if (count > 0) pending.set(digest, count - 1);
    }
  }
  return [...pending.values()].some((count) => count > 0);
}
