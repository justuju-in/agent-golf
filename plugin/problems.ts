import type { ExtensionContext } from "@earendil-works/pi-coding-agent";
import { resolveApiOrigin } from "./config.ts";
import { showProblemView } from "./problem-view.ts";

export const MAX_PROBLEM_BODY_BYTES = 64 * 1024;
const MAX_STRING_CHARACTERS = 1000;
const UNAVAILABLE = "Problem list unavailable. Check the configured server and connection, then try /golf-problems again.";
const ADVISORY = "Informational only: browsing does not start or bind an attempt. Upload checks remain authoritative. Nothing is uploaded by browsing.";

interface Problem {
  slug: string;
  title: string;
  challenge_url: string;
  instructions: string[];
  model: string;
  thinking_level: string;
}
interface Catalogue { rules_version: string; rules: string[]; problems: Problem[] }
interface Result { message: string; type: "info" | "error" }
export interface ProblemOptions { baseUrl?: string; timeoutMs?: number }

function safeStrings(value: unknown): boolean {
  if (typeof value === "string") {
    // Newlines/tabs are ordinary text in the temporary editor, not escapes.
    return Array.from(value).length <= MAX_STRING_CHARACTERS && value.isWellFormed() &&
      !/[\x00-\x08\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/u.test(value);
  }
  if (Array.isArray(value)) return value.every(safeStrings);
  if (value && typeof value === "object") return Object.entries(value).every(([key, item]) => safeStrings(key) && safeStrings(item));
  return true;
}

function catalogue(value: unknown): Catalogue | undefined {
  if (!value || typeof value !== "object" || !safeStrings(value)) return undefined;
  const data = value as Record<string, unknown>;
  const text = (item: unknown): item is string => typeof item === "string" && item.trim().length > 0;
  const texts = (item: unknown): item is string[] => Array.isArray(item) && item.every((s) => typeof s === "string");
  if (!text(data.rules_version) || !texts(data.rules) || !Array.isArray(data.problems)) return undefined;
  const slugs = new Set<string>();
  for (const item of data.problems) {
    if (!item || typeof item !== "object") return undefined;
    const problem = item as Record<string, unknown>;
    if (!text(problem.slug) || !/^[a-z0-9]+(?:_[a-z0-9]+)*$/.test(problem.slug) || slugs.has(problem.slug) ||
      !text(problem.title) || problem.challenge_url !== `https://hackattic.com/challenges/${problem.slug}` ||
      !texts(problem.instructions) || !text(problem.model) || !text(problem.thinking_level)) return undefined;
    if (problem.model !== "any" && !/^[^\s/]+\/\S+$/.test(problem.model)) return undefined;
    if (!/^[a-z][a-z0-9_-]*$/.test(problem.thinking_level)) return undefined;
    slugs.add(problem.slug);
  }
  return data as unknown as Catalogue;
}

async function readCatalogue(response: Response): Promise<Catalogue | undefined> {
  if (!response.body) return undefined;
  const reader = response.body.getReader();
  let size = 0;
  const chunks: Uint8Array[] = [];
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_PROBLEM_BODY_BYTES) return undefined;
      chunks.push(value);
    }
    return catalogue(JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks))));
  } finally {
    await reader.cancel();
    reader.releaseLock();
  }
}

let browsing = false;
export async function browseProblems(
  args: string,
  ctx: Pick<ExtensionContext, "ui" | "hasUI" | "mode">,
  options: ProblemOptions = {},
): Promise<Result> {
  if (args.trim()) return { message: "Usage: /golf-problems", type: "info" };
  if (!ctx.hasUI) return { message: "Problem browsing requires interactive Pi or an RPC client with UI support.", type: "error" };
  if (browsing) return { message: "Another problem browser is open. Close it first.", type: "error" };
  browsing = true;
  try {
    const origin = resolveApiOrigin(options.baseUrl);
    const response = await fetch(`${origin}/api/v1/problems`, {
      headers: { Accept: "application/json" }, credentials: "omit", redirect: "error",
      signal: AbortSignal.timeout(options.timeoutMs ?? 10_000),
    });
    if (response.status !== 200 || !/^application\/json(?:\s*;|$)/i.test(response.headers.get("content-type") ?? "") ||
      Number(response.headers.get("content-length")) > MAX_PROBLEM_BODY_BYTES) {
      await response.body?.cancel();
      return { message: UNAVAILABLE, type: "error" };
    }
    const data = await readCatalogue(response);
    if (!data) return { message: UNAVAILABLE, type: "error" };
    const rules = [`Rules version: ${data.rules_version}`, "", ...data.rules, "", ADVISORY];
    if (!data.problems.length) rules.push("", "No problems are currently listed.");
    const continued = await showProblemView(ctx, "Agent Golf rules", rules.join("\n"),
      data.problems.length ? "view problems" : "close", "close");
    if (continued && data.problems.length) {
      const labels = data.problems.map((p) => `${p.title.replace(/[\n\t]/g, " ")} (${p.slug})`);
      while (true) {
        const selected = await ctx.ui.select("Agent Golf problems — choose to view details", labels);
        const index = selected === undefined ? -1 : labels.indexOf(selected);
        if (index < 0) break;
        const problem = data.problems[index];
        await showProblemView(ctx, "Problem details", [
          problem.title, `Problem: ${problem.slug}`, problem.challenge_url,
          `Model: ${problem.model === "any" ? "any model, one per session" : problem.model}`,
          `Thinking level: ${problem.thinking_level === "any" ? "any thinking level" : problem.thinking_level}`,
          "", ...problem.instructions, "", ADVISORY,
        ].join("\n"), "back to problems", "back to problems");
      }
    }
    return { message: "Problem browsing closed. No attempt or setup was changed.", type: "info" };
  } catch {
    // Never render arbitrary error bodies, URL overrides or exception strings.
    return { message: UNAVAILABLE, type: "error" };
  } finally {
    browsing = false;
  }
}
