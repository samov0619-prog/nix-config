import "./plugin-loader.mjs";
import assert from "node:assert/strict";
import { test } from "node:test";
import { execFileSync } from "node:child_process";
const { default: plugin, offlineEnvironment } = await import("../git-offline.ts");

test("Git environment blocks transports and lazy fetch while preserving other settings", async () => {
  const env = { PATH: "/test", GIT_ALLOW_PROTOCOL: "https", GIT_NO_LAZY_FETCH: "0" };
  let hook, disposed = false;
  const cleanup = await plugin.setup({ shell: { hook: async (event, callback) => {
    assert.equal(event, "create.before"); hook = callback;
    return { dispose: () => { disposed = true; } };
  } } });
  hook({ env });
  assert.deepEqual(env, { PATH: "/test", GIT_ALLOW_PROTOCOL: "", GIT_NO_LAZY_FETCH: "1", GIT_TERMINAL_PROMPT: "0" });
  offlineEnvironment(env);
  cleanup();
  assert.ok(disposed);
});

test("native policies distinguish cached remote inspection from network commands", () => {
  const settings = JSON.parse(execFileSync("nix", ["eval", "--json", "--file",
    new URL("../v2-settings.nix", import.meta.url).pathname, "--apply", "f: f { lib = {}; }"]));
  const effect = command => settings.policies.filter(p => p.action === "tool.use" &&
    new RegExp("^" + p.resource.split("*").map(s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join(".*") + "$").test("shell:" + command)).at(-1)?.effect;
  for (const command of ["git fetch", "git -C /repo push origin main", "git -c color.ui=always pull", "git remote update", "git remote show origin", "git -C /repo remote show origin", "git remote set-head origin --auto", "git remote add -f upstream https://example.invalid/repo"])
    assert.equal(effect(command), "deny", command);
  for (const command of ["git remote show -n origin", "git -C /repo remote show origin -n"])
    assert.equal(effect(command), "allow", command);
  for (const command of ["git status", "git remote -v", "git remote get-url origin", "git remote add upstream https://example.invalid/repo"])
    assert.equal(effect(command), undefined, command);
});
