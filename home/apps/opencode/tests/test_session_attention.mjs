import "./attention-loader.mjs";
import assert from "node:assert/strict";
import { execFileSync, fork } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, rmSync } from "node:fs";
import fs from "node:fs/promises";
import { syncBuiltinESMExports } from "node:module";
import { join } from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
import { mock, test, after } from "node:test";
import { sessionAttention, trackSessionAttention } from "../patches/session-attention.ts";

const source = fileURLToPath(new URL("..", import.meta.url));
const directory = mkdtempSync("/tmp/opencode/attention-policy-");
const previousRuntime = process.env.XDG_RUNTIME_DIR;
process.env.XDG_RUNTIME_DIR = directory;
after(() => {
  previousRuntime === undefined ? delete process.env.XDG_RUNTIME_DIR : process.env.XDG_RUNTIME_DIR = previousRuntime;
  rmSync(directory, { recursive: true, force: true });
});
const sessions = { a: {}, b: {}, ac: { parentID: "a" }, ag: { parentID: "ac" }, bc: { parentID: "b" }, missing: { parentID: "absent" }, cycle: { parentID: "cycle" } };
let sequence = 0;
const event = () => ({ id: `event-${++sequence}` });
function harness(sessionID) {
  const handlers = new Map(), focus = new Set(), attention = [], toasts = [];
  const context = {
    route: sessionID ? { type: "session", sessionID } : { type: "home" },
    tabs: ["a", "b"],
    tabsEnabled: true,
    renderer: { on: (_, fn) => focus.add(fn), off: (_, fn) => focus.delete(fn) },
    ui: {
      router: { current: () => context.route },
      tabs: { enabled: () => context.tabsEnabled, list: () => context.tabs.map(sessionID => ({ sessionID })) },
      toast: { show: value => toasts.push(value) },
    },
    attention: { notify: async value => { attention.push(value); return { ok: true }; } },
    data: { session: { get: id => sessions[id] }, on: (type, fn) => {
      if (!handlers.has(type)) handlers.set(type, new Set());
      const listeners = handlers.get(type); listeners.add(fn);
      return () => { listeners.delete(fn); if (!listeners.size) handlers.delete(type); };
    } },
  };
  const tracking = trackSessionAttention(context);
  tracking.update();
  return {
    context, attention, toasts, handlers, tracking,
    select(id) { context.route = id ? { type: "session", sessionID: id } : { type: "home" }; tracking.update(true); },
    allowed(id, e = event(), channel = "native") { return sessionAttention(context, id, e, channel); },
    emit(type, sessionID, extra = {}, e = event()) { for (const fn of handlers.get(type) ?? []) fn({ ...e, type, data: { sessionID, ...extra } }); return e; },
  };
}

test("background tabs/children and home retain ownership; shared tabs alone never claim", () => {
  const a = harness("a"), b = harness("b"), home = harness();
  a.select("b"); // Explicit selection transfers b; a remains owned in the background.
  assert.equal(a.allowed("a"), true);
  assert.equal(a.allowed("ag"), true);
  assert.equal(b.allowed("b"), false);
  assert.equal(home.allowed("a"), false);
  a.select();
  assert.equal(a.allowed("a"), true);
  for (const id of [undefined, "missing", "absent", "cycle", "global"]) assert.equal(a.allowed(id), false);
  a.context.tabs = ["b"];
  a.tracking.update();
  assert.equal(a.allowed("a"), false, "closed tabs release ownership");
  [a,b,home].forEach(x => x.tracking.dispose());
});

test("one frozen event owner, separate once-only channels, transfer, reload and fallback", () => {
  const a = harness("a"), b = harness("b");
  const e = event();
  assert.equal(a.allowed("a", e), true);
  b.select("a");
  assert.equal(b.allowed("a", e, "urgency"), false, "transfer cannot split an existing event");
  assert.equal(a.allowed("a", e, "urgency"), true);
  assert.equal(a.allowed("a", e), false, "native replay suppressed");
  assert.equal(a.allowed("a", e, "urgency"), false, "urgency replay suppressed");
  assert.equal(b.allowed("a"), true);
  const reload = trackSessionAttention(b.context);
  b.tracking.dispose(); reload.update();
  assert.equal(b.allowed("a"), true, "one consumer reload does not release another");
  reload.dispose();
  assert.equal(a.allowed("a"), true, "closing the owner falls back to a surviving opener");
  a.tracking.dispose();
});

test("delayed ancestry never overtakes a later selection; disabled tabs retain only current family", () => {
  const old = harness("late"), recent = harness("late");
  sessions.late = {};
  recent.tracking.update();
  old.tracking.update();
  const e = event();
  assert.equal(old.allowed("late", e), false);
  assert.equal(recent.allowed("late", e), true);
  old.tracking.dispose(); recent.tracking.dispose(); delete sessions.late;
  const a = harness("a");
  a.context.tabsEnabled = false;
  a.select("b");
  assert.equal(a.allowed("a"), false);
  assert.equal(a.allowed("bc"), true);
  a.select();
  assert.equal(a.allowed("b"), false);
  a.tracking.dispose();
});

test("bundled/plugin helper copies share one renderer lifecycle; stale PID incarnation cannot win", async () => {
  const copy = join(directory, "second-helper.ts");
  copyFileSync(join(source, "patches/session-attention.ts"), copy);
  const other = await import(pathToFileURL(copy));
  const a = harness("a");
  const registration = other.trackSessionAttention(a.context);
  registration.update();
  a.tracking.dispose();
  const clients = join(directory, "opencode-attention-v2/clients");
  const stale = join(clients, `${process.pid}-0-aaaa.json`);
  await fs.writeFile(stale, JSON.stringify({pid:process.pid,start:"0",token:"stale",roots:{a:"999999999999999999999999"}}));
  const e = event();
  assert.equal(other.sessionAttention(a.context,"a",e,"native"), true);
  assert.equal(a.allowed("a",e), false, "receipts shared across helper module copies");
  assert.equal(a.allowed("a",e,"urgency"), true);
  registration.dispose();
  await fs.unlink(stale);
});

test("actual patched notification code: lifecycle, errors, forms, permissions and silent urgency", async () => {
  const temporary = mkdtempSync("/tmp/opencode/scoped-native-");
  const oldPane = process.env.KITTY_WINDOW_ID;
  process.env.KITTY_WINDOW_ID = "42";
  const packets = [];
  const mocked = mock.method(fs, "open", async path => {
    assert.equal(path, "/dev/tty");
    return { write: async value => packets.push(value), close: async () => {} };
  });
  syncBuiltinESMExports();
  try {
    const upstream = process.env.OPENCODE_TEST_SOURCE ?? execFileSync("nix", ["eval", "--offline", "--raw", "path:.#packages.x86_64-linux.opencode.src"], { encoding: "utf8" }).trim();
    const relative = "packages/tui/src/feature-plugins/system/notifications.ts";
    mkdirSync(join(temporary, "packages/tui/src/feature-plugins/system"), { recursive: true });
    copyFileSync(join(upstream, relative), join(temporary, relative));
    execFileSync("patch", ["--batch", "--fuzz=0", "-s", "-p1", "-i", join(source, "patches/session-attention.patch")], { cwd: temporary });
    const { default: native } = await import(pathToFileURL(join(temporary, relative)));
    const packaged = process.env.OPENCODE_TEST_QUIET_URGENCY_PLUGIN;
    const { default: urgency } = await import(packaged ? pathToFileURL(join(packaged, "tui.ts")) : "../plugins/quiet-urgency.ts");
    const a = harness("a"), b = harness("b");
    const cleanup = [native.setup(a.context), native.setup(b.context), urgency.setup(a.context), urgency.setup(b.context)];
    a.select("b");
    const emit = (type, sid, extra) => { const e = event(); [a,b].forEach(x => x.emit(type, sid, extra, e)); };
    emit("session.execution.started", "a"); emit("session.execution.succeeded", "a");
    emit("session.execution.succeeded", "a");
    assert.deepEqual(a.attention.map(x => x.sound.name), ["done"]);
    assert.equal(b.attention.length, 0);
    emit("session.execution.started", "ac"); emit("session.execution.succeeded", "ac");
    emit("permission.asked", "a", { id: "p1" }); emit("permission.asked", "a", { id: "p1" });
    emit("form.created", "a", { form: { id: "f1", sessionID: "a" } });
    emit("form.created", undefined, { form: { id: "global" } });
    emit("session.execution.started", "a");
    emit("session.execution.failed", "a", { error: { type: "unknown", message: "fixture error" } });
    assert.deepEqual(a.attention.map(x => x.sound.name), ["done", "subagent_done", "permission", "question", "error"]);
    assert.equal(a.toasts.length, 1); assert.equal(b.toasts.length, 0);
    await new Promise(resolve => setImmediate(resolve));
    assert.ok(packets.length >= 5);
    assert.ok(packets.every(x => x.startsWith("\x1bP@kitty-cmd") && !x.includes("\x07")));
    cleanup.forEach(stop => stop());
    [a,b].forEach(x => { x.tracking.dispose(); assert.equal(x.handlers.size, 0); });
  } finally {
    mocked.mock.restore(); syncBuiltinESMExports();
    oldPane === undefined ? delete process.env.KITTY_WINDOW_ID : process.env.KITTY_WINDOW_ID = oldPane;
    rmSync(temporary, { recursive: true, force: true });
  }
});

test("two real Linux processes arbitrate one event and recover after abrupt owner exit", async () => {
  const worker = `
    import {sessionAttention,trackSessionAttention} from ${JSON.stringify(pathToFileURL(join(source,"patches/session-attention.ts")).href)};
    const context={renderer:{},ui:{router:{current:()=>({type:'session',sessionID:'process-session'})},tabs:{enabled:()=>true,list:()=>[{sessionID:'process-session'}]}},data:{session:{get:()=>({})}}};
    const track=trackSessionAttention(context);track.update();
    process.on('message',m=>{if(m.select)track.update(true);process.send({ok:m.select?true:sessionAttention(context,'process-session',{id:m.id},m.channel)});});
    process.send({ready:true});
  `;
  const launch = () => fork("--eval", [worker], { execArgv: ["--input-type=module"], stdio: ["ignore","ignore","inherit","ipc"] });
  const ready = child => new Promise(resolve => child.once("message", resolve));
  const ask = (child, message) => new Promise(resolve => { child.once("message", resolve); child.send(message); });
  const a = launch(); await ready(a);
  const b = launch(); await ready(b);
  try {
    const e = event().id;
    const result = await Promise.all([ask(a,{id:e,channel:"native"}),ask(b,{id:e,channel:"native"})]);
    assert.deepEqual(result.map(x=>x.ok),[false,true]);
    await ask(a,{select:true});
    assert.equal((await ask(a,{id:e,channel:"urgency"})).ok,false);
    assert.equal((await ask(b,{id:e,channel:"urgency"})).ok,true);
    const exited = new Promise(resolve=>a.once("exit",resolve)); a.kill("SIGKILL"); await exited;
    assert.equal((await ask(b,{id:event().id,channel:"native"})).ok,true);
  } finally { a.kill(); b.kill(); }
});
