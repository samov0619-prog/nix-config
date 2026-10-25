import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, existsSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { mock, test } from "node:test";
import plugin from "../workspace-context.ts";

test("publishes viewed session, full Unicode title, route changes and cleanup", async () => {
  const runtime = mkdtempSync(join(tmpdir(), "workspace-context-"));
  const oldRuntime = process.env.XDG_RUNTIME_DIR, oldPane = process.env.KITTY_WINDOW_ID;
  process.env.XDG_RUNTIME_DIR = runtime;
  process.env.KITTY_WINDOW_ID = "42";
  let tick, dispose;
  const timer = mock.method(globalThis, "setInterval", (callback) => {
    tick = callback;
    return { unref() {} };
  });
  const clear = mock.method(globalThis, "clearInterval", () => {});
  try {
    const titles = { one: "Название сессии без усечения — кириллица", two: "Другая сессия" };
    const api = {
      route: { current: { name: "session", params: { sessionID: "one" } } },
      state: { path: { directory: "/fallback" }, session: { get: (id) => ({
        title: titles[id],
        directory: `/${id}`,
      }) } },
      lifecycle: { onDispose: (callback) => { dispose = callback; } },
    };
    await plugin.tui(api);
    const path = join(runtime, "hypr-spaces/apps", `${process.pid}.json`);
    const read = () => JSON.parse(readFileSync(path));
    assert.equal(read().title, "Название сессии без усечения — кириллица");
    assert.equal(read().pane, "42");
    assert.match(read().start, /^\d+$/);
    titles.one = "Переименованная сессия";
    tick();
    assert.equal(read().title, "Переименованная сессия");
    titles.one = "New session - 2026-10-23T10:19:12.809Z";
    tick();
    assert.equal(read().title, titles.one); // Default titles are real session names too.
    api.route.current.params.sessionID = "two";
    tick();
    assert.equal(read().title, "Другая сессия");
    assert.equal(read().cwd, "/two");
    api.route.current = { name: "home" };
    tick();
    assert.equal(read().title, "");
    assert.equal(read().cwd, "/fallback");
    dispose();
    assert.equal(existsSync(path), false);
    assert.equal(clear.mock.callCount(), 1);
  } finally {
    timer.mock.restore(); clear.mock.restore();
    if (oldRuntime === undefined) delete process.env.XDG_RUNTIME_DIR; else process.env.XDG_RUNTIME_DIR = oldRuntime;
    if (oldPane === undefined) delete process.env.KITTY_WINDOW_ID; else process.env.KITTY_WINDOW_ID = oldPane;
    rmSync(runtime, { recursive: true, force: true });
  }
});
