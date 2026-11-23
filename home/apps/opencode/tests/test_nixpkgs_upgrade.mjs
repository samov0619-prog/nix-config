// Source-level upgrade contracts, not a built OpenCode/real terminal test.
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
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import {
  canonicalModel,
  paidModels,
  routedModel,
  routingKey,
  routingState,
} from "../plugins/model-routing/model-routing.ts";

const moduleRoot = fileURLToPath(new URL("..", import.meta.url));
const upstream =
  process.env.OPENCODE_TEST_SOURCE ??
  execFileSync(
    "nix",
    [
      "eval",
      "--offline",
      "--raw",
      "--option",
      "allow-import-from-derivation",
      "false",
      "path:.#packages.x86_64-linux.opencode.src",
    ],
    { encoding: "utf8" },
  ).trim();
const directory = mkdtempSync("/tmp/opencode/nixpkgs-upgrade-");
let backend, compaction, question;
try {
  const patches = [
    "session-routing",
    "manual-model-routing",
    "model-variants",
    "session-attention",
    "question-location",
  ];
  const files = new Set(
    patches.flatMap((name) =>
      [
        ...readFileSync(
          join(moduleRoot, `patches/${name}.patch`),
          "utf8",
        ).matchAll(/^--- a\/(.+)$/gm),
      ].map((match) => match[1]),
    ),
  );
  for (const relative of files) {
    const target = join(directory, relative);
    mkdirSync(dirname(target), { recursive: true });
    copyFileSync(join(upstream, relative), target);
    chmodSync(target, 0o600);
  }
  for (const name of patches)
    execFileSync(
      "patch",
      [
        "--batch",
        "--fuzz=0",
        "-s",
        "-p1",
        "-i",
        join(moduleRoot, `patches/${name}.patch`),
      ],
      {
        cwd: directory,
        stdio: ["ignore", "pipe", "inherit"],
        encoding: "utf8",
      },
    );
  backend = readFileSync(
    join(directory, "packages/core/src/session/runner/model.ts"),
    "utf8",
  );
  compaction = readFileSync(
    join(directory, "packages/core/src/session/compaction.ts"),
    "utf8",
  );
  question = readFileSync(
    join(directory, "packages/core/src/tool/plugin/question.ts"),
    "utf8",
  );
} finally {
  rmSync(directory, { recursive: true, force: true });
}

function run(iterator) {
  let step;
  do {
    step = iterator.next();
  } while (!step.done);
  return step.value;
}
function result(value) {
  const iterator = (function* () {
    return value;
  })();
  iterator.pipe = (...operations) =>
    operations.reduce((input, operation) => operation(input), iterator);
  return iterator;
}
class SelectionError extends Error {
  constructor(data) {
    super(JSON.stringify(data));
    Object.assign(this, data);
  }
  *[Symbol.iterator]() {
    throw this;
  }
}
function extract(anchor, endMarker, name) {
  const anchorIndex = backend.indexOf(anchor);
  const start = backend.indexOf("function* (", anchorIndex);
  const end = backend.indexOf(endMarker, start);
  assert.ok(
    anchorIndex >= 0 && start > anchorIndex && end > start,
    "Review changed selection layout",
  );
  return stripTypeScriptTypes(
    backend.slice(start, end).replace("function* (", `function* ${name}(`) +
      "\n}",
  );
}
const selectCode = extract(
  'const select = Effect.fn("SessionRunnerModel.select")',
  "\n    })",
  "select",
);
const resolveCode = extract(
  'resolve: Effect.fn("SessionRunnerModel.resolve")',
  "\n      }),",
  "resolve",
);
const sol = { providerID: "openai", id: "gpt-6.1-sol", variant: "high" };
const pickle = { providerID: "opencode", id: "big-pickle" };
const catalog = [
  ...new Map(
    [sol, pickle, ...Object.values(paidModels)].map((ref) => [
      `${ref.providerID}/${ref.id}`,
      { ...ref, modelID: ref.id },
    ]),
  ).values(),
];
const policy = readFileSync(
  join(upstream, "packages/core/src/tool/model-policy.ts"),
  "utf8",
);
const modelTools = new Function(
  `${stripTypeScriptTypes(policy).replaceAll("export ", "")}\nreturn modelTools;`,
)();
// SessionContext passes catalog info, not a Model.Ref, to the native policy.
const hidden = (model) =>
  [
    ...modelTools({
      model: { ...model, modelID: model.modelID ?? model.id },
      websearch: true,
      fullCodeMode: false,
    }).hidden,
  ].sort();

function resolveFixture(metadata) {
  const hooks = [],
    initialized = [];
  const root = { id: "root", metadata };
  const child = {
    id: "child",
    parentID: "root",
    agent: "build",
    model: pickle,
    metadata: { [routingKey]: routingState("free") },
  };
  const sessions = new Map([
    ["root", root],
    ["child", child],
  ]);
  const store = { get: (id) => result(sessions.get(id)) };
  const resolver = {
    fallback: () => result(catalog[0]),
    resolveModel: (info, variant) => {
      initialized.push({ info, variant });
      return result({ providerID: info.providerID, id: info.id, variant });
    },
  };
  const nativeAgent = { id: "build", info: { model: sol } };
  const agents = { select: () => result(nativeAgent) };
  const Effect = { map: (fn) => (input) => result(fn(run(input))) };
  const Model = { Ref: { make: (value) => value } };
  const selectGenerator = new Function(
    "store",
    "canonicalModel",
    "routedModel",
    "Model",
    "agents",
    "resolver",
    "Effect",
    "ModelUnavailableError",
    "ModelNotSelectedError",
    `${selectCode}\nreturn select;`,
  )(
    store,
    canonicalModel,
    routedModel,
    Model,
    agents,
    resolver,
    Effect,
    SelectionError,
    SelectionError,
  );
  const select = (...args) => result(run(selectGenerator(...args)));
  const resolve = new Function(
    "Model",
    "select",
    "hooks",
    "resolver",
    `${resolveCode}\nreturn resolve;`,
  )(
    Model,
    select,
    {
      trigger: (...args) => {
        hooks.push(args);
        return result({ model: args[2].model });
      },
    },
    resolver,
  );
  const available = () => result(catalog);
  return {
    hooks,
    initialized,
    root,
    child,
    sessions,
    nativeAgent,
    select: (session = child, request) =>
      run(select(session, available, request)),
    run(request, session = child) {
      return run(resolve(session, available, request));
    },
  };
}

test("2.4 selection routes primary/title/compaction/generate before native provider hooks", () => {
  const metadata = { [routingKey]: routingState("paid") };
  const fixture = resolveFixture(metadata);
  for (const request of [
    { kind: "primary", agent: "build" },
    { kind: "primary", agent: "plan" },
    { kind: "primary", agent: "explore" },
    { kind: "title", agent: "title" },
    { kind: "compaction", agent: "compaction" },
    { kind: "generate", agent: "build" },
  ]) {
    const role = request.kind === "generate" ? "summary" : request.agent;
    const expected = routedModel(metadata, role, "child", "root");
    const value = fixture.run(request);
    assert.deepEqual(value, {
      providerID: expected.providerID,
      id: expected.id,
      variant: expected.variant,
    });
    assert.equal(fixture.hooks.at(-1)[2].kind, request.kind);
    assert.equal(fixture.hooks.at(-1)[2].agent, request.agent);
  }
  fixture.root.metadata = { [routingKey]: routingState("free") };
  assert.equal(
    fixture.run({ kind: "title", agent: "title" }).id,
    "big-pickle",
    "live root policy wins over a child's inherited metadata",
  );
});

test("legacy stored model aliases are canonicalized before native selection without history mutation", () => {
  const fixture = resolveFixture({});
  const session = {
    id: "legacy",
    model: { providerID: "openai", id: "gpt-6.1-sol-plan" },
  };
  const value = fixture.run({ kind: "primary", agent: "plan" }, session);
  const selected = fixture.select(session);
  assert.equal(value.id, "gpt-6.1-sol");
  assert.equal(value.variant, "xhigh");
  assert.equal(selected.info.id, value.id);
  assert.equal(selected.variant, value.variant);
  assert.equal(session.model.id, "gpt-6.1-sol-plan");
});

for (const [name, mode, stored, expected] of [
  ["stored Big Pickle / Paid", "paid", pickle, sol],
  ["stored Sol / Free", "free", sol, pickle],
]) {
  test(`tool preflight and request share effective selection: ${name}`, () => {
    const f = resolveFixture({ [routingKey]: routingState(mode) });
    const session = { id: "root", agent: "build", model: stored };
    const selected = f.select(session);
    assert.equal(f.hooks.length, 0, "preflight does not trigger model hooks");
    assert.equal(
      f.initialized.length,
      0,
      "preflight does not initialize a model",
    );
    const actual = f.run({ kind: "primary", agent: "build" }, session);
    assert.equal(selected.info.id, expected.id);
    assert.equal(actual.id, expected.id);
    assert.deepEqual(hidden(selected.info), hidden(actual));
    assert.notDeepEqual(
      hidden(stored),
      hidden(actual),
      "fixture crosses native editing-tool policies",
    );
    assert.equal(f.hooks.length, 1);
    assert.equal(f.initialized.length, 1);
    assert.deepEqual(
      session.model,
      stored,
      "selection does not migrate history",
    );
  });
}

test("Free family general child with configured Sol has Big Pickle tools and request", () => {
  const f = resolveFixture({ [routingKey]: routingState("free") });
  f.child.agent = "general";
  f.child.model = sol;
  const before = structuredClone(f.child);
  const selected = f.select();
  const actual = f.run({ kind: "primary", agent: "general" });
  assert.equal(selected.info.id, pickle.id);
  assert.equal(actual.id, pickle.id);
  assert.deepEqual(hidden(selected.info), hidden(actual));
  assert.deepEqual(f.child, before);
});

test("child role overrides, variants and live root switches apply to both selection paths", () => {
  const state = routingState("paid");
  state.overrides = {
    child: { build: pickle, plan: { ...sol, variant: "low" } },
  };
  const f = resolveFixture({ [routingKey]: state });
  f.child.model = sol;
  assert.equal(f.select().info.id, pickle.id);
  assert.deepEqual(
    hidden(f.select().info),
    hidden(f.run({ kind: "primary", agent: "build" })),
  );
  const plan = { kind: "primary", agent: "plan" };
  assert.equal(f.select(f.child, plan).variant, "low");
  assert.equal(f.run(plan).variant, "low");
  f.root.metadata = { [routingKey]: routingState("free") };
  assert.equal(f.select(f.child, plan).info.id, pickle.id);
  assert.equal(f.run(plan).id, pickle.id);
  f.root.metadata = { [routingKey]: routingState("paid") };
  assert.equal(f.select().info.id, sol.id);
  assert.equal(f.run({ kind: "primary", agent: "build" }).id, sol.id);
});

test("without a profile native agent selection remains; unavailable explicit models do not silently fall back", () => {
  const f = resolveFixture({});
  const session = { id: "root", agent: "general" };
  assert.equal(f.select(session).info.id, sol.id);
  assert.equal(
    f.run({ kind: "primary", agent: "general" }, session).id,
    sol.id,
  );
  const invalid = {
    ...session,
    model: { providerID: "opencode", id: "missing" },
  };
  assert.throws(() => f.select(invalid), SelectionError);
  assert.throws(
    () => f.run({ kind: "primary", agent: "general" }, invalid),
    SelectionError,
  );
});

test("sessions without a stored agent use the native default agent for tool policy and requests", () => {
  const f = resolveFixture({ [routingKey]: routingState("paid") });
  f.nativeAgent.id = "plan";
  const session = { id: "root", model: pickle };
  const selected = f.select(session);
  const actual = f.run({ kind: "primary", agent: "plan" }, session);
  assert.equal(
    selected.variant,
    "xhigh",
    "native default Plan must not use the Build wildcard effort",
  );
  assert.equal(actual.variant, selected.variant);
  assert.deepEqual(hidden(selected.info), hidden(actual));
});

test("compaction carries its own role and question retains an explicit Location", () => {
  assert.match(
    compaction,
    /kind: "compaction", agent: Agent\.ID\.make\("compaction"\)/,
  );
  assert.match(compaction, /model: agent\?\.model \?\? context\.model\.ref/);
  assert.match(
    question,
    /import \{ Location \} from "\.\.\/\.\.\/location\.js"/,
  );
  assert.match(
    question,
    /Effect\.provideService\(Location\.Service, ctx\.location\)/,
  );
});

test("native compaction keeps its provider/model identity while textual summaries use role routing", () => {
  const anchor = compaction.indexOf("const selectModel = Effect.fnUntraced(");
  const start = compaction.indexOf("function* (", anchor);
  const end = compaction.indexOf("\n    })", start);
  assert.ok(anchor >= 0 && start > anchor && end > start);
  const code = stripTypeScriptTypes(
    compaction
      .slice(start, end)
      .replace("function* (", "function* selectModel(") + "\n}",
  );
  const calls = [];
  let unavailable = false;
  const context = {
    session: { id: "root", agent: "explore" },
    model: { ref: paidModels.explore, limit: { input: 244000 } },
  };
  const select = new Function(
    "agents",
    "models",
    "catalog",
    "Agent",
    "calculateCeiling",
    "UNKNOWN_WINDOW",
    `${code}\nreturn selectModel;`,
  )(
    { get: () => result({ id: "compaction", model: sol }) },
    {
      resolve: (session, _available, request) => {
        calls.push({ session, request });
        if (unavailable) throw new SelectionError({ id: "missing" });
        return result({ ref: sol, limit: { input: 244000 } });
      },
    },
    { available: () => result(catalog) },
    { ID: { make: (value) => value } },
    (limit, buffer) => limit.input - buffer,
    200000,
  );
  const native = run(select(context, 32000, true));
  assert.equal(native.context.model, context.model);
  assert.equal(
    calls.length,
    0,
    "do not route encrypted native checkpoints through a helper identity",
  );
  assert.equal(run(select(context, 32000, false)).context.model.ref, sol);
  assert.deepEqual(calls[0].request, {
    kind: "compaction",
    agent: "compaction",
  });
  unavailable = true;
  assert.throws(
    () => run(select(context, 32000, false)),
    SelectionError,
    "invalid routed summaries fail closed; no silent model/provider fallback",
  );
  assert.equal(run(select(context, 32000, true)).context.model, context.model);
});

test("native terminal-title helper strips crash-triggering controls but preserves Unicode", () => {
  const source = readFileSync(
    join(upstream, "packages/tui/src/util/renderer.ts"),
    "utf8",
  );
  const start = source.indexOf("export function setTerminalTitle(");
  const end = source.indexOf("export function destroyRenderer(", start);
  assert.ok(start > 0 && end > start, "Review changed title helper layout");
  const code = stripTypeScriptTypes(
    source.slice(start, end).replace("export function", "function"),
  );
  const setTitle = new Function(
    "RendererControlState",
    `${code}\nreturn setTerminalTitle;`,
  )({ EXPLICIT_SUSPENDED: "suspended" });
  const titles = [];
  const renderer = { setTerminalTitle: (title) => titles.push(title) };
  setTitle(renderer, "Сброс клиентов после сбоя сервера\twg");
  setTitle(renderer, "日本語 🐈\n\t\x1b\x7f\x85test");
  assert.deepEqual(titles, [
    "Сброс клиентов после сбоя сервера wg",
    "日本語 🐈 test",
  ]);
  setTitle({ ...renderer, isDestroyed: true }, "ignored");
  setTitle({ ...renderer, controlState: "suspended" }, "ignored");
  assert.equal(titles.length, 2);
});

function packageFixture(version) {
  // Evaluate the actual local override with metadata only, never a derivation
  // build. The upstream fixture starts with nixpkgs' different channel default.
  return execFileSync(
    "nix",
    [
      "eval",
      "--offline",
      "--impure",
      "--json",
      "--expr",
      `
    let
      package = import ${JSON.stringify(join(moduleRoot, "package.nix"))} {
        upstream = {
          version = ${JSON.stringify(version)};
          overrideAttrs = f: f { env = { OPENCODE_CHANNEL = "latest"; KEEP_NATIVE_ENV = "yes"; }; };
        };
        pkgs.lib = {
          hasPrefix = prefix: value: builtins.substring 0 (builtins.stringLength prefix) value == prefix;
          assertMsg = predicate: message: if predicate then true else throw message;
        };
      };
    in { env = package.env; patches = map builtins.baseNameOf package.patches; }
  `,
    ],
    { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] },
  );
}

test("actual package override preserves the prod namespace and native build environment", () => {
  const value = JSON.parse(packageFixture("2.4.0+44aed4f"));
  assert.deepEqual(value.env, {
    OPENCODE_CHANNEL: "prod",
    KEEP_NATIVE_ENV: "yes",
  });
  assert.deepEqual(value.patches, [
    "session-routing.patch",
    "manual-model-routing.patch",
    "model-variants.patch",
    "session-attention.patch",
    "question-location.patch",
  ]);
});

test("other releases fail before patching instead of recommending a shared unstable update", () => {
  for (const version of ["2.2.5", "2.3.0", "2.4.1", "2.4.00"]) {
    assert.throws(
      () => packageFixture(version),
      (error) => {
        assert.match(String(error.stderr), /target upstream v2\.4\.0/);
        assert.match(String(error.stderr), /separate opencode input/);
        return true;
      },
    );
  }
});
