import "./plugin-loader.mjs";
import assert from "node:assert/strict";
import { test } from "node:test";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
const { setup } = await import("../macos/opencode/plugins/voice/tui.ts");

async function fixture() {
  const directory = await mkdtemp(join(tmpdir(), "voice-v2-"));
  const previous = process.env.OPENCODE_CONFIG_DIR;
  process.env.OPENCODE_CONFIG_DIR = directory;
  let commands;
  let route = { type: "session", sessionID: "one" };
  const inserted = [], dialogs = [], notifications = [];
  const input = { plainText: "Draft", insertText: text => inserted.push(text) };
  const context = {
    renderer: { currentFocusedRenderable: input },
    ui: { router: { current: () => route }, toast: { show: value => notifications.push(value) },
          dialog: { prompt: async value => { dialogs.push(value); } } },
    keymap: { layer: factory => { commands = factory().commands; } },
  };
  let resolve, cancelled = 0, recording = 0;
  const runtime = { record: () => { recording++; return new Promise(r => { resolve = r; }); },
                    stop: () => resolve("Hello locally"), cancel: () => { cancelled++; resolve?.("Late result"); } };
  const cleanup = setup(context, runtime);
  for (let n = 0; !commands && n < 30; n++) await new Promise(r => setTimeout(r, 5));
  assert.ok(commands);
  return { context, inserted, dialogs, notifications, runtime, commands,
    changeRoute: () => { route = { type: "session", sessionID: "two" }; },
    recording: () => recording, cancelled: () => cancelled,
    close: async () => { cleanup(); previous === undefined ? delete process.env.OPENCODE_CONFIG_DIR : process.env.OPENCODE_CONFIG_DIR = previous; await rm(directory, { recursive: true }); } };
}

test("native local voice toggles, inserts reviewed text and never submits", async () => {
  const f = await fixture();
  try {
    const pending = f.commands[0].run();
    await new Promise(r => setImmediate(r));
    await f.commands[0].run();
    await pending;
    assert.equal(f.commands[0].bind, "ctrl+r");
    assert.deepEqual(f.inserted, ["Hello locally "]);
    assert.equal(f.recording(), 1);
  } finally { await f.close(); }
});

test("route changes preserve transcription without inserting into another session", async () => {
  const f = await fixture();
  try {
    const pending = f.commands[0].run();
    await new Promise(r => setImmediate(r));
    f.changeRoute();
    await f.commands[0].run();
    await pending;
    assert.deepEqual(f.inserted, []);
    assert.equal(f.dialogs[0].value, "Hello locally");
  } finally { await f.close(); }
});

test("cancel/dispose discard late transcription and stop the runtime", async () => {
  const f = await fixture();
  try {
    const pending = f.commands[0].run();
    await new Promise(r => setImmediate(r));
    f.commands[2].run();
    await pending;
    assert.deepEqual(f.inserted, []);
    assert.equal(f.cancelled(), 1);
  } finally { await f.close(); }
});
