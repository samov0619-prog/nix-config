// Source/evaluation guards, not live activation or model/browser acceptance.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import { personalLayers } from "./personal-layers.mjs";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const layers = personalLayers();
const originalHome = JSON.parse(
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
const body = (text) => text.replace(/^---\n[\s\S]*?\n---\n\n/, "");
const fileText = (file) => file.text ?? readFileSync(file.source, "utf8");

test("each personal JSONC explicitly registers five current-session commands and real prompt bodies", () => {
  for (const layer of Object.values(layers)) {
    const { settings, files } = layer;
    assert.deepEqual(JSON.parse(files["opencode.jsonc"].text), settings);
    assert.equal(settings.$schema, "https://opencode.ai/config.json");
    assert.deepEqual(Object.keys(settings.commands).sort(), [
      "browser-verification",
      "delegated-review",
      "delegated-review-chrome",
      "problem-brief",
      "task-analysis",
    ]);
    for (const [name, command] of Object.entries(settings.commands)) {
      const source = read(`../commands/${name}.md`);
      assert.equal(
        command.description,
        source.split("\n")[1].slice("description: ".length),
      );
      assert.equal(command.subagent, false);
      assert.equal("agent" in command || "model" in command, false);
      assert.equal(command.template, `{file:commands/${name}.md}`);
      assert.equal(files[`commands/${name}.md`].text.startsWith("---"), false);
      if (name !== "delegated-review")
        assert.equal(files[`commands/${name}.md`].text, body(source));
    }
    assert.deepEqual(settings.instructions, [
      "~/.config/opencode-local/AGENTS-personal.md",
    ]);
    assert.ok(files["task-analysis.README.md"]);
    assert.ok(files["browser-verification.README.md"]);
    assert.ok(files["problem-brief.README.md"]);
  }
});

test("generated delegated review changes only its policy location, preserving the orchestration contract", () => {
  const source = body(read("../commands/delegated-review.md"));
  const before =
    "Before the initial reviewer launch, read `review-analysis.md` from OpenCode's\nactive global config directory (normally `~/.config/opencode`; respect\n`XDG_CONFIG_HOME`), unless already loaded and unchanged.";
  const after =
    "Before the initial reviewer launch, read\n`~/.config/opencode-local/review-analysis.md` directly from the personal layer,\nunless already loaded and unchanged.";
  assert.equal(source.split(before).length, 2);
  for (const layer of Object.values(layers)) {
    assert.equal(
      layer.files["commands/delegated-review.md"].text,
      source.replace(before, after),
    );
    assert.equal(
      fileText(layer.files["review-analysis.md"]),
      read("../config/review-analysis.md"),
    );
    assert.equal(
      fileText(layer.files["review-system.md"]),
      read("../config/review-system.md"),
    );
  }
});

test("home preserves all existing role models, prompts and denials without overriding primary systems", () => {
  const { settings, files } = layers.home;
  assert.equal(settings.model, originalHome.model);
  assert.deepEqual(
    Object.keys(settings.agents),
    Object.keys(originalHome.agents),
  );
  for (const [name, original] of Object.entries(originalHome.agents)) {
    const actual = settings.agents[name];
    assert.equal(actual.model, original.model, name);
    assert.equal(actual.mode, original.mode, name);
    if (original.system) {
      assert.equal(actual.system, `{file:agents/${name}.md}`);
      assert.equal(files[`agents/${name}.md`].text, original.system);
    } else assert.equal("system" in actual, false, name);
    assert.deepEqual(
      actual.permissions?.slice(0, original.permissions?.length ?? 0) ?? [],
      original.permissions ?? [],
      name,
    );
  }
  assert.doesNotMatch(
    files["AGENTS-personal.md"].text,
    /nsh <package>|## Engineering Choices|## Formatting/,
  );
  assert.match(files["AGENTS-personal.md"].text, /## Goals and Approach/);
  assert.match(
    files["AGENTS-personal.md"].text,
    /opencode-local\/commands\/delegated-review-chrome\.md/,
  );
  assert.doesNotMatch(
    files["AGENTS-personal.md"].text,
    /active global\n  config directory/,
  );
});

test("corporate roles inherit models and retain read-only policies without home dependencies", () => {
  const { settings, files } = layers.corporate;
  assert.deepEqual(Object.keys(settings.agents).sort(), ["research", "review"]);
  assert.equal("model" in settings, false);
  for (const [name, agent] of Object.entries(settings.agents)) {
    assert.equal(agent.mode, "subagent");
    assert.equal("model" in agent, false, name);
    assert.equal(agent.system, `{file:agents/${name}.md}`);
    assert.deepEqual(
      agent.permissions,
      ["edit", "subagent", "todowrite"].map((action) => ({
        action,
        resource: "*",
        effect: "deny",
      })),
    );
    assert.doesNotMatch(fileText(files[`agents/${name}.md`]), /^---/);
  }
  assert.equal(
    files["agents/research.md"].text,
    originalHome.agents.research.system,
  );
  assert.match(
    fileText(files["agents/review.md"]),
    /opencode-local\/review-analysis\.md/,
  );
  assert.match(files["AGENTS-personal.md"].text, /FBDC-<number>/);
  assert.doesNotMatch(
    files["AGENTS-personal.md"].text,
    /NSH_FLAKE|\bnsh\b|nix-config|\/tmp\/opencode|~\/\.opencode|Existing team command\/agent symlinks/,
  );
  assert.equal(
    Object.keys(files).some(
      (path) => path.startsWith("plugins/") || path.includes("todo"),
    ),
    false,
  );
});

test("manual discussion-map differs only by supported autoinvoke metadata", () => {
  const original = read("../skills/discussion-map/SKILL.md");
  for (const layer of Object.values(layers)) {
    assert.deepEqual(layer.settings.skills, [
      "~/.config/opencode-local/skills",
    ]);
    const skill = layer.files["skills/discussion-map/SKILL.md"].text;
    assert.equal(
      skill.replace("metadata:\n  opencode/autoinvoke: false\n", ""),
      original,
    );
  }
});

test("home todo is explicitly loaded with all dependencies and can be completely omitted", () => {
  assert.deepEqual(layers.home.settings.plugins, ["./plugins/agent-todo"]);
  assert.equal(
    layers.home.settings.permissions.every(
      (rule) => rule.effect === "deny" && rule.action.startsWith("agent_todo_"),
    ),
    true,
  );
  for (const name of ["build", "plan"]) {
    const rules = layers.home.settings.agents[name].permissions;
    assert.ok(
      rules.some(
        (rule) =>
          rule.action === "agent_todo_propose" && rule.effect === "allow",
      ),
    );
  }
  assert.ok(
    layers.home.settings.agents.plan.permissions.some(
      (rule) => rule.action === "edit" && rule.effect === "deny",
    ),
  );
  assert.deepEqual(
    Object.keys(layers.home.files)
      .filter((path) => path.startsWith("plugins/"))
      .sort(),
    [
      "plugins/agent-todo/agent-todo-instructions.ts",
      "plugins/agent-todo/agent-todo-review.ts",
      "plugins/agent-todo/index.ts",
      "plugins/agent-todo/tui.tsx",
    ],
  );
  const disabled = personalLayers(false);
  assert.equal(
    "plugins" in disabled.home.settings ||
      "permissions" in disabled.home.settings,
    false,
  );
  assert.equal(
    Object.keys(disabled.home.files).some((path) =>
      path.startsWith("plugins/"),
    ),
    false,
  );
  assert.deepEqual(disabled.corporate, layers.corporate);
});

test("personal settings do not replace shared integrations or CLI and HM wires the layer", () => {
  for (const layer of Object.values(layers)) {
    for (const key of ["providers", "mcp", "policies", "default_agent"])
      assert.equal(key in layer.settings, false, key);
    assert.equal("cli.json" in layer.files, false);
    assert.equal(
      Object.keys(layer.files).some(
        (path) =>
          path.includes("decision-check") || path.includes("decision-support"),
      ),
      false,
    );
  }
  assert.match(read("../default.nix"), /personal-layers/);
  assert.match(
    read("../default.nix"),
    /home\.sessionVariables\.OPENCODE_CONFIG/,
  );
  assert.doesNotMatch(
    read("../default.nix"),
    /skills\.discussion-map|"opencode\/review-analysis\.md"|"opencode\/commands\/delegated-review/,
  );
  assert.doesNotMatch(read("../todo.nix"), /personal-layers/);
});
