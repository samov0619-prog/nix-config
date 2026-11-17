// Instruction/source-wiring guards, not an executable source-selection engine.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { existsSync, lstatSync, readFileSync, readlinkSync, realpathSync } from "node:fs";
import { test } from "node:test";

import { badgeTone } from "./fixtures/review-requirements/candidate.mjs";

const root = new URL("../", import.meta.url);
const read = (path) => readFileSync(new URL(path, root), "utf8");
const compact = (text) => text.replace(/\s+/g, " ");
const analysis = compact(read("config/review-analysis.md"));
const command = compact(read("commands/delegated-review.md"));
const prep = "macos/trf-review/";
const corporateRaw = read(prep + "opencode/AGENTS.md");
const corporate = compact(corporateRaw);
const sha256 = (text) => createHash("sha256").update(text).digest("hex");

test("source policy is conditional on explicit instructions, never an MR/environment heuristic", () => {
  for (const marker of [
    "Requirements policy: sources-v1.",
    "explicit external-requirements rule in the applicable `AGENTS.md`",
    "An MR alone does not imply that a separate specification exists",
    "do not ask for a ticket or confirmation that no specification exists merely to review",
    "Ask about behavior only when an unresolved ambiguity materially affects review",
  ]) {
    assert.ok(analysis.includes(marker), marker);
  }
  assert.ok(corporate.includes("This rule comes from this `AGENTS.md`, not from the existence of an MR"));
  assert.ok(corporate.includes("A task's own substantive acceptance criteria may be the requirements"));
});

test("discovery validates task identity, selected target, contents and applicable revision", () => {
  for (const marker of [
    "Use an explicit user-supplied source first",
    "A source explicitly supplied or requested by the user is required within the agreed review scope",
    "Never use an unrelated checked-out branch or personal commit-style history",
    "not a matching number/title alone",
    "Do not invent a ticket prefix",
    "do not silently select the newest or first search result",
    "Read the relevant requirements and API/UI contracts, not only a search snippet",
    "do not guess tool names, enable disabled MCP servers",
    "Do not send private sources to public search",
  ]) {
    assert.ok(analysis.includes(marker), marker);
  }
});

test("required-source failures and scoped exceptions cannot silently become completed conformance", () => {
  for (const marker of [
    "required source not identified",
    "identified source unavailable or ambiguous",
    "before completing the review or launching a reviewer",
    "Name an access/permission failure",
    "must be explicitly agreed for this task",
    "do not ask again while that agreement remains applicable",
    "requirements gap without a final verdict",
    "checks the relevant source/excerpts",
    "not passive recorded-evidence audits",
  ]) {
    assert.ok(analysis.includes(marker), marker);
  }
});

test("delegated orchestration resolves sources before launch and preserves the manifest contract", () => {
  assert.ok(command.indexOf("## Resolve the requirements basis") < command.indexOf("## Compose a minimal handoff"));
  for (const marker of [
    "Requirements policy: sources-v1.",
    "active global config directory",
    "Before the initial reviewer launch",
    "before launch; do not spend child/recovery invocations discovering an unknown task",
    "not new fields in the `dr-scope-v1` manifest",
    "a ticket number or a document-read claim alone is not enough",
  ]) {
    assert.ok(command.includes(marker), marker);
  }
});

test("corporate AGENTS preserves the exact trf baseline outside source selection", () => {
  const withoutAddition = corporateRaw.replace(/## Requirements Sources\n[\s\S]*?(?=## Formatting\n)/, "");
  assert.notEqual(withoutAddition, corporateRaw);
  assert.equal(sha256(withoutAddition), "8307170553b228d7a8f6aa3838329730fee96aae7f5b128e2a10af009084b638");
});

test("corporate native reviewer keeps trf permissions/model inheritance and reads personal policies", () => {
  const agent = read(prep + "opencode-local/agents/review.md");
  const [, frontmatter, body] = agent.split(/^---\n/m);
  assert.equal(sha256(frontmatter), "6b1d124b2950982b9579ab7e34ac0c1f7581ac3a6253865dfb0de184253508ca");
  assert.doesNotMatch(frontmatter, /^model:/m);
  assert.ok(body.includes("`~/.config/opencode-local/review-analysis.md`"));
  assert.ok(body.includes("`~/.config/opencode-local/review-system.md`"));
  assert.doesNotMatch(body, /active global config/);
  assert.ok(body.includes("If either is unavailable"));
  assert.ok(body.includes("without a final verdict"));
});

test("source symlinks share current policies/commands and preserve team-to-personal placement", () => {
  const links = {
    "opencode-local/review-analysis.md": "../../../config/review-analysis.md",
    "opencode-local/review-system.md": "../../../config/review-system.md",
    "opencode-local/commands/delegated-review-chrome.md": "../../../../commands/delegated-review-chrome.md",
    "opencode/agents/review.md": "../../opencode-local/agents/review.md",
    "opencode/commands/delegated-review.md": "../../opencode-local/commands/delegated-review.md",
    "opencode/commands/delegated-review-chrome.md": "../../opencode-local/commands/delegated-review-chrome.md",
  };
  for (const [path, target] of Object.entries(links)) {
    const url = new URL(prep + path, root);
    assert.ok(lstatSync(url).isSymbolicLink(), path);
    assert.equal(readlinkSync(url), target);
    assert.ok(existsSync(url), path);
  }
  for (const [path, original] of [
    ["opencode/commands/delegated-review-chrome.md", "commands/delegated-review-chrome.md"],
  ]) {
    assert.equal(realpathSync(new URL(prep + path, root)), realpathSync(new URL(original, root)));
  }
  assert.equal(realpathSync(new URL(prep + "opencode/commands/delegated-review.md", root)), realpathSync(new URL(prep + "opencode-local/commands/delegated-review.md", root)));
  assert.equal(lstatSync(new URL(prep + "opencode-local/commands/delegated-review.md", root)).isSymbolicLink(), false);
  for (const path of ["opencode/review-analysis.md", "opencode/review-system.md"]) {
    assert.throws(() => lstatSync(new URL(prep + path, root)), { code: "ENOENT" });
  }
  for (const untouched of ["opencode-local/opencode.jsonc", "opencode/opencode.jsonc", "opencode/.git"]) {
    assert.equal(existsSync(new URL(prep + untouched, root)), false, untouched);
  }
});

test("team source selection has no personal workflow dependency; personal routing owns all review paths", () => {
  assert.doesNotMatch(corporateRaw, /review-analysis|review-system|delegated-review|opencode-local|Ordinary code review|Chrome-MCP/);
  const personal = read(prep + "opencode-local/AGENTS-personal.md");
  for (const path of ["review-analysis.md", "review-system.md", "commands/delegated-review.md", "commands/delegated-review-chrome.md"]) {
    assert.ok(personal.includes("~/.config/opencode-local/" + path), path);
  }
});

test("Mac code-review template differs from the shared template only in its personal policy location", () => {
  const before = "Before the initial reviewer launch, read `review-analysis.md` from OpenCode's\nactive global config directory (normally `~/.config/opencode`; respect\n`XDG_CONFIG_HOME`), unless already loaded and unchanged. If unavailable, report";
  const after = "Before the initial reviewer launch, read\n`~/.config/opencode-local/review-analysis.md` directly from the personal layer,\nunless already loaded and unchanged. If unavailable, report";
  const shared = read("commands/delegated-review.md");
  assert.equal(shared.split(before).length, 2);
  assert.equal(read(prep + "opencode-local/commands/delegated-review.md"), shared.replace(before, after));
});

test("synthetic target violates the documented result contract, not just a magic-number preference", () => {
  const spec = read("tests/fixtures/review-requirements/SPEC.md");
  assert.match(spec, /Show green for `success`, red for every other result/);
  assert.equal(badgeTone("success"), "red"); // Required green; deliberately defective fixture.
  assert.equal(badgeTone("rejected"), "red");
  assert.equal(badgeTone("error"), "red");
});
