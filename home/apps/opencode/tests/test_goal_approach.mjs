// Text/placement guards only: these do not exercise model decisions.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const root = new URL("../", import.meta.url);
const read = (path) => readFileSync(new URL(path, root), "utf8");
const home = read("config/AGENTS.md");
const personal = read("macos/trf-review/opencode-local/AGENTS-personal.md");
const section = /^## Goals and Approach\n[\s\S]*?(?=^## )/m;
const goalPolicy = home.match(section)?.[0];

test("home and corporate personal rules carry the same bounded approach check", () => {
  assert.ok(goalPolicy);
  assert.equal(personal.match(section)?.[0], goalPolicy);
  assert.ok(read("default.nix").includes('"opencode/AGENTS.md".source = ./config/AGENTS.md;'));
  assert.doesNotMatch(read("macos/trf-review/opencode/AGENTS.md"), /## Goals and Approach/);
});

test("the approach check preserves experimentation, informed choice and permissions", () => {
  const text = goalPolicy.replace(/\s+/g, " ");
  for (const marker of [
    "Before materially increasing complexity or scope",
    "an existing capability, a more direct approach or a smaller change",
    "coverage, limitations and unverified assumptions",
    "do not turn each routine local decision into research or a request for confirmation",
    "Simplicity is a preference, not a veto",
    "Learning, experimentation, convenience, control and independence",
    "Clarify only a consequential unresolved choice",
    "without repeating settled objections unless new material facts appear",
    "does not waive project constraints, permissions",
  ]) {
    assert.ok(text.includes(marker), marker);
  }
});

test("corporate personal rules preserve the exact trf baseline outside the two personal additions", () => {
  const baseline = personal.replace(section, "").replace(/^## Review Workflows\n[\s\S]*?(?=^## )/m, "");
  assert.notEqual(baseline, personal);
  assert.equal(
    createHash("sha256").update(baseline).digest("hex"),
    "66dd884afc079aaa5a7276b8fb31a3bc35f8aa68020b152de111f1b6c3308bf4",
  );
});
