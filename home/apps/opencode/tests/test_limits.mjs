import "./plugin-loader.mjs";
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  mkdtemp,
  readFile,
  readdir,
  rm,
  stat,
  writeFile,
} from "node:fs/promises";
import { join } from "node:path";
import { coalescedWriter } from "../plugins/limits/writer.ts";
import {
  budgetMode,
  checkpointKey,
  checkpointRequest,
  emptyBudget,
  parseUsage,
  recover,
  resetBudget,
  thresholds,
  windowMode,
} from "../plugins/limits/policy.ts";
const { setup } = await import("../plugins/limits/index.ts");

const tick = () => new Promise((resolve) => setImmediate(resolve));
function usage(
  primary = 68,
  secondary = 24,
  reset = Math.floor(Date.now() / 1000) + 3600,
) {
  return {
    email: "PRIVATE",
    account_id: "PRIVATE",
    rate_limit: {
      primary_window: {
        used_percent: 100 - primary,
        limit_window_seconds: 18000,
        reset_at: reset,
      },
      secondary_window: {
        used_percent: 100 - secondary,
        limit_window_seconds: 604800,
        reset_at: reset + 86400,
      },
    },
  };
}

test("real-shaped WHAM percentages, unknown data and independent windows", () => {
  const sample = parseUsage(usage(68, 3), 1000);
  assert.equal(sample.windows[0].remaining, 68);
  assert.equal(sample.windows[1].remaining, 3);
  assert.ok(!JSON.stringify(sample).includes("PRIVATE"));
  assert.equal(parseUsage({}), undefined);
  assert.equal(
    parseUsage({
      rate_limit: {
        primary_window: {
          used_percent: -1,
          limit_window_seconds: 1,
          reset_at: 10,
        },
      },
    }),
    undefined,
  );
  assert.equal(
    parseUsage({
      rate_limit: {
        primary_window: {
          used_percent: "10",
          limit_window_seconds: 1,
          reset_at: 10,
        },
      },
    }),
    undefined,
  );
  const state = emptyBudget();
  recover(state, sample);
  assert.equal(budgetMode(state, 1), "warn");
  assert.equal(
    budgetMode(state, 3),
    "wrap",
    "weekly window limits three workers",
  );
  assert.equal(
    budgetMode(state, 0),
    "wrap",
    "finishing all sessions does not clear guard",
  );
  assert.equal(
    budgetMode(emptyBudget(), 3),
    "normal",
    "unknown is not fabricated exhaustion",
  );
  assert.deepEqual(
    [1, 2, 3].map((active) => thresholds(active)),
    [
      { wrap: 15, warn: 25 },
      { wrap: 20, warn: 30 },
      { wrap: 25, warn: 35 },
    ],
  );
});

test("weekly thresholds scale the observed 3/22 ratio and retain worker dependence", () => {
  assert.deepEqual(
    [0, 1, 2, 3, 4].map((active) => thresholds(active, 604800)),
    [
      { wrap: 2, warn: 3 },
      { wrap: 2, warn: 3 },
      { wrap: 3, warn: 4 },
      { wrap: 3, warn: 5 },
      { wrap: 4, warn: 5 },
    ],
  );
  assert.deepEqual(thresholds(100), { wrap: 50, warn: 60 });
  assert.deepEqual(thresholds(100, 604800), { wrap: 7, warn: 8 });
  for (const [active, remaining, expected] of [
    [1, 4, "normal"],
    [1, 3, "warn"],
    [1, 2, "wrap"],
    [2, 5, "normal"],
    [2, 4, "warn"],
    [2, 3, "wrap"],
    [3, 6, "normal"],
    [3, 5, "warn"],
    [3, 3, "wrap"],
  ]) {
    const state = emptyBudget();
    recover(state, parseUsage(usage(80, remaining)));
    assert.equal(
      budgetMode(state, active),
      expected,
      `${active} workers, week ${remaining}%`,
    );
  }
});

test("window markers independently reflect thresholds, persistent latches and manual dismissal", () => {
  const state = emptyBudget();
  const modes = () =>
    state.snapshot.windows.map((item) => windowMode(state, item, 2));
  for (const [primary, weekly, expected] of [
    [80, 80, ["normal", "normal"]],
    [30, 80, ["warn", "normal"]],
    [80, 4, ["normal", "warn"]],
    [30, 3, ["warn", "wrap"]],
    [20, 3, ["wrap", "wrap"]],
  ]) {
    recover(state, parseUsage(usage(primary, weekly)));
    budgetMode(state, 2);
    assert.deepEqual(modes(), expected);
  }
  recover(state, parseUsage(usage(80, 80)));
  budgetMode(state, 2);
  assert.deepEqual(
    modes(),
    ["wrap", "wrap"],
    "each existing latch keeps its own marker",
  );
  resetBudget(state, 2);
  assert.deepEqual(
    modes(),
    ["normal", "normal"],
    "manual override dismisses both markers",
  );
});

test("latch survives commits/count changes/reload; recovery needs a fresh renewal or >95%", () => {
  const state = emptyBudget();
  recover(state, parseUsage(usage(10, 2, 100), 50_000));
  assert.equal(budgetMode(state, 3), "wrap");
  const restored = JSON.parse(JSON.stringify(state));
  assert.equal(budgetMode(restored, 1), "wrap");
  recover(state, parseUsage(usage(95, 2, 100), 101_000));
  assert.ok(state.latched.primary_window, "95% is not >95%");
  recover(state, parseUsage(usage(96, 2, 100), 102_000));
  assert.equal(state.latched.primary_window, undefined);
  assert.ok(
    state.latched.secondary_window,
    "short-window reset cannot release weekly guard",
  );
  assert.equal(budgetMode(state, 1), "wrap");
  recover(state, parseUsage(usage(80, 80, 200_000), 200_000_000));
  assert.equal(
    budgetMode(state, 1),
    "normal",
    "new reset epoch works without observing 96–100%",
  );
});

test("manual override lasts for the limiting cycle, not the next request", () => {
  const state = emptyBudget();
  recover(state, parseUsage(usage(68, 3, 100), 50_000));
  budgetMode(state, 3);
  resetBudget(state, 3);
  assert.equal(budgetMode(state, 3), "normal");
  assert.equal(
    state.ignored.primary_window,
    undefined,
    "healthy windows remain protected",
  );
  recover(state, parseUsage(usage(68, 8, 100), 60_000));
  assert.equal(budgetMode(state, 3), "normal");
  recover(state, parseUsage(usage(5, 8, 100), 70_000));
  assert.equal(
    budgetMode(state, 3),
    "wrap",
    "another window can still become limiting",
  );
  recover(state, parseUsage(usage(100, 100, 200_000), 200_000_000));
  assert.equal(budgetMode(state, 3), "normal");
  recover(state, parseUsage(usage(100, 2, 200_000), 200_001_000));
  assert.equal(
    budgetMode(state, 3),
    "wrap",
    "next budget cycle is protected again",
  );
});

function stream() {
  const queue = [];
  let wake;
  let subscriptions = 0;
  let active = 0;
  return {
    get subscriptions() {
      return subscriptions;
    },
    get active() {
      return active;
    },
    send(event) {
      queue.push(event);
      wake?.();
    },
    subscribe({ signal }) {
      subscriptions++;
      signal.addEventListener("abort", () => wake?.(), { once: true });
      return (async function* () {
        active++;
        try {
          while (!signal.aborted) {
            if (queue.length) yield queue.shift();
            else
              await new Promise((resolve) => {
                wake = resolve;
              });
          }
        } finally {
          active--;
        }
      })();
    },
  };
}

function fixture(account = "PRIVATE-ACCOUNT") {
  const hooks = new Map();
  const tools = new Map();
  const sessions = new Map();
  const events = stream();
  let credential = {
    type: "oauth",
    methodID: "chatgpt-browser",
    access: "PRIVATE-TOKEN",
    metadata: { accountID: account },
  };
  let rpc;
  let disposed = 0;
  let emitted = 0;
  const registration = () => ({
    async dispose() {
      disposed++;
    },
  });
  const ctx = {
    integration: {
      connection: {
        async active() {
          return { type: "credential", id: "cred_private" };
        },
        async resolve() {
          return credential;
        },
      },
    },
    rpc: {
      async register(_definition, handlers) {
        rpc = handlers;
        return {
          ...registration(),
          events: {
            async emit() {
              emitted++;
            },
          },
        };
      },
    },
    session: {
      async hook(name, handler) {
        hooks.set(name, handler);
        return registration();
      },
      async get({ sessionID }) {
        if (!sessions.has(sessionID))
          sessions.set(sessionID, {
            id: sessionID,
            metadata: { unrelated: "keep" },
          });
        return sessions.get(sessionID);
      },
      async update({ sessionID, metadata }) {
        sessions.set(sessionID, { id: sessionID, metadata });
      },
    },
    tool: {
      async hook(name, handler) {
        hooks.set(name, handler);
        return registration();
      },
      async transform(callback) {
        callback({
          add(tool) {
            tools.set(tool.name, tool);
          },
        });
        return registration();
      },
    },
    event: events,
  };
  return {
    ctx,
    hooks,
    tools,
    sessions,
    events,
    set credential(value) {
      credential = value;
    },
    get rpc() {
      return rpc;
    },
    get disposed() {
      return disposed;
    },
    get emitted() {
      return emitted;
    },
  };
}

function request(sessionID, providerID = "openai") {
  return {
    sessionID,
    agent: "build",
    model: { providerID, id: "model" },
    system: [],
  };
}

test("server integration: shared TTL/cache, dynamic workers/waits, checkpoint report, privacy, cleanup", async () => {
  const directory = await mkdtemp("/tmp/opencode/limits-");
  const oldState = process.env.XDG_STATE_HOME;
  const oldFetch = globalThis.fetch;
  process.env.XDG_STATE_HOME = directory;
  let calls = 0;
  globalThis.fetch = async (url, options) => {
    calls++;
    assert.equal(url, "https://chatgpt.com/backend-api/wham/usage");
    assert.equal(
      options.redirect,
      "error",
      "credentials never follow redirects",
    );
    assert.equal(options.headers.authorization, "Bearer PRIVATE-TOKEN");
    return Response.json(usage(68, 3));
  };
  const one = fixture();
  const two = fixture();
  let stopOne, stopTwo;
  try {
    stopOne = await setup(one.ctx);
    stopTwo = await setup(two.ctx);
    await Promise.all([one.rpc.status({}), two.rpc.status({})]);
    assert.equal(calls, 1, "one request across locations/TUIs");
    await one.hooks.get("context")(request("ses_one"));
    await two.hooks.get("context")(request("ses_two"));
    const third = request("ses_three");
    await one.hooks.get("context")(third);
    assert.deepEqual(
      third.system,
      [],
      "budget observation adds no model instructions",
    );
    assert.equal((await one.rpc.status({})).mode, "wrap");
    assert.deepEqual((await one.rpc.status({})).windowModes, {
      primary_window: "normal",
      secondary_window: "wrap",
    });
    assert.deepEqual((await one.rpc.status({})).thresholds, [
      { key: "primary_window", wrap: 25, warn: 35 },
      { key: "secondary_window", wrap: 3, warn: 5 },
    ]);
    await one.hooks.get("execute.before")({
      tool: "subagent",
      sessionID: "ses_one",
      id: "child-tool",
    });
    assert.equal(
      (await one.rpc.status({})).active,
      2,
      "parent waiting on child does not double-count",
    );
    one.events.send({
      type: "permission.asked",
      data: { sessionID: "ses_two", id: "permission" },
    });
    await tick();
    assert.equal((await one.rpc.status({})).active, 1);
    one.events.send({
      type: "permission.replied",
      data: { sessionID: "ses_two", requestID: "permission" },
    });
    await tick();
    assert.equal((await one.rpc.status({})).active, 2);
    one.events.send({
      type: "form.created",
      data: { form: { sessionID: "ses_two", id: "form" } },
    });
    await tick();
    assert.equal((await one.rpc.status({})).active, 1);
    one.events.send({
      type: "form.cancelled",
      data: { sessionID: "ses_two", id: "form" },
    });
    await tick();
    await one.hooks.get("execute.after")({
      tool: "subagent",
      sessionID: "ses_one",
      id: "child-tool",
    });
    assert.equal((await one.rpc.status({})).active, 3);
    await one.hooks.get("context")(request("ses_three", "opencode"));
    assert.equal(
      (await one.rpc.status({})).active,
      2,
      "free provider stops consuming this account",
    );
    const ready = one.tools.get("checkpoint_ready");
    await assert.rejects(
      ready.execute({ reviewPassed: false }, { sessionID: "ses_one" }),
      /reviewed handoff/,
    );
    await ready.execute(
      {
        summary: "Coherent text checkpoint",
        review: "Reviewed; fixed issue; repeat review found no blockers",
        checks: "Unit checks passed; target UI not tested",
        resume: "Continue with integration validation",
        reviewPassed: true,
        commit: "No Git: text handoff",
      },
      { sessionID: "ses_one" },
    );
    assert.equal(
      one.sessions.get("ses_one").metadata[checkpointKey].ready,
      true,
    );
    assert.equal(one.sessions.get("ses_one").metadata.unrelated, "keep");
    assert.equal(
      (await one.rpc.status({})).mode,
      "wrap",
      "checkpoint commit/report does not clear quota latch",
    );
    const afterReady = request("ses_one");
    await one.hooks.get("context")(afterReady);
    assert.deepEqual(
      afterReady.system,
      [],
      "even a completed checkpoint injects no stop instruction",
    );
    await one.hooks.get("prompt")({ sessionID: "ses_one" });
    assert.equal(
      one.sessions.get("ses_one").metadata[checkpointKey].ready,
      false,
    );
    await one.rpc.reset({});
    assert.equal((await one.rpc.status({})).mode, "normal");
    assert.deepEqual((await one.rpc.status({})).windowModes, {
      primary_window: "normal",
      secondary_window: "normal",
    });
    assert.equal(
      calls,
      1,
      "no model/tool/lifecycle event triggers redundant quota fetches",
    );
    const files = await readdir(join(directory, "opencode/limits"));
    assert.equal(files.length, 1);
    const file = join(directory, "opencode/limits", files[0]);
    const text = await readFile(file, "utf8");
    assert.ok(!text.includes("PRIVATE"));
    assert.equal((await stat(file)).mode & 0o777, 0o600);
    assert.equal(
      (await stat(join(directory, "opencode/limits"))).mode & 0o777,
      0o700,
    );
    assert.match(checkpointRequest, /review again/);
    assert.match(checkpointRequest, /Plan mode do not edit or commit/);
    assert.ok(one.emitted > 0);
  } finally {
    await stopOne?.();
    await stopTwo?.();
    assert.equal(one.disposed, 7);
    oldState === undefined
      ? delete process.env.XDG_STATE_HOME
      : (process.env.XDG_STATE_HOME = oldState);
    globalThis.fetch = oldFetch;
    // Clear only this test's in-memory plugin singleton, never persistent user state.
    const shared = globalThis[Symbol.for("local.limits.v1")];
    shared.pools.clear();
    shared.workers.clear();
    await rm(directory, { recursive: true });
  }
});

test("token sharing: no quota requests/cache, active workers and checkpoint remain available", async () => {
  const directory = await mkdtemp("/tmp/opencode/limits-sharing-");
  const oldState = process.env.XDG_STATE_HOME;
  const oldFetch = globalThis.fetch;
  process.env.XDG_STATE_HOME = directory;
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    throw new Error("Token-sharing quota must not be fetched");
  };
  const sample = fixture();
  sample.credential = {
    type: "oauth",
    methodID: "chatgpt-token-sharing",
    access: "PRIVATE-SHARING-TOKEN",
  };
  const shared = globalThis[Symbol.for("local.limits.v1")];
  let stop;
  try {
    stop = await setup(sample.ctx);
    assert.deepEqual(await sample.rpc.status({}), {
      available: false,
      reason: "token-sharing-quota-unavailable",
      active: 0,
      mode: "normal",
      windowModes: {},
      thresholds: [],
      snapshot: null,
    });
    const event = request("ses_sharing");
    Object.freeze(event.system);
    await sample.hooks.get("context")(event);
    assert.equal((await sample.rpc.status({})).active, 1);
    assert.deepEqual(await sample.rpc.reset({}), { reset: false });
    await sample.hooks.get("experimental.ws.receive")({
      ...event,
      frame: JSON.stringify({ type: "codex.rate_limits", ...usage(1, 1) }),
    });
    assert.equal(shared.pools.size, 0, "no incompatible cache read or write");
    assert.deepEqual(await readdir(directory), []);
    assert.equal(calls, 0, "no legacy HTTP request or credential fallback");
    sample.events.send({
      type: "form.created",
      data: { form: { sessionID: event.sessionID, id: "form" } },
    });
    await tick();
    assert.equal((await sample.rpc.status({})).active, 0);
    sample.events.send({
      type: "form.replied",
      data: { sessionID: event.sessionID, id: "form" },
    });
    await tick();
    assert.equal((await sample.rpc.status({})).active, 1);
    await sample.tools.get("checkpoint_ready").execute(
      {
        summary: "Text boundary",
        review: "Review, fixes and repeat review complete",
        checks: "Mock checks only; live token sharing not checked",
        resume: "Verify target UI",
        reviewPassed: true,
        commit: "No Git: fixture",
      },
      { sessionID: event.sessionID },
    );
    assert.equal(
      sample.sessions.get(event.sessionID).metadata[checkpointKey].ready,
      true,
    );
    await sample.hooks.get("prompt")({ sessionID: event.sessionID });
    assert.equal(
      sample.sessions.get(event.sessionID).metadata[checkpointKey].ready,
      false,
    );
    sample.events.send({
      type: "session.execution.succeeded",
      data: { sessionID: event.sessionID },
    });
    await tick();
    assert.equal((await sample.rpc.status({})).active, 0);
    assert.equal(calls, 0);
  } finally {
    await stop?.();
    await tick();
    oldState === undefined
      ? delete process.env.XDG_STATE_HOME
      : (process.env.XDG_STATE_HOME = oldState);
    globalThis.fetch = oldFetch;
    shared.pools.clear();
    shared.workers.clear();
    await rm(directory, { recursive: true });
  }
});

test("credential switches refresh clients, hide legacy snapshots/latches and restore the selected account", async () => {
  const directory = await mkdtemp("/tmp/opencode/limits-switch-");
  const oldState = process.env.XDG_STATE_HOME;
  const oldFetch = globalThis.fetch;
  process.env.XDG_STATE_HOME = directory;
  let calls = 0;
  globalThis.fetch = async (_url, options) => {
    calls++;
    assert.equal(options.headers.authorization, "Bearer PRIVATE-TOKEN");
    return Response.json(usage(1, 1));
  };
  const sample = fixture("switch-account");
  const shared = globalThis[Symbol.for("local.limits.v1")];
  const legacy = (accountID) => ({
    type: "oauth",
    methodID: "chatgpt-browser",
    access: "PRIVATE-TOKEN",
    metadata: { accountID },
  });
  const switched = async () => {
    sample.events.send({
      type: "credential.switched",
      data: { integrationID: "openai" },
    });
    await tick();
  };
  let stop;
  try {
    stop = await setup(sample.ctx);
    await sample.hooks.get("context")(request("ses_switch"));
    assert.equal((await sample.rpc.status({})).mode, "wrap");
    assert.equal(calls, 1);
    await tick();
    const before = sample.emitted;
    sample.events.send({
      type: "credential.switched",
      data: { integrationID: "other" },
    });
    await tick();
    assert.equal(
      sample.emitted,
      before,
      "unrelated provider switch is ignored",
    );
    // Even matching account metadata must never expose a legacy pool in sharing mode.
    sample.credential = {
      ...legacy("switch-account"),
      methodID: "chatgpt-token-sharing",
    };
    await switched();
    assert.equal(
      sample.emitted,
      before + 1,
      "switch invalidates connected clients without a model call",
    );
    const unsupported = await sample.rpc.status({});
    assert.equal(unsupported.reason, "token-sharing-quota-unavailable");
    assert.equal(unsupported.snapshot, null);
    assert.deepEqual(unsupported.windowModes, {});
    assert.equal(unsupported.mode, "normal");
    const [pool] = shared.pools.values();
    const previous = JSON.stringify(pool.state);
    const files = await readdir(join(directory, "opencode/limits"));
    const file = join(directory, "opencode/limits", files[0]);
    const previousFile = await readFile(file, "utf8");
    await sample.hooks.get("context")(request("ses_switch"));
    await sample.hooks.get("experimental.ws.receive")({
      ...request("ses_switch"),
      frame: JSON.stringify({ type: "codex.rate_limits", ...usage(99, 99) }),
    });
    assert.deepEqual(await sample.rpc.reset({}), { reset: false });
    assert.equal(JSON.stringify(pool.state), previous);
    assert.equal(await readFile(file, "utf8"), previousFile);
    assert.equal(calls, 1);
    sample.credential = legacy("switch-account");
    await switched();
    assert.equal(
      (await sample.rpc.status({})).mode,
      "wrap",
      "original account latch is preserved",
    );
    assert.equal(calls, 1, "return to legacy reuses its valid TTL cache");
    sample.credential = legacy("different-account");
    await switched();
    const other = await sample.rpc.status({});
    assert.equal(other.available, true);
    assert.equal(other.active, 0, "old account workers are not reassigned");
    assert.equal(calls, 2, "new legacy account gets its own snapshot");
    assert.equal(shared.pools.size, 2);
  } finally {
    await stop?.();
    await tick();
    oldState === undefined
      ? delete process.env.XDG_STATE_HOME
      : (process.env.XDG_STATE_HOME = oldState);
    globalThis.fetch = oldFetch;
    shared.pools.clear();
    shared.workers.clear();
    await rm(directory, { recursive: true });
  }
});

test("a legacy quota response in flight cannot restore percentages after switching credentials", async () => {
  const directory = await mkdtemp("/tmp/opencode/limits-inflight-switch-");
  const oldState = process.env.XDG_STATE_HOME;
  const oldFetch = globalThis.fetch;
  process.env.XDG_STATE_HOME = directory;
  let release, started;
  globalThis.fetch = async () => {
    started();
    await new Promise((resolve) => {
      release = resolve;
    });
    return Response.json(usage(4, 3));
  };
  const sample = fixture("inflight-account");
  const shared = globalThis[Symbol.for("local.limits.v1")];
  let stop;
  try {
    stop = await setup(sample.ctx);
    for (const [index, replacement] of [
      {
        type: "oauth",
        methodID: "chatgpt-token-sharing",
        access: "PRIVATE-SHARING",
      },
      {
        type: "oauth",
        methodID: "chatgpt-browser",
        access: "PRIVATE-TOKEN",
        metadata: { accountID: "other-inflight-account" },
      },
    ].entries()) {
      sample.credential = {
        type: "oauth",
        methodID: "chatgpt-browser",
        access: "PRIVATE-TOKEN",
        // Each request needs an uncached origin so it really enters fetch.
        metadata: { accountID: `inflight-account-${index}` },
      };
      const fetching = new Promise((resolve) => {
        started = resolve;
      });
      const status = sample.rpc.status({});
      await fetching;
      sample.credential = replacement;
      sample.events.send({
        type: "credential.switched",
        data: { integrationID: "openai" },
      });
      release();
      release = undefined;
      const result = await status;
      assert.equal(result.available, false);
      assert.equal(
        result.snapshot ?? null,
        null,
        "never expose the old request's percentages",
      );
      if (replacement.methodID === "chatgpt-token-sharing")
        assert.equal(result.reason, "token-sharing-quota-unavailable");
    }
  } finally {
    release?.();
    await stop?.();
    await tick();
    oldState === undefined
      ? delete process.env.XDG_STATE_HOME
      : (process.env.XDG_STATE_HOME = oldState);
    globalThis.fetch = oldFetch;
    shared.pools.clear();
    shared.workers.clear();
    await rm(directory, { recursive: true });
  }
});

test("one lifecycle observer: unrelated event storms, duplicate changes and owner handover", async () => {
  const directory = await mkdtemp("/tmp/opencode/limits-events-");
  const oldState = process.env.XDG_STATE_HOME;
  const oldFetch = globalThis.fetch;
  process.env.XDG_STATE_HOME = directory;
  globalThis.fetch = async () => Response.json(usage(80, 80));
  const one = fixture("event-account");
  const two = fixture("event-account");
  const shared = globalThis[Symbol.for("local.limits.v1")];
  const emissions = () => one.emitted + two.emitted;
  let stopOne, stopTwo;
  try {
    stopOne = await setup(one.ctx);
    stopTwo = await setup(two.ctx);
    assert.equal(one.events.subscriptions, 1);
    assert.equal(
      two.events.subscriptions,
      0,
      "locations share one global stream",
    );
    await one.hooks.get("context")(request("ses_events"));
    await tick();
    let before = emissions();
    for (let i = 0; i < 1000; i++) {
      one.events.send({
        type: "message.part.text.delta",
        data: { sessionID: `ses_noise_${i}` },
      });
      one.events.send({ type: "rpc.local.limits.updated", data: {} });
    }
    one.events.send({
      type: "session.metadata.updated",
      data: { sessionID: "ses_events" },
    });
    one.events.send({
      type: "session.execution.started",
      data: { sessionID: "ses_events" },
    });
    await tick();
    assert.equal(
      shared.workers.size,
      1,
      "ignored events cannot allocate phantom workers",
    );
    assert.equal(
      emissions(),
      before,
      "ignored events cannot trigger RPC feedback loops",
    );
    await one.hooks.get("context")(request("ses_events"));
    await two.hooks.get("context")(request("ses_events"));
    await tick();
    assert.equal(
      emissions(),
      before,
      "unchanged context hooks do not refresh every client",
    );

    for (let i = 0; i < 100; i++)
      one.events.send({
        type: "permission.asked",
        data: { sessionID: "ses_events", id: "wait" },
      });
    await tick();
    assert.equal(
      emissions(),
      ++before,
      "one notification, not one per event or location",
    );
    assert.equal((await two.rpc.status({})).active, 0);
    one.events.send({
      type: "form.created",
      data: { form: { sessionID: "ses_events", id: "form" } },
    });
    one.events.send({
      type: "permission.replied",
      data: { sessionID: "ses_events", requestID: "wait" },
    });
    await tick();
    assert.equal(
      emissions(),
      before,
      "still waiting: visible count has not changed",
    );

    // A parent waiting on both a form and a child still counts as one wait.
    await one.hooks.get("execute.before")({
      tool: "subagent",
      sessionID: "ses_events",
      id: "child",
    });
    one.events.send({
      type: "form.replied",
      data: { sessionID: "ses_events", id: "form" },
    });
    await tick();
    assert.equal(emissions(), before);
    await one.hooks.get("execute.after")({
      tool: "subagent",
      sessionID: "ses_events",
      id: "child",
    });
    await tick();
    assert.equal(emissions(), ++before);

    await stopOne();
    stopOne = undefined;
    await tick();
    assert.equal(one.events.active, 0);
    assert.equal(two.events.active, 1);
    assert.equal(
      two.events.subscriptions,
      1,
      "remaining setup takes stream ownership",
    );
    assert.equal(
      (await two.rpc.status({})).active,
      1,
      "handover retains shared workers",
    );
    two.events.send({
      type: "session.execution.succeeded",
      data: { sessionID: "ses_events" },
    });
    two.events.send({
      type: "session.execution.succeeded",
      data: { sessionID: "ses_events" },
    });
    await tick();
    assert.equal(emissions(), ++before);
    assert.equal((await two.rpc.status({})).active, 0);
    assert.equal(shared.workers.size, 0);
    await stopTwo();
    stopTwo = undefined;
    await tick();
    assert.equal(two.events.active, 0);
    assert.equal(shared.listeners.size, 0);
    assert.equal(shared.observer, undefined);
  } finally {
    await stopOne?.();
    await stopTwo?.();
    await tick();
    oldState === undefined
      ? delete process.env.XDG_STATE_HOME
      : (process.env.XDG_STATE_HOME = oldState);
    globalThis.fetch = oldFetch;
    shared.pools.clear();
    shared.workers.clear();
    await rm(directory, { recursive: true });
  }
});

test("writer coalesces bursts into latest state with one write in flight", async () => {
  let value = 0,
    concurrent = 0,
    maximum = 0;
  const written = [];
  let release;
  const save = coalescedWriter(async () => {
    maximum = Math.max(maximum, ++concurrent);
    written.push(value);
    if (written.length === 1)
      await new Promise((resolve) => {
        release = resolve;
      });
    concurrent--;
  });
  const drain = save();
  for (let i = 1; i <= 1000; i++) {
    value = i;
    assert.equal(save(), drain);
  }
  await tick();
  assert.deepEqual(
    written,
    [1000],
    "serialize only when writing, not when enqueuing",
  );
  for (let i = 1001; i <= 2000; i++) {
    value = i;
    assert.equal(save(), drain);
  }
  release();
  await drain;
  assert.deepEqual(
    written,
    [1000, 2000],
    "slow sink retains no queue of obsolete snapshots",
  );
  assert.equal(maximum, 1);
  value = 2001;
  const next = save();
  assert.notEqual(next, drain);
  await next;
  assert.deepEqual(written, [1000, 2000, 2001]);
});

test("writer can drain again after a rejected write", async () => {
  let attempts = 0;
  const save = coalescedWriter(async () => {
    if (++attempts === 1) throw new Error("storage unavailable");
  });
  await assert.rejects(save(), /storage unavailable/);
  await save();
  assert.equal(attempts, 2);
});

test("a second window latch is persisted even when the overall mode is unchanged", async () => {
  const directory = await mkdtemp("/tmp/opencode/limits-latch-");
  const oldState = process.env.XDG_STATE_HOME;
  const oldFetch = globalThis.fetch;
  process.env.XDG_STATE_HOME = directory;
  globalThis.fetch = async () => Response.json(usage(80, 80));
  const sample = fixture("second-latch-account");
  const stop = await setup(sample.ctx);
  try {
    for (const id of ["ses_latch", "ses_wait1", "ses_wait2"])
      await sample.hooks.get("context")(request(id));
    for (const id of ["ses_wait1", "ses_wait2"])
      await sample.hooks.get("execute.before")({
        tool: "subagent",
        sessionID: id,
        id: "child",
      });
    await sample.hooks.get("experimental.ws.receive")({
      ...request("ses_latch"),
      frame: JSON.stringify({ type: "codex.rate_limits", ...usage(10, 3) }),
    });
    await sample.hooks.get("context")(request("ses_latch"));
    const cacheDirectory = join(directory, "opencode/limits");
    const [file] = await readdir(cacheDirectory);
    const cache = async () =>
      JSON.parse(await readFile(join(cacheDirectory, file), "utf8"));
    const before = await cache();
    assert.ok(before.latched.primary_window);
    assert.equal(before.latched.secondary_window, undefined);
    for (const id of ["ses_wait1", "ses_wait2"])
      await sample.hooks.get("execute.after")({
        tool: "subagent",
        sessionID: id,
        id: "child",
      });
    await sample.hooks.get("context")(request("ses_latch"));
    const after = await cache();
    assert.equal(
      after.notices,
      undefined,
      "obsolete model-notice bookkeeping is not persisted",
    );
    assert.ok(
      after.latched.secondary_window,
      "the new independent latch must survive reload",
    );
  } finally {
    await stop();
    oldState === undefined
      ? delete process.env.XDG_STATE_HOME
      : (process.env.XDG_STATE_HOME = oldState);
    globalThis.fetch = oldFetch;
    const shared = globalThis[Symbol.for("local.limits.v1")];
    shared.pools.clear();
    shared.workers.clear();
    await rm(directory, { recursive: true });
  }
});

test("legacy cache preserves latches across reload but drops obsolete model notices", async () => {
  const directory = await mkdtemp("/tmp/opencode/limits-");
  const oldState = process.env.XDG_STATE_HOME;
  const oldFetch = globalThis.fetch;
  process.env.XDG_STATE_HOME = directory;
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return Response.json(usage(10, 80));
  };
  let stop;
  try {
    const first = fixture("reload-account");
    stop = await setup(first.ctx);
    await first.hooks.get("context")(request("ses_reload"));
    assert.equal((await first.rpc.status({})).mode, "wrap");
    await stop();
    stop = undefined;
    const cacheDirectory = join(directory, "opencode/limits");
    const [file] = await readdir(cacheDirectory);
    const path = join(cacheDirectory, file);
    const legacy = JSON.parse(await readFile(path, "utf8"));
    legacy.latched.secondary_window = legacy.snapshot.windows[1].resetAt;
    legacy.notices = { ses_reload: "old-weekly-wrap-notice" };
    await writeFile(path, JSON.stringify(legacy));
    globalThis[Symbol.for("local.limits.v1")].pools.clear();
    const second = fixture("reload-account");
    stop = await setup(second.ctx);
    assert.equal((await second.rpc.status({})).mode, "wrap");
    assert.equal(calls, 1);
    const pool = globalThis[Symbol.for("local.limits.v1")].pools
      .values()
      .next().value;
    assert.ok(
      pool.state.latched.secondary_window,
      "threshold changes do not silently release a previous latch",
    );
    assert.equal(pool.state.notices, undefined);
    // A hot reload can also inherit an older pool object, not just a disk file.
    pool.state.notices = { ses_reload: "obsolete in-memory notice" };
    await second.rpc.reset({});
    assert.equal((await second.rpc.status({})).mode, "normal");
    assert.equal(JSON.parse(await readFile(path, "utf8")).notices, undefined);
  } finally {
    await stop?.();
    oldState === undefined
      ? delete process.env.XDG_STATE_HOME
      : (process.env.XDG_STATE_HOME = oldState);
    globalThis.fetch = oldFetch;
    const shared = globalThis[Symbol.for("local.limits.v1")];
    shared.pools.clear();
    shared.workers.clear();
    await rm(directory, { recursive: true });
  }
});

test("normal, warning and reserve observations never modify model instructions or read checkpoint metadata", async () => {
  const directory = await mkdtemp("/tmp/opencode/limits-no-injection-");
  const oldState = process.env.XDG_STATE_HOME;
  const oldFetch = globalThis.fetch;
  process.env.XDG_STATE_HOME = directory;
  globalThis.fetch = async () => Response.json(usage(80, 80));
  const sample = fixture("no-injection-account");
  sample.ctx.session.get = async () => {
    throw Error("observation must not read session metadata");
  };
  const stop = await setup(sample.ctx);
  try {
    for (const [remaining, mode] of [
      [80, "normal"],
      [25, "warn"],
      [15, "wrap"],
    ]) {
      await sample.hooks.get("context")(request("ses_observed"));
      await sample.hooks.get("experimental.ws.receive")({
        ...request("ses_observed"),
        frame: JSON.stringify({
          type: "codex.rate_limits",
          ...usage(remaining, 80),
        }),
      });
      for (let i = 0; i < 2; i++) {
        const system = Object.freeze([
          { type: "text", text: "Existing project instructions" },
        ]);
        const event = { ...request("ses_observed"), system };
        await sample.hooks.get("context")(event);
        assert.equal(event.system, system);
        assert.deepEqual(event.system, [
          { type: "text", text: "Existing project instructions" },
        ]);
        assert.equal((await sample.rpc.status({})).mode, mode);
      }
    }
  } finally {
    await stop();
    oldState === undefined
      ? delete process.env.XDG_STATE_HOME
      : (process.env.XDG_STATE_HOME = oldState);
    globalThis.fetch = oldFetch;
    const shared = globalThis[Symbol.for("local.limits.v1")];
    shared.pools.clear();
    shared.workers.clear();
    await rm(directory, { recursive: true });
  }
});

test("partially failed plugin setup disposes registrations and event listener", async () => {
  const sample = fixture();
  sample.ctx.session.hook = async () => {
    throw new Error("hook registration failed");
  };
  const shared = globalThis[Symbol.for("local.limits.v1")];
  const before = shared.listeners.size;
  await assert.rejects(setup(sample.ctx), /hook registration failed/);
  assert.equal(sample.disposed, 1, "RPC registration cleaned up");
  assert.equal(shared.listeners.size, before);
});

test("session without metadata admits prompts and tools without budget instructions and can create/reset a checkpoint", async () => {
  const directory = await mkdtemp("/tmp/opencode/limits-no-metadata-");
  const oldState = process.env.XDG_STATE_HOME;
  const oldFetch = globalThis.fetch;
  process.env.XDG_STATE_HOME = directory;
  globalThis.fetch = async () => Response.json(usage(10, 80));
  const sample = fixture("no-metadata-account");
  const id = "ses_no_metadata";
  // Session.Info.metadata is optional in the pinned V2 schema. Existing sessions
  // without it caused prompt admission to return HTTP 500 in the real server.
  sample.sessions.set(id, { id });
  const stop = await setup(sample.ctx);
  try {
    await sample.hooks.get("prompt")({ sessionID: id });
    assert.equal(
      sample.sessions.get(id).metadata,
      undefined,
      "no eager metadata write on an ordinary prompt",
    );
    await sample.hooks.get("execute.before")({
      tool: "read",
      sessionID: id,
      id: "read",
    });
    const event = request(id);
    await sample.hooks.get("context")(event);
    assert.deepEqual(event.system, []);
    assert.equal((await sample.rpc.status({})).mode, "wrap");
    assert.equal(sample.sessions.get(id).metadata, undefined);

    const ready = sample.tools.get("checkpoint_ready");
    assert.equal(
      ready.options.codemode,
      false,
      "handoff instructions require a directly callable tool",
    );
    const handoff = {
      summary: "Reviewed fixture handoff",
      review: "No known blockers",
      checks: "Fixture only; installed runtime not tested",
      resume: "Validate in the target runtime",
      reviewPassed: true,
      commit: "No Git: fixture handoff",
    };
    await ready.execute(handoff, { sessionID: id });
    assert.equal(sample.sessions.get(id).metadata[checkpointKey].ready, true);
    const afterReady = request(id);
    await sample.hooks.get("context")(afterReady);
    assert.deepEqual(afterReady.system, []);
    await sample.hooks.get("prompt")({ sessionID: id });
    assert.equal(sample.sessions.get(id).metadata[checkpointKey].ready, false);

    await ready.execute(handoff, { sessionID: id });
    await sample.hooks.get("execute.before")({
      tool: "read",
      sessionID: id,
      id: "continued",
    });
    assert.equal(sample.sessions.get(id).metadata[checkpointKey].ready, false);
  } finally {
    await stop();
    oldState === undefined
      ? delete process.env.XDG_STATE_HOME
      : (process.env.XDG_STATE_HOME = oldState);
    globalThis.fetch = oldFetch;
    const shared = globalThis[Symbol.for("local.limits.v1")];
    shared.pools.clear();
    shared.workers.clear();
    await rm(directory, { recursive: true });
  }
});

test("unknown/error responses never invent quota; failure cooldown and WS reuse", async () => {
  const directory = await mkdtemp("/tmp/opencode/limits-");
  const oldState = process.env.XDG_STATE_HOME;
  const oldFetch = globalThis.fetch;
  process.env.XDG_STATE_HOME = directory;
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return new Response("PRIVATE", { status: 401 });
  };
  const fixtureOne = fixture("another-private-account");
  const stop = await setup(fixtureOne.ctx);
  try {
    const status = await fixtureOne.rpc.status({});
    assert.equal(status.snapshot, null);
    assert.equal(status.mode, "normal");
    await fixtureOne.hooks.get("context")(request("ses_ws"));
    await fixtureOne.rpc.status({});
    assert.equal(calls, 1, "failed endpoint does not cause a retry storm");
    const frame = JSON.stringify({
      type: "codex.rate_limits",
      rate_limits: {
        primary: {
          used_percent: 20,
          window_minutes: 300,
          resets_at: 9999999999,
        },
        secondary: {
          used_percent: 98,
          window_minutes: 10080,
          resets_at: 9999999999,
        },
      },
    });
    const event = { ...request("ses_ws"), frame };
    await fixtureOne.hooks.get("experimental.ws.receive")(event);
    assert.equal(event.frame, frame, "protocol frames are never modified");
    assert.equal(
      (await fixtureOne.rpc.status({})).snapshot.windows[1].remaining,
      2,
    );
    assert.equal((await fixtureOne.rpc.status({})).mode, "wrap");
    await fixtureOne.hooks.get("experimental.ws.receive")({
      ...event,
      frame: JSON.stringify({
        type: "codex.rate_limits",
        rate_limits: {
          primary: {
            used_percent: 5,
            window_minutes: 300,
            resets_at: 9999999999,
          },
        },
      }),
    });
    assert.equal(
      (await fixtureOne.rpc.status({})).snapshot.windows.length,
      2,
      "partial frames do not hide the known weekly window",
    );
    assert.equal(
      calls,
      1,
      "provider notification needs no extra HTTP or LLM call",
    );
  } finally {
    await stop();
    oldState === undefined
      ? delete process.env.XDG_STATE_HOME
      : (process.env.XDG_STATE_HOME = oldState);
    globalThis.fetch = oldFetch;
    const shared = globalThis[Symbol.for("local.limits.v1")];
    shared.pools.clear();
    shared.workers.clear();
    await rm(directory, { recursive: true });
  }
});
