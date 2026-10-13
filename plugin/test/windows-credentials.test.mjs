import assert from "node:assert/strict";
import { chmod, mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";
import { readStoredCredential } from "../login.ts";

const ORIGIN = "https://agent-golf.example";
const CREDENTIAL = { key: "00000000-0000-4000-8000-000000000001", username: "student_1" };

// Windows reports 0o777 folders and 0o666 files whatever chmod did; reproduce those modes here.
async function windowsLikeModes(t) {
  const directory = await mkdtemp(join(tmpdir(), "golf-windows-credentials-"));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const folder = join(directory, "agent-golf");
  await mkdir(folder);
  await chmod(folder, 0o777);
  const file = join(folder, "credentials.json");
  await writeFile(file, JSON.stringify({ schema: 1, credentials: { [ORIGIN]: CREDENTIAL } }) + "\n");
  await chmod(file, 0o666);
  return folder;
}

test("on Windows, credentials are read even though Node reports group/other permission bits", async (t) => {
  const folder = await windowsLikeModes(t);
  assert.deepEqual(await readStoredCredential(ORIGIN, folder, "win32"), CREDENTIAL);
});

test("elsewhere, a credential folder or file readable by others is still refused", async (t) => {
  const folder = await windowsLikeModes(t);
  for (const platform of ["linux", "darwin"]) {
    await assert.rejects(readStoredCredential(ORIGIN, folder, platform), /insecure-credential-directory/);
  }
  await chmod(folder, 0o700);
  await assert.rejects(readStoredCredential(ORIGIN, folder, "linux"), /insecure-credential-file/);
});
