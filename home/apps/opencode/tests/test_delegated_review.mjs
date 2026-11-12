import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const source = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const command = source("../commands/delegated-review.md");
const system = source("../config/review-system.md");
const settings = JSON.parse(
  execFileSync(
    "nix",
    [
      "eval",
      "--offline",
      "--json",
      "--file",
      fileURLToPath(new URL("../config/v2-settings.nix", import.meta.url)),
      "--apply",
      "f: f { lib = {}; }",
    ],
    { timeout: 10000 },
  ),
);

test("review config loads the shared prompt and retains the native model/permission policy", () => {
  const routes = JSON.parse(source("../plugins/model-routing/routing-models.json"));
  const route = routes.review ?? routes["*"];
  assert.equal(
    settings.agents.review.model,
    `${route.providerID}/${route.id}#${route.variant}`,
  );
  assert.equal(settings.agents.review.mode, "subagent");
  assert.equal(settings.agents.review.system, system);
  assert.deepEqual(
    settings.agents.review.permissions,
    ["edit", "subagent", "todowrite"].map((action) => ({
      action,
      resource: "*",
      effect: "deny",
    })),
  );
  assert.deepEqual(
    settings.agents.review.permissions,
    settings.agents.research.permissions,
  );
});

// These are instruction/declaration guards, NOT execution of the retry policy.
test("the command stays with the orchestrator and has no model override or eager shell blocks", () => {
  const [, frontmatter, body] = command.split(/^---\n/m);
  assert.ok(body.includes("$ARGUMENTS"));
  assert.equal(frontmatter.trim().split("\n").length, 2);
  assert.match(frontmatter, /^description: .+$/m);
  assert.match(frontmatter, /^subagent: false$/m);
  assert.doesNotMatch(frontmatter, /^(agent|model|subtask):/m);
  assert.doesNotMatch(command, /!`/);
  const module = source("../default.nix");
  assert.match(
    module,
    /"opencode\/commands\/delegated-review\.md"\.source = \.\/commands\/delegated-review\.md;/,
  );
  assert.doesNotMatch(module, /"opencode\/commands\/README\.md"/);
});

test("recovery instructions preserve identity, cap retries and forbid false completion", () => {
  for (const marker of [
    "sessionID",
    "parent-filtered child list",
    "fingerprint",
    "up to six further",
    "additional_remaining = 6 - additional_used",
    "Before the initial invocation, additional counters are 0 used / 6 remaining",
    "never a reset before subsequent invocations",
    "1/6 additional used, 5 additional remaining, 0 provider-failure retries",
    "first provider retry waits 20 seconds",
    "20, 40, 60, 90, 120, 120",
    "10 minutes since the last verified substantive review progress",
    "A replacement never resets the budget",
    "no recoverable child and no still-running invocation",
    "never claim zero rework",
    "INCOMPLETE — no final verdict",
    "not a verdict on\nmixed versions",
    "Do not discard other reviewers'",
    "do not turn the\nwhole plan serial",
  ]) {
    assert.ok(command.includes(marker), marker);
  }
  assert.match(command, /Never send a duplicate prompt,/);
  assert.match(command, /Do not bypass a user's cancellation or denied access/);
  assert.match(command, /Native completion\/text alone is insufficient/);
  assert.match(command, /wait for the actual command or an explicit request to begin/);
  assert.match(command, /Do not guess serialization variants or brute-force/);
  assert.doesNotMatch(command, /Before any invocation/);
});

test("parent and reviewer prohibit temporary review artifacts, not native runtime storage", () => {
  for (const prompt of [command, system]) {
    assert.match(prompt, /Do not create temporary helper scripts, manifests, reports or/);
    assert.match(prompt, /even\s+outside the repository/);
    assert.match(prompt, /inline interpreter code/);
    assert.match(prompt, /runtime-managed session\/log storage/);
  }
  assert.match(command, /do not redirect its output to files/);
});

test("the published fingerprint recipe has an exact canonical encoding, including escaped paths", () => {
  const recipe = command.match(/```python\n([\s\S]*?)\n```/)[1];
  const manifest = {
    schema: "dr-scope-v1",
    repo: "/fixture",
    kind: "working-tree",
    base: "a".repeat(40),
    head: null,
    paths: ['a"\\\né'],
    exclusions: ["result"],
    diff_sha256: "b".repeat(64),
    files: [
      {
        path: 'a"\\\né',
        type: "file",
        mode: "100644",
        sha256: "c".repeat(64),
      },
    ],
  };
  // Independent, explicitly ordered JSON encoding of this small fixture.
  const wire = JSON.stringify({
    base: manifest.base,
    diff_sha256: manifest.diff_sha256,
    exclusions: manifest.exclusions,
    files: [
      {
        mode: "100644",
        path: manifest.paths[0],
        sha256: "c".repeat(64),
        type: "file",
      },
    ],
    head: null,
    kind: "working-tree",
    paths: manifest.paths,
    repo: "/fixture",
    schema: "dr-scope-v1",
  }).replaceAll("é", "\\u00e9");
  const expected = createHash("sha256").update(wire, "ascii").digest("hex");
  const hash = (value) =>
    execFileSync(
      "python3",
      ["-B", "-c", "import sys, json\nmanifest = json.load(sys.stdin)\n" + recipe],
      { input: JSON.stringify(value), encoding: "utf8", timeout: 5000 },
    ).trim();
  assert.equal(hash(manifest), expected);
  assert.equal(hash(Object.fromEntries(Object.entries(manifest).reverse())), expected);
  const changed = structuredClone(manifest);
  changed.files[0].sha256 = "d".repeat(64);
  assert.notEqual(hash(changed), expected);
  changed.files[0] = { path: manifest.paths[0], type: "deleted", mode: null, sha256: null };
  assert.notEqual(hash(changed), expected);
});

test("the reviewer remains general-purpose and distinguishes partial evidence from a verdict", () => {
  for (const marker of [
    "delegated change or claim",
    "Do not edit files, delegate, commit, install, build",
    "An edit denial is not permission",
    "requiring validation, not authority",
    "Files merely read are\nnot automatically reviewed",
    "The parent owns retry budgets",
    "When no format is supplied",
    "without any final\nverdict: no APPROVE, REQUEST_CHANGES or BLOCKER",
  ]) {
    assert.ok(system.includes(marker), marker);
  }
  assert.doesNotMatch(system, /openai\/|anthropic\/|gpt-6/);
});
