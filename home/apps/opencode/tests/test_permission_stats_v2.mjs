import "./plugin-loader.mjs";
import assert from "node:assert/strict";
import { test } from "node:test";
import { mkdtemp, readFile, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

test("V2 permission stream correlates requests, preserves legacy fields, ignores duplicates and aborts", async () => {
  const directory = await mkdtemp(join(tmpdir(), "permission-v2-"));
  const previous = process.env.XDG_STATE_HOME;
  process.env.XDG_STATE_HOME = directory;
  try {
    const { default: plugin } = await import("../plugins/permission-stats.ts");
    let aborted = false;
    const cleanup = plugin.setup({ event: { async *subscribe({ signal }) {
      yield { type: "permission.asked", data: { id: "request", sessionID: "session", action: "shell", resources: ["date"] } };
      yield { type: "permission.replied", data: { requestID: "missing", reply: "once" } };
      yield { type: "permission.replied", data: { requestID: "request", reply: "always" } };
      yield { type: "permission.replied", data: { requestID: "request", reply: "always" } };
      await new Promise(resolve => signal.addEventListener("abort", () => { aborted = true; resolve(); }, { once: true }));
    } } });
    const file = join(directory, "opencode/permission-history.jsonl");
    let records;
    for (let n = 0; n < 50; n++) {
      try { records = (await readFile(file, "utf8")).trim().split("\n").map(JSON.parse); if (records[0]) break; } catch {}
      await new Promise(resolve => setTimeout(resolve, 5));
    }
    assert.equal(records.length, 1);
    assert.deepEqual({ ...records[0], time: undefined }, {
      time: undefined, permission: "shell", patterns: ["date"], response: "always", sessionID: "session", requestID: "request",
    });
    assert.equal((await stat(file)).mode & 0o777, 0o600);
    await new Promise(resolve => setImmediate(resolve));
    cleanup();
    assert.ok(aborted);
  } finally {
    previous === undefined ? delete process.env.XDG_STATE_HOME : process.env.XDG_STATE_HOME = previous;
    await rm(directory, { recursive: true });
  }
});
