import "./plugin-loader.mjs";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { syncBuiltinESMExports } from "node:module";
import fs from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
import { mock, test } from "node:test";
import { sessionAttention } from "../patches/session-attention.ts";

const source = fileURLToPath(new URL("..", import.meta.url));
const sessions = {
  a: {}, b: {},
  ac: { parentID: "a" }, ag: { parentID: "ac" }, bc: { parentID: "b" },
  missing: { parentID: "absent" }, cycle: { parentID: "cycle2" }, cycle2: { parentID: "cycle" },
};
function harness(sessionID) {
  const handlers = new Map();
  const attention = [], toasts = [];
  const context = {
    route: sessionID ? { type: "session", sessionID } : { type: "home" },
    ui: { router: { current: () => context.route }, toast: { show: value => toasts.push(value) } },
    attention: { notify: async value => { attention.push(value); return { ok: true }; } },
    data: {
      session: { get: id => sessions[id] },
      on: (type, fn) => {
        handlers.set(type, fn);
        return () => handlers.delete(type);
      },
    },
  };
  return { context, attention, toasts, handlers, emit(type, sessionID, extra = {}) {
    handlers.get(type)?.({ type, data: { sessionID, ...extra } });
  } };
}

test("ownership is the live viewed session/descendants, never global tabs, cwd, home or unknown ancestry", () => {
  const { context } = harness("a");
  for (const id of ["a", "ac", "ag"]) assert.equal(sessionAttention(context, id), true, id);
  for (const id of ["b", "bc", "missing", "absent", "cycle", "global", undefined]) assert.equal(sessionAttention(context, id), false, id);
  context.route.sessionID = "ac";
  assert.equal(sessionAttention(context, "ag"), true);
  assert.equal(sessionAttention(context, "a"), false, "parent is not the child window's session");
  context.route = { type: "home" };
  assert.equal(sessionAttention(context, "a"), false);
  context.route = { type: "plugin", name: "dashboard" };
  assert.equal(sessionAttention(context, "a"), false);
});

test("the actual patched native notification plugin isolates two clients, lifecycle/errors/forms/permissions and route switches", async () => {
  const directory = mkdtempSync("/tmp/opencode/scoped-native-");
  try {
    const upstream = process.env.OPENCODE_TEST_SOURCE ?? execFileSync("nix", ["eval", "--offline", "--raw",
      "path:.#packages.x86_64-linux.opencode.src"], { encoding: "utf8" }).trim();
    const relative = "packages/tui/src/feature-plugins/system/notifications.ts";
    mkdirSync(join(directory, "packages/tui/src/feature-plugins/system"), { recursive: true });
    copyFileSync(join(upstream, relative), join(directory, relative));
    execFileSync("patch", ["--batch", "-s", "-p1", "-i", join(source, "patches/session-attention.patch")], { cwd: directory });
    const { default: native } = await import(pathToFileURL(join(directory, relative)));
    const a = harness("a"), b = harness("b"), home = harness();
    const clients = [a, b, home];
    const cleanup = clients.map(client => native.setup(client.context));
    const emit = (type, sessionID, extra) => clients.forEach(client => client.emit(type, sessionID, extra));
    emit("session.execution.started", "a");
    emit("session.execution.succeeded", "a");
    emit("session.execution.succeeded", "a");
    assert.equal(a.attention.length, 1);
    assert.equal(a.attention[0].sound.name, "done");
    assert.equal(b.attention.length, 0);
    assert.equal(home.attention.length, 0);
    emit("session.execution.started", "ac");
    emit("session.execution.succeeded", "ac");
    assert.equal(a.attention.at(-1).sound.name, "subagent_done");
    emit("session.execution.started", "bc");
    emit("session.execution.failed", "bc", { error: { type: "unknown", message: "fixture error" } });
    emit("session.execution.succeeded", "bc");
    assert.equal(b.attention.length, 1);
    assert.equal(b.attention[0].sound.name, "error");
    assert.equal(b.toasts.length, 1);
    assert.equal(a.toasts.length, 0);
    emit("permission.asked", "a", { id: "p1" });
    emit("permission.asked", "a", { id: "p1" });
    emit("form.created", "a", { form: { id: "f1", sessionID: "a", title: "Confirm" } });
    emit("form.created", "global", { form: { id: "global", sessionID: "global" } });
    assert.deepEqual(a.attention.map(value => value.sound.name), ["done", "subagent_done", "permission", "question"]);
    assert.equal(b.attention.length, 1);
    assert.equal(home.attention.length, 0);
    a.context.route = { type: "session", sessionID: "b" };
    emit("session.execution.started", "a");
    emit("session.execution.interrupted", "a");
    assert.equal(a.attention.length, 4, "no stale ownership after navigation");
    b.context.route = { type: "home" };
    emit("session.execution.started", "b");
    emit("session.execution.succeeded", "b");
    assert.equal(a.attention.length, 5);
    assert.equal(b.attention.length, 1);
    cleanup.forEach(dispose => dispose());
    assert.ok(clients.every(client => client.handlers.size === 0));
  } finally { rmSync(directory, { recursive: true }); }
});

test("silent Kitty urgency follows the same ownership policy, never calls an audio player/BEL and disposes", async () => {
  const previous = process.env.KITTY_WINDOW_ID;
  process.env.KITTY_WINDOW_ID = "42";
  const packets = [];
  const mocked = mock.method(fs, "open", async (path, flags) => {
    assert.equal(path, "/dev/tty");
    return { write: async value => packets.push(value), close: async () => {} };
  });
  syncBuiltinESMExports();
  try {
    const { default: urgency } = await import("../plugins/quiet-urgency.ts");
    const { context, emit, handlers } = harness("a");
    const dispose = urgency.setup(context);
    emit("session.execution.succeeded", "b");
    emit("permission.asked", "bc");
    emit("form.created", "global", { form: { sessionID: "global" } });
    assert.equal(packets.length, 0);
    emit("session.execution.succeeded", "a");
    emit("session.execution.failed", "ac");
    emit("form.created", "a", { form: { sessionID: "a" } });
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(packets.length, 3);
    assert.ok(packets.every(value => value.startsWith("\x1bP@kitty-cmd") && !value.includes("\x07")));
    context.route = { type: "home" };
    emit("session.execution.succeeded", "a");
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(packets.length, 3);
    dispose();
    assert.equal(handlers.size, 0);
  } finally {
    mocked.mock.restore(); syncBuiltinESMExports();
    previous === undefined ? delete process.env.KITTY_WINDOW_ID : process.env.KITTY_WINDOW_ID = previous;
  }
});
