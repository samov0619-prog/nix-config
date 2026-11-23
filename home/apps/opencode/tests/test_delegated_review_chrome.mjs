import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  existsSync,
  lstatSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  statSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { test } from "node:test";
import { instructions } from "./instructions.mjs";

const source = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const command = source("../commands/delegated-review-chrome.md");
const flat = command.replace(/^> ?/gm, "").replace(/\s+/g, " ");
const shared = (
  source("../config/review-analysis.md") +
  "\n" +
  source("../config/review-system.md")
).replace(/\s+/g, " ");
const routing = instructions.home.replace(/\s+/g, " ");
const cases = JSON.parse(
  source("./fixtures/delegated-review-chrome/cases.json"),
);
const writeRecipe = command.match(
  /### Exclusive history write[\s\S]*?```python\n([\s\S]*?)\n```/,
)[1];

// Instruction guards, published write/hash recipes and fixture integrity; no model/browser.
test("Chrome command is self-contained, passive and installed without routing overrides", () => {
  const [, header, body] = command.split(/^---\n/m);
  assert.match(header, /^subagent: false$/m);
  assert.doesNotMatch(header, /^(agent|model|subtask):/m);
  assert.ok(body.includes("$ARGUMENTS"));
  assert.doesNotMatch(command, /!`|inherited unchanged/);
  assert.match(command, /^Audit policy: chrome-evidence-v3\.$/m);
  assert.ok(
    flat.includes(
      "Use configured `review` without a model/provider/effort override",
    ),
  );
  assert.ok(
    flat.includes("do not substitute `general` or the parent's own audit"),
  );
  assert.doesNotMatch(command, /otherwise `general`/);
  assert.ok(flat.includes("without a model/provider/effort override"));
  assert.ok(flat.includes("any browser interaction"));
  assert.ok(flat.includes("Do not edit, delegate, commit"));
  assert.ok(flat.includes("neither agent drives the browser"));
  assert.match(source("../default.nix"), /personal-layers\.nix/);
  assert.match(
    source("../config/personal-layers.nix"),
    /delegated-review-chrome/,
  );
});

test("ordinary audit intent selects the installed Chrome workflow once, not a generic review or live test", () => {
  for (const marker of [
    "Distinguish code review from an explicit request to audit",
    "parent must first read and follow an applicable project override, otherwise `~/.config/opencode-local/commands/delegated-review-chrome.md`",
    "using the user's evidence/run target as its arguments",
    "Do not launch an ordinary code-review child first",
    "invoke a slash command recursively",
    "If the applicable template is unavailable",
    "Preserve its export/privacy restrictions and native permissions",
    "Mentioning Chrome/MCP in a code task or requesting a live browser test does not select",
  ])
    assert.ok(routing.includes(marker), marker);
  assert.ok(
    flat.includes(
      "including when selected by an ordinary-language audit request",
    ),
  );
  assert.ok(
    flat.includes(
      "do not launch an additional reviewer through general review routing",
    ),
  );
});

test("the single shared reviewer respects the audit object rather than product-readiness criteria", () => {
  for (const marker of [
    "For a recorded-evidence audit, apply the supplied audit contract",
    "Source-review path/type requirements below apply only when source code is part of that scope",
    "do not demand source access, compilation or live re-testing",
    "requirement → recorded action → observed result → claim",
    "Use the audit contract's claim statuses, coverage rules and verdict criteria",
    "failing feature test can have SUPPORTED claims and an APPROVE audit",
    "Shared evidence, uncertainty and review-only rules still apply",
    "ground every decisive causal link in the scoped evidence, not another model's explanation",
    "establishes a change, not who caused it",
    "do not mark it supported while relegating necessary evidence to optional follow-up",
  ])
    assert.ok(shared.includes(marker), marker);
  assert.ok(flat.includes("not code-review or product-readiness criteria"));
});

test("Chrome audit keeps current-session/latest-run defaults and native fresh-context delegation", () => {
  for (const marker of [
    "Without a supplied session/export, use the current session before this invocation",
    "including empty or whitespace-only arguments",
    "select only the last recorded Chrome-MCP testing run in that source",
    "not the whole session or last successful run",
    "Explicit source/run boundaries take precedence",
    "fresh native `subagent` without `sessionID`, not a fork",
    "no context-clearing layer is needed",
    "not a security sandbox",
    "selected recorded history is deliberate audit evidence, not inherited chat",
    "must not fetch parent or unrelated session history beyond that evidence",
  ])
    assert.ok(flat.includes(marker), marker);
});

test("recovery never adopts an old cancelled reviewer as a new task", () => {
  const ordinary = source("../commands/delegated-review.md").replace(
    /\s+/g,
    " ",
  );
  for (const prompt of [flat, ordinary]) {
    for (const marker of [
      "Recovery applies only after this logical",
      "starts a fresh child without `sessionID`",
      "User cancellation ends automatic recovery",
      "explicit user request",
    ])
      assert.ok(prompt.includes(marker), marker);
  }
  assert.ok(flat.includes("never whole-child CLI exports or probe files"));
  assert.ok(
    flat.includes("the agent cannot relabel recovery or reset budgets itself"),
  );
  assert.ok(
    ordinary.includes("not whole-session CLI export probes or temporary files"),
  );
});

test("evidence acquisition has a completeness gate and a bounded non-file fallback", () => {
  for (const marker of [
    "Capture complete native responses in memory with their exit/error status",
    "do not suppress stderr or pipe JSON through head/tail",
    "Successful JSON parsing alone does not prove boundary, pagination or tool-result completeness",
    "switch once to supported paginated native message reads",
    "Do not loop whole-session export until it happens to parse",
    "Before the sole history write, verify the selected range/cutoff",
    "All acquisition, validation, filtering and secret redaction happen in memory",
    "No scratch/probe exports, including child-session exports for recovery",
    "If the final write fails, stop and disclose any partial artifact",
  ])
    assert.ok(flat.includes(marker), marker);
});

function withHistoryWriter(check) {
  const directory = mkdtempSync("/tmp/opencode/chrome-history-write-");
  const artifact = `${directory}/history.json`;
  const write = (path, payload) =>
    execFileSync(
      "python3",
      [
        "-B",
        "-c",
        "import sys\nartifact = sys.argv[1]\nhistory_bytes = sys.stdin.buffer.read()\n" +
          writeRecipe,
        path,
      ],
      { input: payload, stdio: "pipe", timeout: 5000 },
    );
  try {
    check({ directory, artifact, write });
  } finally {
    // Only this test's uniquely created directory and known fixtures.
    rmSync(directory, { recursive: true });
  }
}

test("published history-write recipe rejects truncated JSON before creating a file", () => {
  withHistoryWriter(({ artifact, write }) => {
    assert.throws(() =>
      write(artifact, Buffer.from('{"messages":[{"text":"cut')),
    );
    assert.equal(existsSync(artifact), false);
  });
});

test("published history-write recipe creates private exact bytes and refuses overwrite", () => {
  withHistoryWriter(({ artifact, write }) => {
    const payload = Buffer.from('{"messages":["scoped fixture"]}\n');
    write(artifact, payload);
    assert.deepEqual(readFileSync(artifact), payload);
    assert.equal(statSync(artifact).mode & 0o077, 0);
    assert.throws(() => write(artifact, Buffer.from('{"messages":[]}')));
    assert.deepEqual(readFileSync(artifact), payload);
  });
});

test("published history-write recipe refuses a symlink without changing its target", () => {
  withHistoryWriter(({ directory, artifact, write }) => {
    const target = `${directory}/existing.json`;
    const original = '{"messages":["existing"]}';
    writeFileSync(target, original, { mode: 0o600 });
    symlinkSync(target, artifact);
    assert.throws(() => write(artifact, Buffer.from('{"messages":[]}')));
    assert.equal(lstatSync(artifact).isSymbolicLink(), true);
    assert.equal(readFileSync(target, "utf8"), original);
  });
});

test("audit blockers require a full recorded path and counterevidence without re-testing", () => {
  for (const marker of [
    "Before a blocking audit finding, trace the decisive recorded path",
    "wrappers, targets, event order, authorized fixtures and later independent observations",
    "A partial record/search cannot establish absence or substitution",
    "claim-status/coverage rules below, not a demonstrated systemic blocker",
    "truthfully reported failed test is not an audit-integrity failure",
    "Verify that a blocking audit finding has its decisive recorded path",
    "request evidence or correction from the same child within the shared budget",
    "do not silently change its verdict or start live tests",
  ])
    assert.ok(flat.includes(marker), marker);
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
  ])
    assert.ok(flat.includes(marker), marker);
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
  ])
    assert.ok(flat.includes(marker), marker);
  assert.ok(
    flat.includes(
      "Never APPROVE/REQUEST_CHANGES/BLOCKER with incomplete coverage",
    ),
  );
});

test("Chrome recovery keeps the shared seven-call budget and native child identity", () => {
  for (const marker of [
    "sessionID",
    "up to six further invocations total",
    "Initialize at 0 only once",
    "0 used / 6 remaining",
    "additional_remaining = 6 - additional_used",
    "1/6 additional used, 5 remaining",
    "20, 40, 60, 90, 120, 120",
    "less than 10 minutes",
    "Never duplicate a prompt/child",
    "no recoverable child and no running invocation",
    "Do not silently rewrite the child's conclusions",
    "fingerprint clarification and report repair",
  ])
    assert.ok(flat.includes(marker), marker);
});

test("published drc-scope-v2 recipe is canonical and binds supporting evidence and limitations", () => {
  const recipe = command.match(/```python\n([\s\S]*?)\n```/)[1];
  const bytes = Buffer.from('recorded evidence: "снимок"\n');
  const manifest = {
    schema: "drc-scope-v2",
    artifact: '/fixture/a"\\\né.json',
    files: [
      {
        path: '/fixture/a"\\\né.json',
        kind: "history",
        bytes: bytes.length,
        sha256: createHash("sha256").update(bytes).digest("hex"),
      },
    ],
    sources: [{ session: "ses_fixture", from: null, through: "e8" }],
    export: {
      method: "supplied synthetic fixture",
      redactions: [],
      limitations: [],
    },
    claims: [{ id: "c1", text: "Баннер показан.", ref: "e8" }],
    pages: ["https://example.invalid/"],
    unavailable: [],
    exclusions: [],
  };
  const sorted = (value) =>
    Array.isArray(value)
      ? value.map(sorted)
      : value && typeof value === "object"
        ? Object.fromEntries(
            Object.keys(value)
              .sort()
              .map((key) => [key, sorted(value[key])]),
          )
        : value;
  const ascii = JSON.stringify(sorted(manifest)).replace(
    /[\u007f-\uffff]/g,
    (char) => `\\u${char.charCodeAt(0).toString(16).padStart(4, "0")}`,
  );
  const expected = createHash("sha256").update(ascii, "ascii").digest("hex");
  const hash = (value) =>
    execFileSync(
      "python3",
      [
        "-B",
        "-c",
        "import sys, json\nmanifest = json.load(sys.stdin)\n" + recipe,
      ],
      { input: JSON.stringify(value), encoding: "utf8", timeout: 5000 },
    ).trim();
  assert.equal(hash(manifest), expected);
  assert.equal(
    hash(Object.fromEntries(Object.entries(manifest).reverse())),
    expected,
  );
  for (const mutate of [
    (m) => {
      m.files[0].sha256 = "0".repeat(64);
    },
    (m) => {
      m.files.push({
        path: "/fixture/image.png",
        kind: "image",
        bytes: 3,
        sha256: "1".repeat(64),
      });
    },
    (m) => {
      m.export.redactions.push("e2: cookie removed");
    },
    (m) => {
      m.unavailable.push("missing required video");
    },
    (m) => {
      m.sources[0].through = "e9";
    },
    (m) => {
      m.claims[0].text += " All passed.";
    },
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
    assert.deepEqual(
      item.oracle.claims.map((claim) => claim.ref),
      item.events
        .filter((event) => event.actor === "model")
        .map((event) => event.id),
    );
    for (const claim of item.oracle.claims) {
      assert.ok(
        ["SUPPORTED", "CONTRADICTED", "CONTAMINATED", "UNVERIFIED"].includes(
          claim.status,
        ),
      );
      statuses.add(claim.status);
      assert.ok(claim.reason.length > 30);
      assert.ok(claim.evidence.length > 0);
      for (const ref of claim.evidence)
        assert.ok(
          ids.indexOf(ref) >= 0 && ids.indexOf(ref) < ids.indexOf(claim.ref),
        );
    }
    if (item.oracle.coverage === "INCOMPLETE")
      assert.equal(item.oracle.verdict, null);
    else if (item.oracle.verdict === "APPROVE")
      assert.ok(
        item.oracle.claims.every((claim) => claim.status === "SUPPORTED"),
      );
    else assert.equal(item.oracle.verdict, "REQUEST_CHANGES");
  }
  assert.equal(statuses.size, 4);
});
