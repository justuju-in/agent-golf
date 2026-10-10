import { readdir } from "node:fs/promises";
import type {
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import type {
  CustomEntry,
  SessionEntry,
  SessionHeader,
} from "@earendil-works/pi-coding-agent/dist/core/session-manager";

export const FOLDER_CHECK_CUSTOM_TYPE = "agent-golf-folder-check";
export const FOLDER_CHECK_POLICY = "zero-directory-entries";

export type FolderCheckState = "empty" | "nonempty" | "unknown";

export interface FolderCheckMetadata {
  schema: 1;
  state: FolderCheckState;
  checked_at: string;
  policy: typeof FOLDER_CHECK_POLICY;
  reason?: string;
}

interface SessionStartLike {
  reason: "startup" | "reload" | "new" | "resume" | "fork";
}

function isFolderCheckMetadata(value: unknown): value is FolderCheckMetadata {
  if (!value || typeof value !== "object") return false;
  const data = value as Record<string, unknown>;
  return (
    data.schema === 1 &&
    (data.state === "empty" || data.state === "nonempty" || data.state === "unknown") &&
    typeof data.checked_at === "string" &&
    data.policy === FOLDER_CHECK_POLICY &&
    (data.reason === undefined || typeof data.reason === "string")
  );
}

export function getFolderCheckEntries(entries: readonly SessionEntry[]): CustomEntry<FolderCheckMetadata>[] {
  return entries.filter(
    (entry): entry is CustomEntry<FolderCheckMetadata> =>
      entry.type === "custom" &&
      entry.customType === FOLDER_CHECK_CUSTOM_TYPE &&
      isFolderCheckMetadata(entry.data),
  );
}

export function getInitialFolderCheckMetadata(
  entries: readonly SessionEntry[],
): FolderCheckMetadata | undefined {
  return getFolderCheckEntries(entries)[0]?.data;
}

export function getFolderWasEmptyUploadValue(
  header: SessionHeader | null,
  entries: readonly SessionEntry[],
): "true" | "false" | undefined {
  if (header?.parentSession) return undefined;

  const metadata = getInitialFolderCheckMetadata(entries);
  if (metadata?.state === "empty") return "true";
  if (metadata?.state === "nonempty") return "false";
  return undefined;
}

function observation(state: FolderCheckState, reason?: string): FolderCheckMetadata {
  return {
    schema: 1,
    state,
    checked_at: new Date().toISOString(),
    policy: FOLDER_CHECK_POLICY,
    ...(reason ? { reason } : {}),
  };
}

async function observeFreshCwd(cwd: string): Promise<FolderCheckMetadata> {
  try {
    const entries = await readdir(cwd);
    return observation(entries.length === 0 ? "empty" : "nonempty");
  } catch (error) {
    const code =
      error && typeof error === "object" && "code" in error
        ? String((error as { code?: unknown }).code)
        : undefined;
    return observation("unknown", code ? `read-failed:${code}` : "read-failed");
  }
}

export async function recordFolderCheckForSession(
  pi: Pick<ExtensionAPI, "appendEntry">,
  event: SessionStartLike,
  ctx: Pick<ExtensionContext, "cwd" | "sessionManager">,
): Promise<void> {
  const entries = ctx.sessionManager.getEntries();
  if (getInitialFolderCheckMetadata(entries)) return;

  const header = ctx.sessionManager.getHeader();
  let metadata: FolderCheckMetadata;

  if (event.reason === "fork" || header?.parentSession) {
    metadata = observation("unknown", "inherited-session");
  } else if (
    (event.reason === "startup" || event.reason === "new") &&
    !entries.some(
      (entry) =>
        entry.type === "message" &&
        (entry.message.role === "user" || entry.message.role === "assistant"),
    )
  ) {
    metadata = await observeFreshCwd(ctx.cwd);
  } else {
    metadata = observation("unknown", `not-fresh:${event.reason}`);
  }

  pi.appendEntry(FOLDER_CHECK_CUSTOM_TYPE, metadata);
}

export default function (pi: ExtensionAPI) {
  pi.on("session_start", async (event, ctx) => {
    await recordFolderCheckForSession(pi, event, ctx);
  });

  pi.registerCommand("golf-login", {
    description: "Log in to Agent Golf (not implemented yet)",
    handler: async (args, ctx) => {
      if (!args.trim()) {
        ctx.ui.notify("Usage: /golf-login <key>", "info");
        return;
      }

      // Never echo or persist the supplied key in this command stub.
      ctx.ui.notify("Agent Golf login is not implemented yet. No key was saved.", "info");
    },
  });

  pi.registerCommand("golf-submit", {
    description: "Submit the current session to Agent Golf (not implemented yet)",
    handler: async (args, ctx) => {
      if (!args.trim()) {
        ctx.ui.notify("Usage: /golf-submit <problem>", "info");
        return;
      }

      ctx.ui.notify("Agent Golf submission is not implemented yet. Nothing was uploaded.", "info");
    },
  });
}
