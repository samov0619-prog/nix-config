// Source/evaluation guards only, not model compliance or live Mac acceptance.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { instructions } from "./instructions.mjs";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const common = read("../config/AGENTS.common.md");
const personal = read("../config/AGENTS.md");
const home = read("../config/AGENTS.home.md");
const homeReview = read("../config/AGENTS.review.md");
const corporate = read("../config/AGENTS.corporate.md");
const corporatePersonal = read("../config/AGENTS.corporate-personal.md");
const homeOnly =
  /\bnsh\b|NSH_FLAKE|nixpkgs|nix-config|nix shell|\/tmp\/opencode|~\/\.opencode/;
const corporateOnly =
  /## Requirements Sources|MCP-KAITEN|MCP-XTRACKER|promptLogs|Kaiten card|ALWAYS ASK for the task\/ticket/;
const taskLog = read("../skills/task-summary-log/SKILL.md");

test("the evaluated variants use only their explicit source lists", () => {
  assert.deepEqual(Object.keys(instructions).sort(), [
    "corporate",
    "corporatePersonal",
    "home",
    "homeBase",
    "homePersonal",
  ]);
  assert.equal(instructions.homeBase, common + "\n" + home);
  assert.equal(instructions.homePersonal, personal + "\n" + homeReview);
  assert.equal(
    instructions.home,
    instructions.homeBase + "\n" + instructions.homePersonal,
  );
  assert.equal(instructions.corporate, common + "\n" + corporate);
  assert.equal(
    instructions.corporatePersonal,
    personal + "\n" + corporatePersonal,
  );
});

test("HM's Linux and Darwin global rules contain the base, never personal workflows", () => {
  for (const isLinux of [true, false]) {
    const installed = execFileSync(
      "nix",
      [
        "eval",
        "--offline",
        "--raw",
        "--file",
        fileURLToPath(new URL("../default.nix", import.meta.url)),
        "--apply",
        `f: (f {
          pkgs.stdenv.isLinux = ${isLinux};
           lib.optionalAttrs = condition: attrs: if condition then attrs else {};
           lib.hasPrefix = prefix: text: builtins.substring 0 (builtins.stringLength prefix) text == prefix;
           config.programs.opencode.todo.enable = true;
           config.xdg.configHome = "/home/fixture/.config";
           config.home.homeDirectory = "/home/fixture";
           opencodePackage = null;
        }).xdg.configFile."opencode/AGENTS.md".text`,
      ],
      { encoding: "utf8", timeout: 10000 },
    );
    assert.equal(installed, instructions.homeBase);
    assert.doesNotMatch(installed, corporateOnly);
    assert.doesNotMatch(installed, /XTracker|FBDC-|task-summary-log/);
    assert.doesNotMatch(installed, /opencode-local/);
    assert.doesNotMatch(
      installed,
      /Goals and Approach|Explicit Review|configured `review`|`research`|discussion-map/,
    );
  }
});

test("shared engineering rules are environment-neutral and do not require personal agents", () => {
  assert.doesNotMatch(common + personal, homeOnly);
  assert.doesNotMatch(common + personal, corporateOnly);
  assert.doesNotMatch(
    common + personal,
    /opencode-local|review-analysis\.md|commands\/delegated-review/,
  );
  assert.doesNotMatch(
    common,
    /Goals and Approach|interactive shell is Fish|`research`|`review`|discussion-map/,
  );
  for (const section of [
    "Engineering Choices",
    "Source Exploration",
    "Code Comments",
  ]) {
    assert.ok(common.includes("## " + section), section);
  }
  assert.match(personal, /Goals and Approach|Personal Delegation Preferences/);
});

test("home retains the 68-bullet baseline apart from explicit path/delegation migrations", () => {
  // Reconstruct only the agreed changed fragments, then retain the original
  // immutable count/hash guard for every other pre-split home instruction.
  let withoutComments = instructions.home.replace(
    /^## Code Comments\n[\s\S]*?(?=^## )/m,
    "",
  );
  withoutComments = withoutComments.replace(
    /^## Personal Delegation Preferences\n[\s\S]*?(?=^## )/m,
    "",
  );
  withoutComments = withoutComments.replace(
    /^- Use tools for mechanical extraction,[\s\S]*?(?=^- |^## )/m,
    "- Use tools for mechanical extraction, counting and transformation, without an\n" +
      "  extra model call. Delegate bounded fact collection to `explore`, substantive\n" +
      "  source synthesis to `research`, and independent correctness checks to `review`\n" +
      "  only when separate analysis is justified and delegation is permitted. Give the\n" +
      "  child a source scope, question and expected evidence; avoid duplicating its work.\n",
  );
  const pathMigrations = [
    [
      "read `~/.config/opencode-local/review-analysis.md`\n  directly from the personal layer.",
      "read `review-analysis.md` in OpenCode's active global\n  config directory (normally `~/.config/opencode`; respect `XDG_CONFIG_HOME`).",
    ],
    [
      "an applicable project override, otherwise\n  `~/.config/opencode-local/commands/delegated-review.md`, with the user's scope\n  as arguments.",
      "the applicable installed `commands/delegated-review.md` template with the user's\n  scope as arguments, respecting project overrides.",
    ],
    [
      "For the latter, the parent must first read and follow\n  an applicable project override, otherwise\n  `~/.config/opencode-local/commands/delegated-review-chrome.md`, using the user's\n  evidence/run target as its arguments.",
      "For the latter, the parent must first read and follow the applicable installed\n  `commands/delegated-review-chrome.md` orchestration template, respecting project\n  overrides and using the user's evidence/run target as its arguments.",
    ],
  ];
  for (const [before, after] of pathMigrations) {
    assert.equal(withoutComments.split(before).length, 2);
    withoutComments = withoutComments.replace(before, after);
  }
  const bullets = withoutComments.match(/^- .*?(?:\n[ \t].*)*$/gm).sort();
  assert.equal(bullets.length, 68);
  assert.equal(
    createHash("sha256").update(bullets.join("\n\n")).digest("hex"),
    "0ba7e0f635d6aa66b850fecd4faa65b55649cdc3c49fcedb778da3139cf51025",
  );
  assert.match(instructions.home, /\bnsh unstable\b/);
  assert.match(
    instructions.home,
    /ONLY ask for a task or ticket number when that history establishes/,
  );
});

test("standalone corporate personal output has shared guidance and its own review paths", () => {
  assert.doesNotMatch(instructions.corporatePersonal, homeOnly);
  assert.doesNotMatch(instructions.corporatePersonal, corporateOnly);
  assert.match(
    instructions.corporatePersonal,
    /~\/\.config\/opencode-local\/review-analysis\.md/,
  );
  assert.match(
    instructions.corporatePersonal,
    /~\/\.config\/opencode-local\/commands\/delegated-review\.md/,
  );
  assert.doesNotMatch(
    instructions.corporatePersonal,
    /## Explicit Review Requests|ONLY ask for a task or ticket number/,
  );
  assert.equal(
    (instructions.corporatePersonal.match(/^## Goals and Approach$/gm) ?? [])
      .length,
    1,
  );
});

test("corporate-specific contracts survive tracker migration and shared-rule extraction", () => {
  const migrations = [
    [
      "- Use available, permitted read-only issue-tracker/Wiki MCP tools to read the task\n" +
        "  and its linked requirements. The configuration may expose `MCP-XTRACKER`,\n" +
        "  `MCP-KAITEN`, `MCP-WIKI` and `MCP-GITLAB`; discover actual tools and respect\n",
      "- Use XTracker for current corporate tasks. Use available, permitted read-only\n" +
        "  issue-tracker/Wiki MCP tools to read the task and its linked requirements.\n" +
        "  The configuration may expose `MCP-XTRACKER`, `MCP-WIKI` and `MCP-GITLAB`;\n" +
        "  discover actual tools and respect\n",
    ],
    [
      "- ALWAYS ASK for the Kaiten card number if it is missing in the context. The number is optional.\n",
      "- For a requested log, ask for the XTracker task key if missing in the context.\n" +
        "  The key is optional: continue without it if the user declines or has none.\n",
    ],
  ];
  let expected = read("../macos/trf-review/opencode/AGENTS.md");
  for (const [before, after] of migrations) {
    assert.equal(
      expected.split(before).length,
      2,
      "the historical fragment must occur exactly once",
    );
    expected = expected.replace(before, after);
  }
  for (const heading of [
    "Discussion",
    "Source Exploration",
    "Formatting",
    "Verification and Resources",
    "User Actions",
  ]) {
    const section = new RegExp(
      `^## ${heading}\\n[\\s\\S]*?(?=^## |$(?![\\s\\S]))`,
      "m",
    );
    assert.ok(expected.match(section), heading);
    expected = expected.replace(section, "");
  }
  assert.equal(corporate, expected);
  assert.match(
    instructions.corporate,
    /Keep skill permission restrictions intact|a subagent is not a permission bypass/,
  );
  assert.match(corporate, corporateOnly);
  assert.doesNotMatch(corporate, /Kaiten|MCP-KAITEN|KT-|FBDC-/);
  assert.doesNotMatch(corporate, homeOnly);
  assert.doesNotMatch(
    corporate,
    /## Goals and Approach|opencode-local|review-analysis|review-system|\/delegated-review/,
  );
});

test("Samov's current XTracker convention is personal and cannot regress from old history", () => {
  assert.match(
    corporatePersonal,
    /confirmed current XTracker\n  task key `FBDC-<number>`/,
  );
  assert.match(
    corporatePersonal,
    /Older `KT-\.\.\.`\n  entries do not override/,
  );
  assert.match(corporatePersonal, /Do not reuse a task key from history/);
  assert.match(
    corporatePersonal,
    /no approval to create branches, commit or perform remote Git operations/,
  );
  assert.match(instructions.corporatePersonal, /FBDC-<number>/);
  assert.doesNotMatch(
    common + home + corporate,
    /## Corporate Task Convention/,
  );
});

test("corporate task logs use full keys without duplicating or renaming legacy logs", () => {
  assert.match(taskLog, /ONLY when the user explicitly asks/);
  assert.match(taskLog, /XTracker task key/);
  assert.match(taskLog, /FBDC-123456_add-api-endpoint\.md/);
  assert.match(taskLog, /<task-key or "No ID">/);
  assert.match(taskLog, /numeric filenames or previous tracker keys/);
  assert.match(taskLog, /Matching digits alone do not prove/);
  assert.match(
    taskLog,
    /Preserve its filename unless the user explicitly requests a rename/,
  );
  assert.match(taskLog, /user declines or has none, continue without it/);
  assert.match(taskLog, /date -u \+%Y-%m-%d/);
  assert.match(
    taskLog,
    /DO NOT run Git commands to collect changes unless the user allows it/,
  );
  assert.match(taskLog, /NEVER write secrets/);
  assert.doesNotMatch(taskLog, /Kaiten|kaiten-id|KT-/);
  const module = read("../default.nix");
  assert.doesNotMatch(
    module,
    /skills\.task-summary-log|skills\/task-summary-log/,
  );
});

test("corporate review routing changes only discovery ownership; comments live in Common", () => {
  const legacy = read(
    "../macos/trf-review/opencode-local/AGENTS-personal.md",
  ).replace(
    "Existing team command/agent symlinks\n  are discovery entrypoints only, not ownership of personal policy.",
    "Personal commands and agents are\n  registered explicitly in the personal JSONC; no team discovery links are required.",
  );
  for (const heading of ["Review Workflows", "Code Comments"]) {
    const section = new RegExp(
      `^## ${heading}\\n[\\s\\S]*?(?=^## |$(?![\\s\\S]))`,
      "m",
    );
    assert.equal(
      (instructions.corporate + "\n" + instructions.corporatePersonal)
        .match(section)?.[0]
        .trim(),
      legacy.match(section)?.[0].trim(),
    );
  }
});
