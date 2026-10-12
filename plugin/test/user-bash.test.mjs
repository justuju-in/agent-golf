import assert from "node:assert/strict";
import { test } from "node:test";
import { hasPendingUserBash, USER_BASH_START, userBashStartMetadata } from "../user-bash.ts";

const start = (command) => ({ type: "custom", customType: USER_BASH_START, data: userBashStartMetadata(command) });
const end = (command) => ({ type: "message", message: { role: "bashExecution", command, output: "done" } });

test("Bash marker stores only a hash, not a plaintext command", () => {
  const command = "echo disposable-secret";
  const marker = start(command);
  assert.equal(JSON.stringify(marker).includes(command), false);
  assert.equal(JSON.stringify(marker).includes("disposable-secret"), false);
  assert.equal(hasPendingUserBash([marker]), true);
});

test("recorded results release matching starts, including identical concurrent commands", () => {
  assert.equal(hasPendingUserBash([]), false);
  assert.equal(hasPendingUserBash([start("a"), end("a")]), false);
  assert.equal(hasPendingUserBash([start("a"), start("a"), end("a")]), true);
  assert.equal(hasPendingUserBash([start("a"), start("a"), end("a"), end("a")]), false);
  assert.equal(hasPendingUserBash([start("a"), start("b"), end("b")]), true);
  assert.equal(hasPendingUserBash([start("a"), start("b"), end("b"), end("a")]), false);
});

test("historical or unrelated results cannot complete a later command", () => {
  assert.equal(hasPendingUserBash([end("a"), start("a")]), true);
  assert.equal(hasPendingUserBash([start("a"), end("b")]), true);
});

test("pending state can be reconstructed after reload from full append-order entries", () => {
  const entries = [start("a"), start("b"), end("b")];
  assert.equal(hasPendingUserBash(JSON.parse(JSON.stringify(entries))), true);
  assert.equal(hasPendingUserBash([...entries, end("a")]), false);
});

test("malformed Bash markers fail closed", () => {
  assert.equal(hasPendingUserBash([{ type: "custom", customType: USER_BASH_START, data: null }]), true);
  assert.equal(hasPendingUserBash([{ type: "custom", customType: USER_BASH_START, data: { schema: 1, command_sha256: "invalid" } }]), true);
});
