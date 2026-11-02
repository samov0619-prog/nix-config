import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import {
  chmodSync,
  copyFileSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
} from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import { join } from "node:path";
import { test } from "node:test";
import {
  routing,
  routingKey,
  routingState,
} from "../plugins/model-routing/model-routing.ts";

// Execute the actual upstream functions after patch application, not a second
// implementation of the selection rules. Full SDK/JSX coverage is in the PTY.
const directory = mkdtempSync("/tmp/opencode/manual-routing-test-");
let functions;
try {
  const upstream =
    process.env.OPENCODE_TEST_SOURCE ??
    execFileSync(
      "nix",
      [
        "eval",
        "--offline",
        "--raw",
        "path:.#packages.x86_64-linux.opencode.src",
      ],
      { encoding: "utf8" },
    ).trim();
  for (const relative of ["context/local.tsx", "component/dialog-model.tsx"]) {
    const target = join(directory, "packages/tui/src", relative);
    mkdirSync(join(target, ".."), { recursive: true });
    copyFileSync(join(upstream, "packages/tui/src", relative), target);
    chmodSync(target, 0o600);
  }
  execFileSync(
    "patch",
    [
      "--batch",
      "--fuzz=0",
      "-s",
      "-p1",
      "-i",
      join(
        process.cwd(),
        "home/apps/opencode/patches/manual-model-routing.patch",
      ),
    ],
    { cwd: directory, encoding: "utf8" },
  );
  const source = readFileSync(
    join(directory, "packages/tui/src/context/local.tsx"),
    "utf8",
  );
  functions = stripTypeScriptTypes(
    source.slice(
      source.indexOf("      let selecting = false"),
      source.indexOf("      function reconcileSessionSelection"),
    ),
  );
  assert.match(source, /model\.set\(selected, \{ preserveRouting: true \}\)/);
  assert.match(
    readFileSync(
      join(directory, "packages/tui/src/component/dialog-model.tsx"),
      "utf8",
    ),
    /await local\.model\.set/,
  );
} finally {
  rmSync(directory, { recursive: true, force: true });
}

function fixture(mode = "free") {
  const sessions = new Map([
    [
      "root",
      {
        id: "root",
        metadata: { unrelated: 7, [routingKey]: routingState(mode) },
      },
    ],
    [
      "child",
      {
        id: "child",
        parentID: "root",
        metadata: { [routingKey]: routingState("free") },
      },
    ],
  ]);
  const route = { data: { type: "session", sessionID: "child" } };
  const drafts = [],
    updates = [],
    toasts = [];
  const invalidated = new Set();
  const context = {
    route,
    routing,
    routingKey,
    agent: { current: () => ({ id: "build" }) },
    client: {
      api: {
        session: {
          get: async ({ sessionID }) =>
            structuredClone(sessions.get(sessionID)),
          update: async ({ sessionID, metadata }) => {
            updates.push(sessionID);
            sessions.get(sessionID).metadata = metadata;
          },
        },
      },
    },
    data: {
      session: {
        invalidate: (id) => invalidated.add(id),
        sync: async (id) =>
          assert.ok(
            invalidated.delete(id),
            "sync must follow cache invalidation",
          ),
      },
    },
    toast: { show: (toast) => toasts.push(toast) },
    sessionSelection: () => ({ providerID: "opencode", modelID: "big-pickle" }),
    setSessionDraft: (id, selection) => drafts.push({ id, selection }),
    preferredSelection: (model) => ({ ...model, variant: "high" }),
    locationAgentKey: (id) => id,
    setSelectionState: () => {},
  };
  const api = new Function(
    ...Object.keys(context),
    `${functions}\nreturn { selectModel, manualSelection };`,
  )(...Object.values(context));
  return { ...api, context, sessions, drafts, updates, toasts };
}
const chosen = { providerID: "openai", modelID: "gpt-6.1-sol" };

for (const mode of ["free", "paid"]) {
  test(`manual selection exits ${mode} at the live root and preserves unrelated/child metadata`, async () => {
    const f = fixture(mode);
    assert.equal(await f.selectModel(chosen), true);
    assert.deepEqual(f.updates, ["root"]);
    assert.deepEqual(f.sessions.get("root").metadata, { unrelated: 7 });
    assert.equal(f.sessions.get("child").metadata[routingKey].mode, "free");
    assert.deepEqual(f.drafts, [
      { id: "child", selection: { ...chosen, variant: "high" } },
    ]);
  });
}

test("agent switching preserves policy; explicit same-model selection still exits it", async () => {
  const f = fixture();
  await f.selectModel(chosen, true);
  assert.deepEqual(f.updates, []);
  await f.selectModel({ providerID: "opencode", modelID: "big-pickle" });
  assert.deepEqual(f.updates, ["root"]);
});

test("lookup/write failures and cyclic ancestry do not apply a misleading draft; retry remains possible", async () => {
  for (const failure of ["lookup", "write", "cycle"]) {
    const f = fixture();
    const original =
      f.context.client.api.session[failure === "lookup" ? "get" : "update"];
    if (failure === "cycle") f.sessions.get("root").parentID = "child";
    else
      f.context.client.api.session[failure === "lookup" ? "get" : "update"] =
        async () => {
          throw Error(failure);
        };
    assert.equal(await f.selectModel(chosen), false);
    assert.equal(f.drafts.length, 0);
    assert.equal(f.toasts.at(-1).variant, "error");
    assert.equal(f.sessions.get("root").metadata[routingKey].mode, "free");
    if (failure === "cycle") delete f.sessions.get("root").parentID;
    else
      f.context.client.api.session[failure === "lookup" ? "get" : "update"] =
        original;
    assert.equal(await f.selectModel(chosen), true);
  }
});

test("variant changes share the exit path and overlapping selections do not race", async () => {
  const f = fixture();
  let release;
  f.context.data.session.sync = () =>
    new Promise((resolve) => {
      release = resolve;
    });
  const first = f.manualSelection("child", () => f.drafts.push("variant"));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(await f.selectModel(chosen), false);
  f.context.route.data = { type: "home" };
  release();
  await first;
  assert.equal(
    f.drafts.length,
    0,
    "late reply must not change the newly viewed session",
  );
});
