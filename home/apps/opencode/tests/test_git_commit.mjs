import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { test } from "node:test";

test("only git commit requests shell approval; other Git operations keep their policy", () => {
  const settings = JSON.parse(
    execFileSync("nix", [
      "eval",
      "--offline",
      "--json",
      "--file",
      new URL("../config/v2-settings.nix", import.meta.url).pathname,
      "--apply",
      "f: f { lib = {}; }",
    ]),
  );
  // Native V2 whole-value wildcard rule, including its trailing ' *' exception.
  const matches = (pattern, value) => {
    const regex = (p) =>
      new RegExp(
        "^" +
          p
            .split("*")
            .map((part) => part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
            .join(".*") +
          "$",
      );
    return (
      regex(pattern).test(value) ||
      (pattern.endsWith(" *") && regex(pattern.slice(0, -2)).test(value))
    );
  };
  const effect = (command) =>
    [{ action: "*", resource: "*", effect: "allow" }, ...settings.permissions]
      .filter(
        (rule) =>
          matches(rule.action, "shell") && matches(rule.resource, command),
      )
      .at(-1).effect;
  for (const command of [
    "git commit",
    "git commit -m example",
    "git commit --amend --no-edit",
    "git -C /repo commit",
    "git -c user.name=Example commit -m example",
  ])
    assert.equal(effect(command), "ask", command);
  for (const command of [
    "git status",
    "git diff --cached",
    "git log -1",
    "git add file.txt",
    "git commit-tree HEAD^{tree}",
  ])
    assert.equal(effect(command), "allow", command);
  const rules = readFileSync(
    new URL("../config/AGENTS.md", import.meta.url),
    "utf8",
  );
  assert.match(rules, /ONLY after a separate explicit user request to commit/);
  assert.match(rules, /checkpoint requests do not authorize/);
  assert.match(rules, /do not request or save Always approval/);
});
