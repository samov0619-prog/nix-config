// Export/config/source contracts only, not the corporate Mac's live runtime.
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  existsSync,
  lstatSync,
  mkdtempSync,
  readFileSync,
  rmSync,
} from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const read = (path) => readFileSync(join(root, path), "utf8");
const evaluate = (directory) =>
  JSON.parse(
    execFileSync(
      "nix",
      [
        "eval",
        "--offline",
        "--json",
        "--file",
        join(root, "macos/export.nix"),
        "--apply",
        `f: f { personalDirectory = ${JSON.stringify(directory)}; }`,
      ],
      { timeout: 10000, maxBuffer: 4 * 1024 * 1024 },
    ),
  );
const { files } = evaluate("~/.config/opencode-local");
const text = (entry) => entry.text ?? readFileSync(entry.source, "utf8");
assert.ok(
  process.env.OPENCODE_TEST_TYPESCRIPT,
  "Set OPENCODE_TEST_TYPESCRIPT to an installed typescript.js; no dependencies are installed by this test.",
);
const ts = (
  await import(pathToFileURL(process.env.OPENCODE_TEST_TYPESCRIPT).href)
).default;
const parsed = ts.parseConfigFileTextToJson(
  "opencode.jsonc",
  text(files["opencode/opencode.jsonc"]),
);
assert.equal(parsed.error, undefined, "the preserved team's JSONC must parse");
const common = parsed.config;
const personal = JSON.parse(text(files["opencode-local/opencode.jsonc"]));

test("corporate protected settings/plugins and historical acceptance remain byte-identical", () => {
  const baseline = JSON.parse(read("macos/sources/baseline.json"));
  for (const [name, expected] of Object.entries(baseline.preserved)) {
    const bytes = readFileSync(join(root, "macos/sources", name));
    assert.equal(
      createHash("sha256").update(bytes).digest("hex"),
      expected,
      name,
    );
    const output = name
      .replace(/^common\//, "opencode/")
      .replace(/^personal-history\//, "opencode-local/");
    assert.equal(text(files[output]), bytes.toString("utf8"), output);
  }
});

test("Common has seven unchanged MCPs and no Samov role/workflow dependency", () => {
  assert.deepEqual(Object.keys(common.mcp.servers), [
    "MCP-WIKI",
    "MCP-KAITEN",
    "MCP-XTRACKER",
    "MCP-GITLAB",
    "Chrome MCP",
    "MCP-HUB",
    "Figma-Framelink",
  ]);
  assert.deepEqual(
    Object.keys(common.agents),
    ["title"],
    "preserve the team's native title model setting",
  );
  assert.equal(common.default_agent, undefined);
  assert.equal(common.instructions, undefined);
  assert.equal(common.skills, undefined);
  const body = text(files["opencode/AGENTS.md"]);
  assert.doesNotMatch(
    body,
    /Samov|Goals and Approach|\bFish\b|opencode-local|discussion-map|delegated-review|NixOS|\bnsh\b/,
  );
  assert.match(body, /XTracker/);
  assert.doesNotMatch(
    Object.keys(files)
      .filter((name) => name.startsWith("opencode/"))
      .join("\n"),
    /agents\/review|delegated-review|discussion-map/,
  );
  assert.ok(files["opencode/commands/problem-brief.md"]);
  assert.equal(files["opencode-local/commands/problem-brief.md"], undefined);
});

test("personal commands/roles are explicit, frontmatter-free, parent-model inheriting and manual-map only", () => {
  assert.deepEqual(Object.keys(personal.agents), ["research", "review"]);
  for (const agent of Object.values(personal.agents))
    assert.equal(agent.model, undefined);
  for (const [name, command] of Object.entries(personal.commands)) {
    assert.equal(command.subagent, false);
    assert.equal(command.agent, undefined);
    assert.equal(command.model, undefined);
    assert.equal(command.template, `{file:commands/${name}.md}`);
    assert.ok(
      !text(files[`opencode-local/commands/${name}.md`]).startsWith("---"),
    );
  }
  assert.equal(Object.keys(personal.commands).length, 4);
  assert.match(
    text(files["opencode-local/skills/discussion-map/SKILL.md"]),
    /opencode\/autoinvoke: false/,
  );
  assert.match(
    text(files["opencode-local/AGENTS-personal.md"]),
    /FBDC-<number>/,
  );
  assert.doesNotMatch(
    JSON.stringify(personal),
    /decision-check|agent-todo|switch-paid|local\.model-routing/,
  );
});

test("custom-XDG export rewrites personal policy/instruction/skill paths without global discovery links", () => {
  const exported = evaluate(
    "/Users/example/custom-config/opencode-local",
  ).files;
  for (const [name, entry] of Object.entries(exported)) {
    if (!name.startsWith("opencode-local/")) continue;
    if (name.includes("/update-2026-11-16/")) continue; // historical artifacts remain verbatim
    assert.doesNotMatch(text(entry), /~\/\.config\/opencode-local/);
  }
  const settings = JSON.parse(text(exported["opencode-local/opencode.jsonc"]));
  assert.deepEqual(settings.instructions, [
    "/Users/example/custom-config/opencode-local/AGENTS-personal.md",
  ]);
  assert.deepEqual(settings.skills, [
    "/Users/example/custom-config/opencode-local/skills",
  ]);
});

test("export excludes mutable/private state, external voice installation, binaries and home sound patches", () => {
  const names = Object.keys(files);
  assert.doesNotMatch(
    names.join("\n"),
    /cli\.json|service.*\.json|\.env|auth\.json|node_modules|\/voice\/|sounds\/|session-attention|\.db(?:$|\n)/,
  );
  const skill = text(
    files["opencode/skills/code-patterns-skill-generator/SKILL.md"],
  );
  assert.match(skill, /path determines the skill ID/);
  assert.match(skill, /Frequency is evidence of a convention, not correctness/);
  assert.doesNotMatch(skill, /grep -r|restart OpenCode|DO NOT add.*metadata/);
  assert.match(
    text(files["opencode/skills/task-summary-log/SKILL.md"]),
    /XTracker/,
  );
});

test("exporter writes ordinary staging files, manifests hashes and refuses overwrite/live-config destinations", () => {
  const directory = mkdtempSync("/tmp/opencode/mac-export-test-");
  try {
    const output = join(directory, "stage");
    const script = join(root, "scripts/export-macos.py");
    execFileSync("python3", ["-B", script, output], { timeout: 20000 });
    const manifest = JSON.parse(
      readFileSync(join(output, "manifest.json"), "utf8"),
    );
    for (const [name, hash] of Object.entries(manifest.files)) {
      const path = join(output, name);
      assert.ok(lstatSync(path).isFile() && !lstatSync(path).isSymbolicLink());
      assert.equal(
        createHash("sha256").update(readFileSync(path)).digest("hex"),
        hash,
      );
    }
    assert.equal(Object.keys(manifest.files).length, Object.keys(files).length);
    assert.ok(
      manifest.files["UPGRADE-240.md"],
      "the package includes its backup/rollback procedure",
    );
    assert.equal(spawnSync("python3", ["-B", script, output]).status, 2);
    const live = join(directory, ".config/new-root");
    assert.equal(spawnSync("python3", ["-B", script, live]).status, 2);
    assert.equal(existsSync(live), false);
    const custom = join(directory, "custom-xdg/new-root");
    assert.equal(
      spawnSync("python3", ["-B", script, custom], {
        env: { ...process.env, XDG_CONFIG_HOME: join(directory, "custom-xdg") },
      }).status,
      2,
    );
    assert.equal(existsSync(custom), false);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});
