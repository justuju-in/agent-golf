import { constants } from "node:fs";
import { chmod, lstat, mkdir, open, rename, unlink } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { homedir } from "node:os";
import { join } from "node:path";
import { getApiOrigin, resolveApiOrigin } from "./config.ts";
export { getApiOrigin } from "./config.ts";

export interface LoginOptions {
  baseUrl?: string;
  credentialDir?: string;
  timeoutMs?: number;
}

export interface LoginResult {
  message: string;
  type: "info" | "error";
}

interface Credential {
  key: string;
  username: string;
}

interface CredentialFile {
  schema: 1;
  credentials: Record<string, Credential>;
}

const USERNAME = /^[a-z0-9_]{3,32}$/;
const SETUP_MESSAGE = "Set AGENT_GOLF_API_BASE_URL to the server origin (for local testing: http://localhost:8000).";

function isCredentialFile(value: unknown): value is CredentialFile {
  if (!value || typeof value !== "object") return false;
  const data = value as Partial<CredentialFile>;
  if (data.schema !== 1 || !data.credentials || typeof data.credentials !== "object" || Array.isArray(data.credentials)) return false;
  return Object.entries(data.credentials).every(([origin, credential]) => {
    try {
      return getApiOrigin(origin) === origin && !!credential &&
        typeof credential.key === "string" && credential.key.length > 0 &&
        typeof credential.username === "string" && USERNAME.test(credential.username);
    } catch {
      return false;
    }
  });
}

export async function readStoredCredential(
  origin: string,
  directory = join(homedir(), ".config", "agent-golf"),
): Promise<Credential | undefined> {
  let file;
  try {
    const folder = await lstat(directory);
    if (!folder.isDirectory() || (folder.mode & 0o077) !== 0) throw new Error("insecure-credential-directory");
    file = await open(join(directory, "credentials.json"), constants.O_RDONLY | constants.O_NOFOLLOW);
    const info = await file.stat();
    if (!info.isFile() || (info.mode & 0o077) !== 0) throw new Error("insecure-credential-file");
    const parsed: unknown = JSON.parse(await file.readFile("utf8"));
    if (!isCredentialFile(parsed)) throw new Error("invalid-credential-file");
    return parsed.credentials[origin];
  } catch (error) {
    if (error && typeof error === "object" && "code" in error && error.code === "ENOENT") return undefined;
    throw error;
  } finally {
    await file?.close();
  }
}

// Serialize read-modify-write operations within this Pi process so concurrent
// logins to different origins don't erase one another's saved credentials.
let pendingSave: Promise<void> = Promise.resolve();

async function writeCredential(origin: string, key: string, username: string, directory: string): Promise<void> {
  await mkdir(directory, { recursive: true, mode: 0o700 });
  if (!(await lstat(directory)).isDirectory()) throw new Error("invalid-credential-directory");
  await chmod(directory, 0o700);
  const destination = join(directory, "credentials.json");
  let data: CredentialFile = { schema: 1, credentials: {} };
  let existing;
  try {
    existing = await open(destination, constants.O_RDONLY | constants.O_NOFOLLOW);
    const parsed: unknown = JSON.parse(await existing.readFile("utf8"));
    if (!isCredentialFile(parsed)) throw new Error("invalid-credential-file");
    data = parsed;
  } catch (error) {
    if (!(error && typeof error === "object" && "code" in error && error.code === "ENOENT")) throw error;
  } finally {
    await existing?.close();
  }
  data.credentials[origin] = { key, username };

  const temporary = join(directory, `.credentials-${randomUUID()}.tmp`);
  const file = await open(temporary, "wx", 0o600);
  try {
    try {
      await file.chmod(0o600);
      await file.writeFile(JSON.stringify(data) + "\n", "utf8");
      await file.sync();
    } finally {
      await file.close();
    }
    await rename(temporary, destination);
  } finally {
    await unlink(temporary).catch(() => {});
  }
}

export async function loginStudent(args: string, options: LoginOptions = {}): Promise<LoginResult> {
  const key = args.trim();
  if (!key || /\s|[\x00-\x1f\x7f]/.test(key)) {
    return { message: "Usage: /golf-login <key>", type: "info" };
  }

  let origin: string;
  try {
    origin = resolveApiOrigin(options.baseUrl);
  } catch {
    return { message: `Invalid server origin override. ${SETUP_MESSAGE} Use HTTPS except for loopback development; do not include credentials, a path, query, or fragment.`, type: "error" };
  }

  let username: string;
  try {
    const response = await fetch(`${origin}/api/v1/me`, {
      headers: { Authorization: `Bearer ${key}`, Accept: "application/json" },
      redirect: "error",
      signal: AbortSignal.timeout(options.timeoutMs ?? 10_000),
    });
    if (response.status === 401) {
      await response.body?.cancel();
      return { message: "Invalid student key. Existing credentials were not changed.", type: "error" };
    }
    if (response.status !== 200) {
      await response.body?.cancel();
      return { message: "The server could not validate the key. Existing credentials were not changed.", type: "error" };
    }
    if (!/^application\/json(?:\s*;|$)/i.test(response.headers.get("content-type") ?? "")) {
      await response.body?.cancel();
      return { message: "Invalid login response from the server. Existing credentials were not changed.", type: "error" };
    }
    const data: unknown = await response.json();
    if (!data || typeof data !== "object" || !("username" in data) || typeof data.username !== "string" || !USERNAME.test(data.username)) {
      return { message: "Invalid login response from the server. Existing credentials were not changed.", type: "error" };
    }
    username = data.username;
  } catch {
    // Never display server bodies or exception strings: either can contain keys.
    return { message: "Login failed: server unreachable, request timed out, redirect refused, or invalid response. Existing credentials were not changed.", type: "error" };
  }

  try {
    const save = pendingSave.then(() => writeCredential(
      origin, key, username, options.credentialDir ?? join(homedir(), ".config", "agent-golf"),
    ));
    pendingSave = save.catch(() => {});
    await save;
  } catch {
    return { message: "Key validated, but credentials could not be saved securely. Existing credentials were not replaced.", type: "error" };
  }
  return { message: `Logged in as ${username} on ${origin}.`, type: "info" };
}
