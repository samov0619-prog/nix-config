import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const source = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const command = source("../commands/delegated-review-chrome.md");
const flat = command.replace(/^> ?/gm, "").replace(/\s+/g, " ");
const cases = JSON.parse(source("./fixtures/delegated-review-chrome/cases.json"));

// Instruction guards and fixture integrity only; no model/browser is executed.
test("Chrome command is self-contained, passive and installed without routing overrides", () => {
  const [, header, body] = command.split(/^---\n/m);
  assert.match(header, /^subagent: false$/m);
  assert.doesNotMatch(header, /^(agent|model|subtask):/m);
  assert.ok(body.includes("$ARGUMENTS"));
  assert.doesNotMatch(command, /!`|inherited unchanged/);
  assert.match(command, /^Audit policy: chrome-evidence-v1\.$/m);
  assert.ok(flat.includes("Use configured `review`, otherwise `general`"));
  assert.ok(flat.includes("without a model/provider/effort override"));
  assert.ok(flat.includes("any browser interaction"));
  assert.ok(flat.includes("Do not edit, delegate, commit"));
  assert.ok(flat.includes("neither agent drives the browser"));
  assert.match(source("../default.nix"), /"opencode\/commands\/delegated-review-chrome\.md"\.source = \.\/commands\/delegated-review-chrome\.md;/);
});

test("export exception is parent-only, private, immutable and bounded", () => {
  for (const marker of [
    "Exactly one parent-created history file",
    "create exclusively with owner-only access",
    "never overwrite an existing file",
    "No helper scripts, manifests, reports or new directories",
    "do not persist an unredacted intermediate",
    "request a sanitized replacement rather than rewriting the original",
    "Redaction is not guaranteed by a generic regex",
    "pagination and full tool arguments/results",
    "not cryptographic proof of honest testing",
    "Do not read or modify the session database or guess API endpoints",
    "do not mistake an opaque wrapper for no calls",
  ]) assert.ok(flat.includes(marker), marker);
});

test("audit distinguishes effect, legitimacy, evidence status and completeness", () => {
  for (const marker of [
    "observational, mutating or",
    "ordinary test interaction, authorized setup/fixture",
    "A read-only evaluate is",
    "mock-scoped rendering claim, not real-backend integration",
    "valid contrary evidence is CONTRADICTED",
    "sufficient valid evidence is SUPPORTED",
    "otherwise UNVERIFIED",
    "not infer deliberate deception, motive or blame",
    "not retroactively validate an earlier manufactured observation",
    "INCOMPLETE — no final verdict",
    "a correctly documented failing feature test",
    "counts are not an integrity score",
    "property-specific assessments",
  ]) assert.ok(flat.includes(marker), marker);
  assert.ok(flat.includes("Never APPROVE/REQUEST_CHANGES/BLOCKER with incomplete coverage"));
});

test("Chrome recovery keeps the shared seven-call budget and native child identity", () => {
  for (const marker of [
    "sessionID", "up to six further invocations total",
    "Initialize at 0 only once", "0 used / 6 remaining",
    "additional_remaining = 6 - additional_used",
    "1/6 additional used, 5 remaining", "20, 40, 60, 90, 120, 120",
    "less than 10 minutes", "Never duplicate a prompt/child",
    "no recoverable child and no running invocation",
    "Do not silently rewrite the child's conclusions",
    "fingerprint clarification and report repair",
  ]) assert.ok(flat.includes(marker), marker);
});

test("published drc-scope-v2 recipe is canonical and binds supporting evidence and limitations", () => {
  const recipe = command.match(/```python\n([\s\S]*?)\n```/)[1];
  const bytes = Buffer.from('recorded evidence: "снимок"\n');
  const manifest = {
    schema: "drc-scope-v2", artifact: '/fixture/a"\\\né.json',
    files: [{ path: '/fixture/a"\\\né.json', kind: "history", bytes: bytes.length, sha256: createHash("sha256").update(bytes).digest("hex") }],
    sources: [{ session: "ses_fixture", from: null, through: "e8" }],
    export: { method: "supplied synthetic fixture", redactions: [], limitations: [] },
    claims: [{ id: "c1", text: "Баннер показан.", ref: "e8" }],
    pages: ["https://example.invalid/"], unavailable: [], exclusions: [],
  };
  const sorted = (value) => Array.isArray(value) ? value.map(sorted) : value && typeof value === "object" ? Object.fromEntries(Object.keys(value).sort().map((key) => [key, sorted(value[key])])) : value;
  const ascii = JSON.stringify(sorted(manifest)).replace(/[\u007f-\uffff]/g, (char) => `\\u${char.charCodeAt(0).toString(16).padStart(4, "0")}`);
  const expected = createHash("sha256").update(ascii, "ascii").digest("hex");
  const hash = (value) => execFileSync("python3", ["-B", "-c", "import sys, json\nmanifest = json.load(sys.stdin)\n" + recipe], { input: JSON.stringify(value), encoding: "utf8", timeout: 5000 }).trim();
  assert.equal(hash(manifest), expected);
  assert.equal(hash(Object.fromEntries(Object.entries(manifest).reverse())), expected);
  for (const mutate of [
    (m) => { m.files[0].sha256 = "0".repeat(64); },
    (m) => { m.files.push({ path: "/fixture/image.png", kind: "image", bytes: 3, sha256: "1".repeat(64) }); },
    (m) => { m.export.redactions.push("e2: cookie removed"); },
    (m) => { m.unavailable.push("missing required video"); },
    (m) => { m.sources[0].through = "e9"; },
    (m) => { m.claims[0].text += " All passed."; },
  ]) {
    const changed = structuredClone(manifest);
    mutate(changed);
    assert.notEqual(hash(changed), expected);
  }
});

test("synthetic oracles have stable event links, complete claim coverage and no incomplete verdicts", () => {
  assert.equal(cases.length, 8);
  assert.equal(new Set(cases.map((item) => item.id)).size, cases.length);
  const statuses = new Set();
  for (const item of cases) {
    assert.ok(["COMPLETE", "INCOMPLETE"].includes(item.oracle.coverage));
    const ids = item.events.map((event) => event.id);
    assert.equal(new Set(ids).size, ids.length);
    assert.deepEqual(item.oracle.claims.map((claim) => claim.ref), item.events.filter((event) => event.actor === "model").map((event) => event.id));
    for (const claim of item.oracle.claims) {
      assert.ok(["SUPPORTED", "CONTRADICTED", "CONTAMINATED", "UNVERIFIED"].includes(claim.status));
      statuses.add(claim.status);
      assert.ok(claim.reason.length > 30);
      assert.ok(claim.evidence.length > 0);
      for (const ref of claim.evidence) assert.ok(ids.indexOf(ref) >= 0 && ids.indexOf(ref) < ids.indexOf(claim.ref));
    }
    if (item.oracle.coverage === "INCOMPLETE") assert.equal(item.oracle.verdict, null);
    else if (item.oracle.verdict === "APPROVE") assert.ok(item.oracle.claims.every((claim) => claim.status === "SUPPORTED"));
    else assert.equal(item.oracle.verdict, "REQUEST_CHANGES");
  }
  assert.equal(statuses.size, 4);
});
