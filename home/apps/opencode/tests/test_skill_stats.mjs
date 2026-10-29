import "./plugin-loader.mjs";
import assert from "node:assert/strict";
import { test } from "node:test";
const { default: plugin } = await import("../plugins/skill-stats.ts");

function fixture(storage = new Map()) {
  const hooks = new Map();
  const histories = new Map();
  let reads = 0;
  const context = {
    storage: { get: async key => storage.get(key), set: async (key, value) => storage.set(key, structuredClone(value)) },
    session: { context: async ({ sessionID }) => { reads++; return histories.get(sessionID) ?? []; } },
    tool: { hook: async (name, fn) => {
      hooks.set(name, fn); return { dispose: async () => hooks.delete(name) };
    } },
  };
  return { context, hooks, histories, storage, reads: () => reads };
}

const user = (id, text) => ({ type: "user", id, text });
const assistant = id => ({ type: "assistant", id, model: { providerID: "openai", id: "model", variant: "high" } });
const call = (extra = {}) => ({ tool: "skill", input: { id: "discussion-map" }, sessionID: "root",
  messageID: "answer", id: "call-1", agent: "build", status: "completed", result: { content: "PRIVATE OUTPUT" }, ...extra });

test("one native hook: query before calling assistant, not later steering, with per-session isolation", async () => {
  const f = fixture();
  f.histories.set("root", [user("old", "old query"), assistant("old-answer"), user("query", "root query"),
    assistant("answer"), user("steering", "not yet used by this assistant")]);
  f.histories.set("child", [user("child-query", "child query"), assistant("child-answer")]);
  const cleanup = await plugin.setup(f.context);
  assert.deepEqual([...f.hooks.keys()], ["execute.after"]);
  const after = f.hooks.get("execute.after");
  await after(call({ tool: "read" }));
  assert.equal(f.reads(), 0, "unrelated tools do no work");
  await after(call());
  await after(call({ sessionID: "child", messageID: "child-answer", agent: "general" }));
  const [root, child] = [...f.storage.values()];
  assert.equal(root.queryID, "query");
  assert.equal(root.lastQuery, "root query");
  assert.equal(child.queryID, "child-query");
  assert.equal(child.lastQuery, "child query");
  assert.equal(child.agent, "general");
  assert.deepEqual(root.model, assistant("answer").model);
  assert.ok(!JSON.stringify([...f.storage.values()]).includes("PRIVATE OUTPUT"));
  await cleanup();
  assert.equal(f.hooks.size, 0);
});

test("stable call keys deduplicate concurrent callbacks and survive plugin reload; repeated real calls count", async () => {
  const f = fixture();
  f.histories.set("root", [user("query", "query"), assistant("answer")]);
  const cleanup = await plugin.setup(f.context);
  await Promise.all([f.hooks.get("execute.after")(call()), f.hooks.get("execute.after")(call())]);
  assert.equal(f.storage.size, 1);
  const saved = structuredClone([...f.storage.values()][0]);
  await cleanup();
  const reopened = fixture(f.storage);
  const close = await plugin.setup(reopened.context);
  await reopened.hooks.get("execute.after")(call());
  assert.deepEqual([...f.storage.values()][0], saved);
  assert.equal(reopened.reads(), 0);
  await reopened.hooks.get("execute.after")(call({ id: "call-2" }));
  assert.equal(f.storage.size, 2);
  await reopened.hooks.get("execute.after")(call({ messageID: "next-answer" }));
  assert.equal(f.storage.size, 3, "provider call IDs may be reused in a different assistant message");
  await close();
});

test("unknown boundaries/compacted queries stay unknown; failures are counted without storing error contents", async () => {
  const f = fixture();
  f.histories.set("root", [user("query", "not attributable without assistant boundary")]);
  await plugin.setup(f.context);
  await f.hooks.get("execute.after")(call({ status: "error", error: { message: "PRIVATE ERROR" } }));
  const row = [...f.storage.values()][0];
  assert.equal(row.queryID, null);
  assert.equal(row.lastQuery, null);
  assert.equal(row.model, null);
  assert.equal(row.status, "error");
  assert.ok(!JSON.stringify(row).includes("PRIVATE ERROR"));
  f.histories.set("root", [{ type: "compaction", id: "compaction" }, assistant("answer")]);
  await f.hooks.get("execute.after")(call({ id: "call-2" }));
  assert.equal([...f.storage.values()][1].queryID, null);
  await f.hooks.get("execute.after")(call({ input: null }));
  assert.equal(f.storage.size, 2);
});

test("lookup and storage failures never fail the skill or leak error text", async () => {
  const warnings = [];
  const previous = console.warn;
  console.warn = text => warnings.push(text);
  try {
    const f = fixture();
    f.context.session.context = async () => { throw Error("PRIVATE LOOKUP"); };
    await plugin.setup(f.context);
    await f.hooks.get("execute.after")(call());
    assert.equal([...f.storage.values()][0].queryID, null);
    f.context.storage.set = async () => { throw Error("PRIVATE STORAGE"); };
    await f.hooks.get("execute.after")(call({ id: "call-2" }));
    f.context.storage.get = async () => { throw Error("PRIVATE STORAGE"); };
    await f.hooks.get("execute.after")(call({ id: "call-3" }));
    assert.equal(warnings.length, 1);
    assert.ok(!warnings[0].includes("PRIVATE"));
  } finally { console.warn = previous; }
});
