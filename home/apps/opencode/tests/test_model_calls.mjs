import "./plugin-loader.mjs";
import assert from "node:assert/strict";
import { test } from "node:test";
import { mkdtemp, readFile, rm, stat, chmod, mkdir } from "node:fs/promises";
import { join } from "node:path";

test("per-attempt model journal: title/children/retries, HTTP headers, WS frames, privacy and disposal", async () => {
  const directory = await mkdtemp("/tmp/opencode/model-calls-");
  const previous = process.env.XDG_STATE_HOME;
  process.env.XDG_STATE_HOME = directory;
  try {
    const { default: plugin } = await import("../plugins/model-calls.ts");
    const hooks = new Map();
    let disposed = 0;
    const cleanup = await plugin.setup({ session: { async hook(name, fn) {
      hooks.set(name, fn);
      return { dispose: async () => { disposed++; hooks.delete(name); } };
    } } });
    const identity = { sessionID: "root", agent: "build", kind: "title",
      model: { providerID: "openai", id: "luna-alias", variant: "low" } };
    const request = () => new Request("http://localhost/private-url?secret=PRIVATE", {
      method: "POST", headers: { "content-type": "application/json", authorization: "Bearer PRIVATE" },
      body: JSON.stringify({ model: "gpt-6-luna", reasoning: { effort: "low" }, input: "PRIVATE", api_key: "PRIVATE" }),
    });
    const first = request();
    await hooks.get("http.request")({ ...identity, request: first });
    assert.equal((await first.clone().json()).input, "PRIVATE", "original body remains readable");
    const response = new Response("PRIVATE response", { status: 429 });
    await hooks.get("http.response")({ ...identity, request: first, response });
    assert.equal(await response.text(), "PRIVATE response", "response body not consumed");
    const second = request();
    await hooks.get("http.request")({ ...identity, request: second });
    await hooks.get("http.response")({ ...identity, request: second, response: new Response("", { status: 200 }) });
    await hooks.get("http.response")({ ...identity, request: second, response: new Response("", { status: 200 }) });
    // Failure before headers: attempt stays unknown; don't invent an error/completion.
    await hooks.get("http.request")({ ...identity, kind: "generate", request: request() });
    await hooks.get("experimental.ws.send")({ ...identity, sessionID: "child", kind: "primary", agent: "explore",
      frame: JSON.stringify({ type: "response.create", model: "gpt-6-luna", reasoning: { effort: "max" }, input: "PRIVATE" }) });
    await hooks.get("experimental.ws.send")({ ...identity, frame: '{"type":"ping","secret":"PRIVATE"}' });
    await hooks.get("experimental.ws.send")({ ...identity, frame: "not JSON PRIVATE" });
    const file = join(directory, "opencode/model-calls/root.jsonl");
    const text = await readFile(file, "utf8");
    const rows = text.trim().split("\n").map(JSON.parse);
    assert.equal(rows.length, 5);
    assert.equal(new Set(rows.filter(r => r.event === "attempt").map(r => r.id)).size, 3);
    assert.equal(rows[0].wireModel, "gpt-6-luna");
    assert.equal(rows[0].modelID, "luna-alias");
    assert.equal(rows[0].variant, "low");
    assert.equal(rows[1].id, rows[0].id);
    assert.equal(rows[1].status, 429);
    assert.equal(rows[3].status, 200);
    assert.equal(rows[4].kind, "generate");
    const child = await readFile(join(directory, "opencode/model-calls/child.jsonl"), "utf8");
    assert.equal(JSON.parse(child).effort, "max");
    assert.equal(JSON.parse(child).transport, "websocket");
    assert.ok(!(text + child).includes("PRIVATE"));
    assert.equal((await stat(file)).mode & 0o777, 0o600);
    assert.equal((await stat(join(directory, "opencode/model-calls"))).mode & 0o777, 0o700);
    await chmod(file, 0o644);
    await hooks.get("http.request")({ ...identity, request: request() });
    assert.equal((await stat(file)).mode & 0o777, 0o600, "tighten existing journals");
    await cleanup();
    assert.equal(disposed, 3);
    assert.equal(hooks.size, 0);
  } finally {
    previous === undefined ? delete process.env.XDG_STATE_HOME : process.env.XDG_STATE_HOME = previous;
    await rm(directory, { recursive: true });
  }
});

test("unknown/oversized bodies and unavailable storage never change/block the request", async () => {
  const directory = await mkdtemp("/tmp/opencode/model-calls-");
  const previous = process.env.XDG_STATE_HOME;
  process.env.XDG_STATE_HOME = directory;
  try {
    const { default: plugin } = await import("../plugins/model-calls.ts");
    const hooks = new Map();
    const cleanup = await plugin.setup({ session: { async hook(name, fn) {
      hooks.set(name, fn); return { dispose: async () => {} };
    } } });
    const event = { sessionID: "root", agent: "build", kind: "compaction", model: { providerID: "p", id: "m" } };
    for (const body of ["PRIVATE malformed", JSON.stringify({ model: "PRIVATE bad label", reasoning_effort: "high" }),
                        JSON.stringify({ model: "m", input: "x".repeat(9 * 1024 * 1024) })]) {
      const request = new Request("http://localhost/", { method: "POST", headers: { "content-type": "application/json" }, body });
      await hooks.get("http.request")({ ...event, request });
      assert.equal(await request.text(), body);
    }
    const rows = (await readFile(join(directory, "opencode/model-calls/root.jsonl"), "utf8")).trim().split("\n").map(JSON.parse);
    assert.equal(rows.length, 3);
    assert.ok(rows.every(r => r.wireModel === undefined));
    assert.equal(rows[1].effort, "high");
    // A directory at the journal path forces an append failure even as root.
    await mkdir(join(directory, "opencode/model-calls/blocked.jsonl"));
    await hooks.get("http.request")({ ...event, sessionID: "blocked", request: new Request("http://localhost/") });
    await cleanup();
  } finally {
    previous === undefined ? delete process.env.XDG_STATE_HOME : process.env.XDG_STATE_HOME = previous;
    await rm(directory, { recursive: true });
  }
});
