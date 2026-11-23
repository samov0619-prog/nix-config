// Lightweight module evaluation/source guards; no realization or model calls.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const modulePath = fileURLToPath(new URL("../todo.nix", import.meta.url));
const evaluated = JSON.parse(
  execFileSync(
    "nix",
    [
      "eval",
      "--offline",
      "--impure",
      "--json",
      "--expr",
      `
    let
      lib = {
        mkIf = condition: value: if condition then value else {};
        mkEnableOption = description: { inherit description; };
        mkRemovedOptionModule = path: message: { inherit path message; };
      };
      evaluate = enabled: import ${JSON.stringify(modulePath)} {
        inherit lib;
        config.programs.opencode.todo.enable = enabled;
        config.home.homeDirectory = "/home/fixture";
        pkgs.git = "fixture-git";
        pkgs.runCommand = name: attrs: script: { inherit name script; };
      };
    in map evaluate [ false true ]`,
    ],
    { encoding: "utf8", timeout: 10000 },
  ),
);
const disabled = evaluated[0].config;
const enabled = evaluated[1].config;
const settings = JSON.parse(
  execFileSync(
    "nix",
    [
      "eval",
      "--offline",
      "--json",
      "--file",
      fileURLToPath(new URL("../config/todo-settings.nix", import.meta.url)),
      "--apply",
      'f: f { todoDirectory = "/home/fixture/agent-todo"; }',
    ],
    { timeout: 10000 },
  ),
);

test("notes opt-in is independent of archived guidance and has no ambient instructions or skills", () => {
  assert.deepEqual(disabled, {});
  assert.equal("instructions" in settings, false);
  assert.equal("skills" in enabled.programs.opencode, false);
  assert.equal("settings" in enabled.programs.opencode, false);
  assert.deepEqual(Object.keys(enabled.xdg.configFile), [
    "opencode-local/plugins/agent-todo",
  ]);
  assert.match(
    enabled.xdg.configFile["opencode-local/plugins/agent-todo"].source.script,
    /agent-todo-instructions\.ts/,
  );
  const leaf = read("../default.nix");
  assert.match(leaf, /imports = \[ \.\/todo\.nix \]/);
  assert.match(leaf, /programs\.opencode\.todo\.enable = lib\.mkDefault true/);
  assert.doesNotMatch(
    leaf,
    /decisionSupport|decision-support\.nix|decision-check/,
  );
});

test("note tool names default to deny with explicit Build/Plan exceptions and no edit grants", () => {
  const tools = ["agent_todo_read", "agent_todo_propose"];
  assert.deepEqual(
    settings.permissions,
    tools.map((action) => ({ action, resource: "*", effect: "deny" })),
  );
  assert.deepEqual(Object.keys(settings.agents).sort(), ["build", "plan"]);
  for (const name of ["build", "plan"]) {
    const agent = settings.agents[name];
    assert.deepEqual(Object.keys(agent), ["permissions"]);
    for (const action of tools) {
      assert.deepEqual(
        agent.permissions.find((rule) => rule.action === action),
        { action, resource: "*", effect: "allow" },
      );
    }
    assert.ok(
      agent.permissions.some(
        (rule) =>
          rule.action === "read" &&
          rule.resource === "/home/fixture/agent-todo/*",
      ),
    );
    assert.ok(agent.permissions.every((rule) => rule.action !== "edit"));
  }
});

test("old combined option fails with a migration explanation rather than silently enabling notes", () => {
  assert.deepEqual(evaluated[1].imports[0].path, [
    "programs",
    "opencode",
    "decisionSupport",
    "enable",
  ]);
  assert.match(
    evaluated[1].imports[0].message,
    /archived.*programs\.opencode\.todo\.enable/s,
  );
});

test("archived decision guidance and fixtures are preserved byte-for-byte and removed from active paths", () => {
  const artifacts = [
    [
      "decision-support.nix",
      "4fc1b69d39e2902d78361034335ea69e45bd0851db5c614dfc3b98af1d3a2fe8",
    ],
    [
      "config/decision-support.md",
      "dac1f7ef71ca59e8c553755982e77a05210d7f4e66ec8d98518b5aaf94cda175",
    ],
    [
      "skills/decision-check/SKILL.md",
      "b4be81b0e59dd026ffbf3a4c715b98db65b4ffd2074037d7681466861a450984",
    ],
    [
      "tests/decision-check-scenarios.md",
      "ea34d0bf212da47085fbe6bcf9c5fc17d62e9dec03f66401a3dc03192b489028",
    ],
  ];
  for (const [path, hash] of artifacts) {
    assert.equal(
      createHash("sha256")
        .update(read(`../archive/decision-support/${path}`))
        .digest("hex"),
      hash,
      path,
    );
    assert.equal(
      existsSync(new URL(`../${path}`, import.meta.url)),
      false,
      path,
    );
  }
});
