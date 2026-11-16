import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const source = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const command = source("../commands/delegated-review.md");
const analysis = source("../config/review-analysis.md");
const reviewer = source("../config/review-system.md");
const system = analysis + "\n" + reviewer;
const globalRules = source("../config/AGENTS.md");
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
    "verdict: no APPROVE, REQUEST_CHANGES or BLOCKER",
  ]) {
    assert.ok(system.includes(marker), marker);
  }
  assert.doesNotMatch(system, /openai\/|anthropic\/|gpt-6/);
});

// Text guards only: passing these does not demonstrate defect-finding quality.
test("analysis follows behavior and counterexamples rather than procedural completion", () => {
  for (const marker of [
    "Analysis comes before report formatting",
    "expected behavior",
    "delayed or duplicate events",
    "focus/selection",
    "channel/platform branches",
    "counterexample",
    "later watcher or callback repairs",
    "source reasoning from runtime observation",
  ]) {
    assert.ok(system.includes(marker), marker);
  }
  assert.ok(system.indexOf("Analysis comes before") < system.indexOf("When a fingerprint"));
  assert.match(command, /Do not send the whole command or the parent's recovery ledger/);
  assert.match(command, /configured reviewer's system prompt owns the analysis/);
  assert.match(command, /Apply your configured shared analysis\/evidence policy/);
  assert.doesNotMatch(command, /Seek a counterexample to safety claims/);
});

test("verdicts account for material contract questions without manufacturing defects", () => {
  // The shared reviewer owns this policy; the command validates report consistency.
  for (const marker of [
    "REQUEST_CHANGES",
    "material requirement",
    "optional improvements",
    "clarification",
    "not a confirmed defect",
  ]) {
    assert.ok(system.includes(marker), marker);
  }
  assert.match(system, /Do not infer a bug from missing tests alone/);
  assert.match(system, /accepted risk/);
  assert.match(command, /do not silently rewrite the child's verdict/);
});

test("handoff and review preserve evidence boundaries instead of widening acceptance", () => {
  for (const marker of [
    "Separate requirements/accepted exceptions from implementation observations",
    "which operation is skipped and which side effects still occur",
    "exit status and verification limits",
    "Do not call a failed check clean",
  ]) {
    assert.ok(command.includes(marker), marker);
  }
  for (const marker of [
    "Acceptance is effect-specific",
    "consistency, not product acceptance",
    "safe interleaving with new user input",
    "Preserve failure qualifiers",
    "failed or blocked is not clean",
    "without automatic severity escalation",
  ]) {
    assert.ok(system.includes(marker), marker);
  }
});

test("the command and reviewer expose the same review-policy revision", () => {
  for (const prompt of [command, analysis, system]) {
    assert.match(prompt, /^Review policy: evidence-v5\.$/m);
  }
  assert.match(command, /Include the review-policy revision in the handoff/);
});

test("ordinary review stays in the current conversation with no role, model or context switch", () => {
  for (const marker of [
    "An explicit ordinary review request",
    '"поревьюй"',
    "context, agent and model unchanged",
    "Do not launch a child, fork the session or",
    "temporarily switch roles merely to perform that review",
    "read `review-analysis.md` in OpenCode's active global",
    "respect `XDG_CONFIG_HOME`",
    "Route by intent, not keyword matching",
    "a future or negated request, ordinary implementation/debugging",
    "self-checks do not trigger a separate review workflow",
    "without explicit delegation also\n  stays in the current conversation",
    "do not maintain a second checklist here",
    "no fixes, builds, installation or commits",
    "keep active Plan restrictions intact",
  ]) {
    assert.ok(globalRules.includes(marker), marker);
  }
  assert.doesNotMatch(globalRules, /An explicit request to perform a review now/);
  assert.doesNotMatch(analysis, /The parent owns retry budgets|up to six further|You are a subagent/);
  assert.doesNotMatch(reviewer, /Before a blocking finding|Calibrate the verdict|Try a concrete counterexample/);
  assert.match(source("../default.nix"), /"opencode\/review-analysis\.md"\.source = \.\/config\/review-analysis\.md;/);
});

test("explicit delegation uses the installed workflow and a fresh configured reviewer", () => {
  for (const marker of [
    "Delegate only on an explicit request for a separate reviewer/delegated review",
    "applicable installed `commands/delegated-review.md` template",
    "without a model/provider/effort override",
    "parent session's agent and model unchanged",
    "If `review` is unavailable or delegation is forbidden",
    "do not launch\n  a second child",
    "Reviewers do not delegate\n  recursively",
    "Start a new delegated review task with a fresh child, without `sessionID`",
    "User cancellation\n  ends automatic recovery",
  ]) {
    assert.ok(globalRules.includes(marker), marker);
  }
  assert.match(command, /do not substitute `general`/);
  assert.doesNotMatch(command, /otherwise `general`/);
  assert.match(command, /ordinary review-request routing must not launch/);
  assert.match(source("../default.nix"), /"opencode\/AGENTS\.md"\.source = \.\/config\/AGENTS\.md;/);
});

test("delegated defaults and exact handoff remain explicit without a context-clearing layer", () => {
  const flat = command.replace(/\s+/g, " ");
  for (const marker of [
    "If arguments are empty or whitespace-only",
    "Explicit English or Russian arguments take precedence over defaults",
    "select Working tree below, not branch commits; do not combine the two scopes",
    "Otherwise select Current branch below",
    "State which default was selected and why",
    "Send the exact manifest JSON, diff argv and this recipe in the handoff",
    "Use a fresh native `subagent` without `sessionID` for the initial launch",
    "does not copy the parent's conversation",
    "no context-clearing step, fork or custom isolation layer is needed",
    "not a security sandbox",
    "Do not retrieve the parent's or unrelated sessions' history",
  ]) assert.ok(flat.includes(marker), marker);
  assert.match(reviewer, /Do not retrieve the parent's development conversation or unrelated session history/);
  assert.match(reviewer, /Read recorded history only when explicitly selected as review evidence/);
});

test("blocking findings and suggested fixes require causal evidence, not compulsory compilation", () => {
  for (const marker of [
    "Before a blocking finding, trace the complete relevant implementation path",
    "types/signatures and actual callers, wrappers, hosts/providers",
    "injected/default arguments and spread/override order",
    "A partial search cannot establish absence",
    "existing implementation could invalidate your finding",
    "evidence gap/question, not a demonstrated",
    "Use types to understand contracts, not as proof of runtime behavior",
    "Compilation is not mandatory for every review",
    "`--noEmit` may write incremental metadata",
    "neighboring success/cancel/error paths",
    "revalidate mutable state after an `await`",
    "Architecture/style preferences or a large function are not blockers",
    "do not promote an optional refactor merely to preserve rejection",
  ]) {
    assert.ok(system.includes(marker), marker);
  }
  assert.match(command, /blocking claim lacks its decisive implementation path/);
  assert.match(command, /request evidence or correction from the same child/);
});
