// Policy coverage of the actual patched startup block, not a TUI/terminal test.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const upstream = process.env.OPENCODE_TEST_SOURCE ?? execFileSync("nix", [
  "eval", "--impure", "--offline", "--raw",
  "--option", "allow-import-from-derivation", "false",
  "--expr", "(builtins.getFlake (toString ./.)).inputs.opencode.outPath",
], { encoding: "utf8" }).trim();
const directory = mkdtempSync("/tmp/opencode/theme-policy-");
let block;
try {
  const relative = "packages/tui/src/context/theme.tsx";
  mkdirSync(join(directory, "packages/tui/src/context"), { recursive: true });
  copyFileSync(join(upstream, relative), join(directory, relative));
  execFileSync("patch", ["--batch", "-s", "-p1", "-i",
    join(root, "patches/theme-mode-cache.patch")], { cwd: directory });
  const source = readFileSync(join(directory, relative), "utf8");
  const start = source.indexOf("    if (palette) {");
  const end = source.indexOf("    } else setSystemTheme(undefined)", start);
  assert.ok(start > 0 && end > start, "Review changed upstream startup layout");
  block = new Function("store", "renderer", "palette", "terminalMode", "setStore", "applyPalette",
    source.slice(start + "    if (palette) {".length, end));
} finally {
  rmSync(directory, { recursive: true, force: true });
}

function startup({ live, cached, lock, previous = "dark" }) {
  const store = { mode: previous, lock };
  let paletteMode;
  block(store, { themeMode: live }, {}, () => cached,
    (key, value) => { store[key] = value; },
    () => { paletteMode = store.mode; });
  assert.equal(paletteMode, store.mode, "Cached palette must use the selected mode");
  return store.mode;
}

test("fresh terminal appearance beats a stale opposite-mode palette in both directions", () => {
  assert.equal(startup({ live: "light", cached: "dark" }), "light");
  assert.equal(startup({ live: "dark", cached: "light" }), "dark");
});

test("explicit user mode wins over both terminal and cache", () => {
  assert.equal(startup({ lock: "dark", live: "light", cached: "light" }), "dark");
  assert.equal(startup({ lock: "light", live: "dark", cached: "dark" }), "light");
});

test("cached appearance remains a fallback when terminal detection is unavailable", () => {
  assert.equal(startup({ live: null, cached: "light" }), "light");
  assert.equal(startup({ live: null, cached: "dark", previous: "light" }), "dark");
});

test("no live or cached appearance preserves the existing fallback", () => {
  assert.equal(startup({ live: null, cached: undefined, previous: "light" }), "light");
  assert.equal(startup({ live: null, cached: undefined }), "dark");
});
