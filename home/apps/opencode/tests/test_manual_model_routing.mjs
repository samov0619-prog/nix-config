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
  helperMode,
  routedModel,
  selectedRouting,
} from "../plugins/model-routing/model-routing.ts";

// Execute the actual upstream functions after patch application, not a second
// implementation of the selection rules. Full SDK/JSX verification requires PTY.
const directory = mkdtempSync("/tmp/opencode/manual-routing-test-");
let functions;
let chooser;
let providerSources;
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
  for (const relative of [
    "packages/tui/src/context/local.tsx",
    "packages/tui/src/component/dialog-model.tsx",
    "packages/tui/src/component/prompt/index.tsx",
    "packages/tui/src/app.tsx",
    "packages/core/src/session/runner/model.ts",
    "packages/core/src/session/context.ts",
    "packages/core/src/session/compaction.ts",
    "packages/core/src/session/generate.ts",
  ]) {
    const target = join(directory, relative);
    mkdirSync(join(target, ".."), { recursive: true });
    copyFileSync(join(upstream, relative), target);
    chmodSync(target, 0o600);
  }
  for (const name of [
    "session-routing",
    "manual-model-routing",
    "model-variants",
  ])
    execFileSync(
      "patch",
      [
        "--batch",
        "--fuzz=0",
        "-s",
        "-p1",
        "-i",
        join(process.cwd(), `home/apps/opencode/patches/${name}.patch`),
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
  chooser = stripTypeScriptTypes(
    source.slice(
      source.indexOf("      let helperDialog:"),
      source.indexOf("      let selecting = false"),
    ),
  );
  providerSources = {
    local: source,
    app: readFileSync(join(directory, "packages/tui/src/app.tsx"), "utf8"),
  };
  const variant = source.slice(
    source.indexOf("          async set(value:"),
    source.indexOf("          cycle()"),
  );
  functions += stripTypeScriptTypes(
    variant
      .trim()
      .replace(/^async set\(/, "async function setVariant(")
      .replace(/},$/, "}"),
  );
  assert.match(source, /model\.set\(selected, \{ preserveRouting: true \}\)/);
  assert.match(
    readFileSync(
      join(directory, "packages/tui/src/component/dialog-model.tsx"),
      "utf8",
    ),
    /await local\.model\.set/,
  );
  assert.match(source, /title: "Choose helper models"/);
  assert.match(source, /\(\) => resolve\(undefined\)/);
  assert.doesNotMatch(variant, /saveVariant|setPreferences/);
  assert.match(
    readFileSync(
      join(directory, "packages/tui/src/component/prompt/index.tsx"),
      "utf8",
    ),
    /metadata: local\.model\.routingMetadata\(\)/,
  );
  assert.match(
    readFileSync(
      join(directory, "packages/core/src/session/runner/model.ts"),
      "utf8",
    ),
    /routedModel\(root\.metadata, role, session\.id, root\.id\)/,
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
    helperMode,
    selectedRouting,
    helperChoice: "free",
    helperQuestions: 0,
    chooseHelperMode: async () => {
      context.helperQuestions++;
      return context.helperChoice;
    },
    routingMetadata: () => context.homeMetadata,
    homeMetadata: undefined,
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
    currentSelection: () => {
      const home = context.route.data.type === "home";
      const model = routedModel(
        home ? context.homeMetadata : sessions.get("root").metadata,
        context.agent.current().id,
        home ? "$root" : context.route.data.sessionID,
        home ? "$root" : "root",
      );
      return (
        model && {
          providerID: model.providerID,
          modelID: model.id,
          variant: model.variant,
        }
      );
    },
    normalizeModelVariant: (value) => (value === "default" ? undefined : value),
    models: () => context.catalog,
    catalog: [
      {
        providerID: "openai",
        id: "gpt-6.1-sol",
        variants: [{ id: "high" }, { id: "xhigh" }],
      },
      {
        providerID: "openai",
        id: "gpt-6-luna",
        variants: [{ id: "low" }, { id: "max" }],
      },
      { providerID: "opencode", id: "big-pickle", variants: [] },
      { providerID: "custom", id: "unknown", variants: [{ id: "high" }] },
    ],
    setSessionDraft: (id, selection) => drafts.push({ id, selection }),
    preferredSelection: (model) => ({
      ...model,
      variant: context.catalog.find(
        (item) =>
          item.providerID === model.providerID && item.id === model.modelID,
      )?.variants[0]?.id,
    }),
    locationAgentKey: (id) => id,
    setSelectionState: (key, _, value) => {
      if (key === "routingByLocation")
        context.homeMetadata = { [routingKey]: value };
      else drafts.push({ id: "home", selection: value });
    },
  };
  const api = new Function(
    ...Object.keys(context),
    `${functions}\nreturn { selectModel, manualSelection, setVariant };`,
  )(...Object.values(context));
  return { ...api, context, sessions, drafts, updates, toasts };
}
const chosen = { providerID: "openai", modelID: "gpt-6.1-sol" };

for (const mode of ["free", "paid"]) {
  test(`known model selects paid helpers from ${mode} without confirmation and preserves unrelated/child metadata`, async () => {
    const f = fixture(mode);
    assert.equal(await f.selectModel(chosen), true);
    assert.deepEqual(f.updates, ["root"]);
    assert.equal(f.sessions.get("root").metadata.unrelated, 7);
    assert.equal(f.sessions.get("root").metadata[routingKey].mode, "paid");
    assert.equal(f.context.helperQuestions, 0);
    assert.equal(
      routedModel(f.sessions.get("root").metadata, "build", "child", "root").id,
      chosen.modelID,
    );
    assert.equal(
      routedModel(f.sessions.get("root").metadata, "title", "child", "root").id,
      "gpt-6-luna",
    );
    assert.equal(f.sessions.get("child").metadata[routingKey].mode, "free");
    assert.deepEqual(f.drafts, [
      { id: "child", selection: { ...chosen, variant: "high" } },
    ]);
  });
}

test("agent switching preserves policy; explicit same-model selection refreshes its stack", async () => {
  const f = fixture();
  await f.selectModel(chosen, true);
  assert.deepEqual(f.updates, []);
  await f.selectModel({ providerID: "opencode", modelID: "big-pickle" });
  assert.deepEqual(f.updates, ["root"]);
  assert.equal(f.sessions.get("root").metadata[routingKey].mode, "free");
  assert.equal(f.context.helperQuestions, 0);
});

test("Big Pickle selects free helpers automatically, while a root selection stays local to the root agent", async () => {
  const f = fixture("paid");
  f.context.route.data = { type: "session", sessionID: "root" };
  assert.equal(
    await f.selectModel({ providerID: "opencode", modelID: "big-pickle" }),
    true,
  );
  assert.equal(f.sessions.get("root").metadata[routingKey].mode, "free");
  assert.equal(f.context.helperQuestions, 0);
  assert.equal(await f.selectModel(chosen), true);
  await f.setVariant("xhigh");
  const metadata = f.sessions.get("root").metadata;
  assert.equal(routedModel(metadata, "build", "root", "root").variant, "xhigh");
  assert.equal(routedModel(metadata, "build", "child", "root").variant, "high");
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

test("effort changes only the current agent, keeps helpers and does not save a global model preference", async () => {
  const f = fixture("paid");
  await f.setVariant("xhigh");
  const metadata = f.sessions.get("root").metadata;
  assert.equal(metadata[routingKey].mode, "paid");
  assert.equal(
    routedModel(metadata, "build", "child", "root").variant,
    "xhigh",
  );
  assert.equal(
    routedModel(metadata, "build", "sibling", "root").variant,
    "high",
  );
  assert.equal(routedModel(metadata, "plan", "child", "root").variant, "xhigh");
  assert.equal(
    routedModel(metadata, "compaction", "child", "root").variant,
    "high",
  );
  assert.equal(f.context.helperQuestions, 0);
  f.context.agent.current = () => ({ id: "plan" });
  await f.setVariant("high");
  assert.equal(
    routedModel(f.sessions.get("root").metadata, "build", "child", "root")
      .variant,
    "xhigh",
  );
  assert.equal(
    routedModel(f.sessions.get("root").metadata, "plan", "child", "root")
      .variant,
    "high",
  );
});

test("effort without a routing profile stays a native per-agent draft", async () => {
  const f = fixture("paid");
  f.sessions.get("root").metadata = { unrelated: 7 };
  await f.manualSelection({ ...chosen, variant: "xhigh" }, false);
  assert.deepEqual(f.updates, []);
  assert.equal(f.drafts[0].selection.variant, "xhigh");
});

test("unknown model asks for helpers; cancellation leaves metadata and drafts untouched", async () => {
  for (const mode of ["free", "paid", undefined]) {
    const f = fixture("paid");
    f.context.helperChoice = mode;
    const ok = await f.selectModel({
      providerID: "custom",
      modelID: "unknown",
    });
    assert.equal(f.context.helperQuestions, 1);
    assert.equal(ok, mode !== undefined);
    assert.equal(f.updates.length, mode === undefined ? 0 : 1);
    assert.equal(
      f.sessions.get("root").metadata[routingKey].mode,
      mode ?? "paid",
    );
    assert.equal(f.drafts.length, mode === undefined ? 0 : 1);
  }
});

test("missing helper model/variant fails closed without switching or paid fallback", async () => {
  for (const missing of ["gpt-6-luna", "big-pickle"]) {
    const f = fixture("paid");
    f.context.catalog = f.context.catalog.filter(
      (model) => model.id !== missing,
    );
    const target =
      missing === "big-pickle"
        ? { providerID: "opencode", modelID: missing }
        : chosen;
    assert.equal(await f.selectModel(target), false);
    assert.deepEqual(f.updates, []);
    assert.deepEqual(f.drafts, []);
    assert.equal(f.toasts.at(-1).variant, "error");
  }
});

test("home selection carries its helper stack and per-agent effort into session creation", async () => {
  const f = fixture("paid");
  f.context.route.data = { type: "home" };
  assert.equal(await f.selectModel(chosen), true);
  assert.equal(f.context.homeMetadata[routingKey].mode, "paid");
  assert.equal(await f.setVariant("xhigh"), true);
  assert.equal(
    routedModel(f.context.homeMetadata, "build", "new", "new").variant,
    "xhigh",
  );
  assert.equal(
    routedModel(f.context.homeMetadata, "plan", "new", "new").variant,
    "xhigh",
  );
  assert.equal(
    routedModel(f.context.homeMetadata, "build", "child", "new").variant,
    "high",
  );
  assert.deepEqual(f.updates, []);
});

test("effort alone on home does not introduce a helper policy or leak home policy into an existing session", async () => {
  const f = fixture("paid");
  f.context.route.data = { type: "home" };
  assert.equal(
    await f.manualSelection({ ...chosen, variant: "xhigh" }, false),
    true,
  );
  assert.equal(f.context.homeMetadata, undefined);
  assert.equal(f.drafts[0].selection.variant, "xhigh");
  f.context.homeMetadata = { [routingKey]: routingState("free") };
  f.sessions.get("root").metadata = undefined;
  f.context.route.data = { type: "session", sessionID: "root" };
  assert.equal(
    await f.manualSelection({ ...chosen, variant: "xhigh" }, false),
    true,
  );
  assert.deepEqual(f.updates, []);
  assert.equal(f.sessions.get("root").metadata, undefined);
});

test("overlapping selections and route changes do not apply stale drafts", async () => {
  const f = fixture();
  let release;
  f.context.data.session.sync = () =>
    new Promise((resolve) => {
      release = resolve;
    });
  const first = f.manualSelection({ ...chosen, variant: "high" }, true);
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

function chooserFixture() {
  return new Function(
    "createComponent",
    "DialogSelect",
    `${chooser}\nreturn { chooseHelperMode, bindHelperDialog };`,
  )(
    (_, value) => value,
    () => {},
  );
}

test("LocalProvider stays outside DialogProvider and receives its dialog from the nested App", () => {
  // LocalProvider initializes before DialogProvider. Calling useDialog there
  // crashes at startup, even though isolated selection/chooser tests pass.
  assert.ok(
    providerSources.app.indexOf("<LocalProvider>") <
      providerSources.app.indexOf("<DialogProvider>"),
  );
  assert.ok(
    providerSources.app.indexOf("<App />") >
      providerSources.app.indexOf("<DialogProvider>"),
  );
  assert.ok(
    providerSources.app.indexOf("<App />") <
      providerSources.app.indexOf("</DialogProvider>"),
  );
  assert.doesNotMatch(providerSources.local, /\buseDialog\b/);
  assert.match(
    providerSources.app,
    /const dialog = useDialog\(\)\s+const local = useLocal\(\)\s+onCleanup\(local\.model\.bindHelperDialog\(dialog\)\)/,
  );
});

test("helper chooser fails closed before binding and after cleanup; old cleanup preserves a newer binding", async () => {
  const f = chooserFixture();
  assert.equal(await f.chooseHelperMode(), undefined);
  const old = f.bindHelperDialog({
    replace: () => {
      throw Error("stale dialog");
    },
  });
  const current = f.bindHelperDialog({ replace: (_, close) => close() });
  old();
  assert.equal(await f.chooseHelperMode(), undefined);
  current();
  assert.equal(await f.chooseHelperMode(), undefined);
});

test("native helper chooser settles Free/Paid and Escape/replacement without an implicit choice", async () => {
  for (const choice of ["free", "paid", undefined]) {
    let props, close;
    const dialog = {
      replace: (render, onClose) => {
        props = render();
        close = onClose;
      },
      clear: () => close(),
    };
    const f = chooserFixture();
    const dispose = f.bindHelperDialog(dialog);
    const pending = f.chooseHelperMode();
    assert.deepEqual(
      props.options.map((option) => option.value),
      ["free", "paid"],
    );
    if (choice)
      props.onSelect(props.options.find((option) => option.value === choice));
    else close();
    assert.equal(await pending, choice);
    dispose();
  }
});

test("route or agent change while the unknown-model chooser is open does not mutate policy", async () => {
  for (const action of ["route", "agent"]) {
    const f = fixture("paid");
    f.context.helperChoice = "free";
    // The captured chooser reads this property when its asynchronous answer resolves.
    Object.defineProperty(f.context, "helperChoice", {
      get() {
        if (action === "route") f.context.route.data = { type: "home" };
        else f.context.agent.current = () => ({ id: "plan" });
        return "free";
      },
    });
    assert.equal(
      await f.selectModel({ providerID: "custom", modelID: "unknown" }),
      false,
    );
    assert.deepEqual(f.updates, []);
    assert.deepEqual(f.drafts, []);
  }
});
