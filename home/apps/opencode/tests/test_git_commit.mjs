import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const settings = JSON.parse(
  execFileSync("nix", [
    "eval",
    "--offline",
    "--json",
    "--file",
    new URL("../config/v2-settings.nix", import.meta.url).pathname,
    "--apply",
    "f: f {}",
  ]),
);

// Native V2 whole-value wildcard semantics, including its trailing ' *' exception.
// These are declaration fixtures, not shell-scanner or native approval UI tests.
const matches = (pattern, value) => {
  let escaped = pattern
    .replaceAll("\\", "/")
    .replace(/[.+^${}()|[\]\\]/g, "\\$&")
    .replace(/\*/g, ".*")
    .replace(/\?/g, ".");
  if (escaped.endsWith(" .*")) escaped = escaped.slice(0, -3) + "( .*)?";
  return new RegExp("^" + escaped + "$", "s").test(value.replaceAll("\\", "/"));
};
const effect = (command) =>
  [{ action: "*", resource: "*", effect: "allow" }, ...settings.permissions]
    .filter(
      (rule) =>
        matches(rule.action, "shell") && matches(rule.resource, command),
    )
    .at(-1).effect;
const forms = (command) => [
  `git ${command}`,
  `git -C /repo ${command}`,
  `git -c color.ui=always ${command}`,
  `git -C /repo -c color.ui=always ${command}`,
];
const expectAll = (commands, expected) => {
  for (const command of commands)
    assert.equal(effect(command), expected, command);
};

test("history, integration, checkout and discard operations request approval", () => {
  const commands = [
    "commit",
    "commit -m example",
    "commit --amend --no-edit",
    "merge feature",
    "merge --no-commit feature",
    "cherry-pick abc123",
    "revert abc123",
    "am change.patch",
    "rebase main",
    "rebase --continue",
    "rebase --abort",
    "reset --soft HEAD~1",
    "reset --hard HEAD",
    "checkout main",
    "checkout -- src/file.ts",
    "switch feature",
    "restore --staged src/file.ts",
    "restore src/file.ts",
    "clean -fd",
  ];
  expectAll(commands.flatMap(forms), "ask");
});

test("stash mutations including implicit push request approval, not list/show", () => {
  expectAll(
    [
      "stash",
      "stash -u",
      "stash --include-untracked",
      "stash push -m example",
      "stash save example",
      "stash apply stash@{0}",
      "stash pop",
      "stash drop stash@{0}",
      "stash clear",
      "stash branch recovered stash@{0}",
      "stash store abc123",
      "stash create",
      "stash import abc123",
      "stash export --print",
    ].flatMap(forms),
    "ask",
  );
  expectAll(
    ["stash list", "stash list --stat", "stash show -p stash@{0}"].flatMap(
      forms,
    ),
    "allow",
  );
});

test("ref deletion, rename, force updates and worktree cleanup request approval", () => {
  expectAll(
    [
      "branch -d feature",
      "branch -D feature",
      "branch --delete feature",
      "branch -m feature renamed",
      "branch --move feature renamed",
      "branch -M feature main",
      "branch -C main existing",
      "branch -f main HEAD~1",
      "branch --force main HEAD~1",
      "branch feature -D",
      "branch -r -d origin/feature",
      "branch -rd origin/feature",
      "branch -rD origin/feature",
      "branch -df feature",
      "branch -fD feature",
      "tag -d release",
      "tag --delete release",
      "tag -f release HEAD",
      "tag release --force HEAD",
      "worktree remove ../old",
      "worktree move ../old ../new",
      "worktree prune",
      "worktree repair ../other",
    ].flatMap(forms),
    "ask",
  );
});

test("branch, worktree and graph inspection/comparison stay free", () => {
  expectAll(
    [
      "status --short",
      "diff --cached",
      "diff main...feature -- src",
      "diff --no-index ../one/src ../two/src",
      "diff-tree --no-commit-id --name-only -r HEAD",
      "diff-index --cached HEAD",
      "diff-files --name-only",
      "range-diff main..feature main..updated",
      "log --graph --oneline --all",
      "show HEAD:src/file.ts",
      "merge-base main feature",
      "merge-base --is-ancestor main HEAD",
      "merge-base --fork-point main feature",
      "merge-base --all --octopus main feature other",
      "merge-base --independent main feature",
      "rev-list --left-right --count main...feature",
      "rev-parse --show-toplevel",
      "for-each-ref --format='%(refname)' refs/heads",
      "branch",
      "branch -avv",
      "branch --list feature",
      "branch --contains HEAD",
      "branch --merged main",
      "branch --no-merged main",
      "branch --format='%(refname:short)'",
      "tag",
      "tag -l release-*",
      "tag --list",
      "tag --contains HEAD",
      "tag -v release",
      "worktree list --porcelain",
      "reflog show HEAD",
      "ls-tree -r HEAD",
      "ls-files --stage",
      "cat-file -p HEAD",
      "blame src/file.ts",
      "add src/file.ts",
      "commit-tree HEAD^{tree}",
    ].flatMap(forms),
    "allow",
  );
});

test("direct inspections can mention refs/files named after protected commands", () => {
  expectAll(
    [
      "git diff main rebase",
      "git diff reset merge -- commit",
      "git log --grep rebase",
      "git show commit -- reset",
      "git merge-base merge rebase",
      "git range-diff reset..merge reset..rebase",
      "git rev-list --left-right reset...rebase",
      "git rev-parse --verify rebase",
      "git stash show rebase",
    ],
    "allow",
  );
});

test("inspection words in mutation operands never override approval", () => {
  expectAll(
    [
      "git reset --hard diff",
      "git -C /repo reset --hard diff",
      "git rebase log",
      "git -C /repo rebase diff",
      "git branch -D show",
      "git -C /repo branch -D log",
      "git stash drop show",
      "git -C /repo stash drop diff",
    ],
    "ask",
  );
  // Documented conservative false positive: wildcard is not a Git argv parser.
  assert.equal(effect("git -C /repo diff main rebase"), "ask");
});

test("instruction consent and Always restrictions cover protected mutations", () => {
  const rules = readFileSync(
    new URL("../config/AGENTS.md", import.meta.url),
    "utf8",
  );
  assert.match(rules, /ONLY after a separate explicit user request to commit/);
  assert.match(rules, /checkpoint requests do not authorize/);
  assert.match(rules, /explicit approval before rewriting history/);
  assert.match(rules, /do not request or save Always/);
  assert.match(rules, /explicit subcommands and separate flags/);
});

test("no permission rule widens external access or removes agent restrictions", () => {
  assert.ok(settings.permissions.every((rule) => rule.action === "shell"));
  assert.deepEqual(settings.agents.plan.permissions, [
    { action: "edit", resource: "*", effect: "deny" },
  ]);
  for (const id of ["review", "research", "explore"]) {
    assert.ok(
      settings.agents[id].permissions.some(
        (rule) => rule.action === "edit" && rule.effect === "deny",
      ),
    );
  }
});
