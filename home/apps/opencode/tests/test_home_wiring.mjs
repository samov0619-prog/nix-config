import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import { homeWiring } from "./home-wiring.mjs";

const original = JSON.parse(
  execFileSync(
    "nix",
    [
      "eval",
      "--offline",
      "--json",
      "--file",
      fileURLToPath(new URL("../config/v2-settings.nix", import.meta.url)),
      "--apply",
      "f: f {}",
    ],
    { timeout: 10000 },
  ),
);

test("HM installs one explicit personal JSONC on Linux/Darwin, respecting custom XDG", () => {
  for (const linux of [true, false]) {
    for (const configHome of [
      "/home/fixture/.config",
      "/home/fixture/custom-config",
    ]) {
      const actual = homeWiring(true, linux, configHome);
      const personal = JSON.parse(actual.personalFiles["opencode.jsonc"].text);
      assert.equal(
        actual.env.OPENCODE_CONFIG,
        `${configHome}/opencode-local/opencode.jsonc`,
      );
      assert.deepEqual(personal.instructions, [
        `${configHome}/opencode-local/AGENTS-personal.md`,
      ]);
      assert.deepEqual(personal.skills, [
        `${configHome}/opencode-local/skills`,
      ]);
      assert.match(
        actual.personalFiles["AGENTS-personal.md"].text,
        new RegExp(`${configHome}/opencode-local/review-analysis.md`),
      );
      assert.equal(Object.keys(personal.commands).length, 4);
      assert.deepEqual(personal.plugins, ["./plugins/agent-todo"]);
      assert.deepEqual(actual.skills, ["git-regression-rollback"]);
      assert.doesNotMatch(
        actual.baseText,
        /Goals and Approach|review-analysis|discussion-map|`research`/,
      );
      for (const old of [
        "opencode/review-analysis.md",
        "opencode/commands/delegated-review.md",
        "opencode/commands/delegated-review-chrome.md",
        "opencode/plugins/agent-todo-v2",
      ]) {
        assert.equal(actual.names.includes(old), false, old);
      }
      assert.ok(actual.names.includes("opencode/commands/problem-brief.md"));
      assert.equal(
        actual.names.some((name) =>
          name.startsWith("opencode-local/plugins/agent-todo/"),
        ),
        false,
      );
      assert.equal(
        actual.names.includes("opencode/plugins/workspace-context/tui.ts"),
        linux,
      );
    }
  }
});

test("home base retains every provider/safety/compaction field without personal routing", () => {
  const { model, agents, ...base } = original;
  const actual = homeWiring();
  assert.deepEqual(actual.base, base);
  const personal = JSON.parse(actual.personalFiles["opencode.jsonc"].text);
  assert.equal(personal.model, model);
  assert.deepEqual(Object.keys(personal.agents), Object.keys(agents));
  for (const name of Object.keys(agents)) {
    assert.equal(personal.agents[name].model, agents[name].model);
  }
  assert.ok(actual.names.includes("opencode/plugins/git-offline-v2"));
});

test("disabling notes removes their configuration and leaves review/commands/safety intact", () => {
  const actual = homeWiring(false);
  const personal = JSON.parse(actual.personalFiles["opencode.jsonc"].text);
  assert.equal("plugins" in personal || "permissions" in personal, false);
  assert.ok(personal.agents.review && personal.agents.research);
  assert.equal(Object.keys(personal.commands).length, 4);
  assert.ok(actual.names.includes("opencode/plugins/git-offline-v2"));
  assert.ok(
    personal.agents.plan.permissions.some(
      (rule) => rule.action === "edit" && rule.effect === "deny",
    ),
  );
});
