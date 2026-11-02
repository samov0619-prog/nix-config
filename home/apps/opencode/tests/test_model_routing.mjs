import assert from "node:assert/strict";
import { test } from "node:test";
import "./plugin-loader.mjs";
import {
  paidModels,
  canonicalModel,
  routingKey,
  routedModel,
  routingState,
} from "../plugins/model-routing/model-routing.ts";
const { setup } = await import("../plugins/model-routing/tui.ts");

function fixture() {
  const sessions = new Map([
    [
      "root",
      {
        id: "root",
        location: { directory: "/repo" },
        metadata: { unrelated: 7 },
      },
    ],
    [
      "child",
      {
        id: "child",
        parentID: "root",
        location: { directory: "/repo" },
        metadata: { [routingKey]: routingState("paid") },
      },
    ],
    ["other", { id: "other", location: { directory: "/other" } }],
  ]);
  const cache = new Map(
    [...sessions].map(([id, session]) => [id, structuredClone(session)]),
  );
  const invalidated = new Set();
  let commands;
  const context = {
    route: { type: "session", sessionID: "child" },
    toasts: [],
    updates: [],
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
    ],
    keymap: {
      layer(factory) {
        commands = factory().commands;
      },
    },
    ui: {
      router: {
        current: () => context.route,
        navigate: (route) => {
          context.route = route;
        },
      },
      toast: { show: (toast) => context.toasts.push(toast) },
    },
    data: {
      session: {
        get: (id) => cache.get(id),
        invalidate: (id) => invalidated.add(id),
        sync: async (id) => {
          if (!cache.has(id) || invalidated.delete(id))
            cache.set(id, structuredClone(sessions.get(id)));
        },
      },
      location: {
        default: () => ({ directory: "/repo" }),
        model: { sync: async () => {}, list: () => context.catalog },
      },
    },
    client: {
      session: {
        get: async ({ sessionID }) => structuredClone(sessions.get(sessionID)),
        update: async ({ sessionID, metadata }) => {
          context.updates.push(sessionID);
          sessions.get(sessionID).metadata = metadata;
        },
        create: async (input) => {
          const session = { id: "new", ...input };
          sessions.set(session.id, session);
          return session;
        },
      },
    },
  };
  const ready = setup(context);
  return {
    context,
    sessions,
    run: async (mode) => {
      await ready;
      return commands
        .find((command) => command.slash.name === `switch-${mode}`)
        .run();
    },
  };
}

test("switch from a child changes only root, preserves foreign metadata and survives reopen", async () => {
  const { context, sessions, run } = fixture();
  await run("free");
  assert.deepEqual(context.updates, ["root"]);
  const metadata = JSON.parse(JSON.stringify(sessions.get("root").metadata));
  assert.equal(metadata.unrelated, 7);
  for (const role of [
    "plan",
    "build",
    "explore",
    "title",
    "compaction",
    "summary",
    "future-agent",
  ]) {
    assert.deepEqual(routedModel(metadata, role), {
      providerID: "opencode",
      id: "big-pickle",
    });
  }
  assert.equal(sessions.get("other").metadata, undefined);
  await run("paid");
  assert.equal(
    routedModel(sessions.get("root").metadata, "plan").variant,
    "xhigh",
  );
  assert.equal(
    routedModel(sessions.get("root").metadata, "build").variant,
    "high",
  );
  assert.equal(
    routedModel(sessions.get("root").metadata, "title").variant,
    "low",
  );
});

test("missing free model leaves paid state unchanged; no automatic fallback", async () => {
  const { context, sessions, run } = fixture();
  context.catalog = context.catalog.filter(
    (model) => model.providerID !== "opencode",
  );
  await run("free");
  assert.deepEqual(context.updates, []);
  assert.equal(sessions.get("root").metadata[routingKey], undefined);
  assert.equal(context.toasts.at(-1).variant, "error");
});

test("each mode change invalidates hydrated TUI metadata before sync", async () => {
  const { context, run } = fixture();
  for (const mode of ["free", "paid", "free", "paid"]) {
    await run(mode);
    assert.equal(
      context.data.session.get("root").metadata[routingKey].mode,
      mode,
    );
  }
});

test("home command creates an empty routed session without a model request", async () => {
  const { context, sessions, run } = fixture();
  context.route = { type: "home" };
  await run("free");
  assert.deepEqual(context.route, { type: "session", sessionID: "new" });
  assert.equal(sessions.get("new").metadata[routingKey].mode, "free");
});

test("free to paid fails closed for an unavailable paid variant and succeeds after catalog recovery", async () => {
  const { context, sessions, run } = fixture();
  await run("free");
  const catalog = context.catalog;
  context.catalog = catalog.map((model) =>
    model.id === paidModels.plan.id
      ? {
          ...model,
          variants: model.variants.filter((variant) => variant.id !== "xhigh"),
        }
      : model,
  );
  await run("paid");
  assert.equal(sessions.get("root").metadata[routingKey].mode, "free");
  assert.match(context.toasts.at(-1).message, /Model unavailable:.*#xhigh/);
  context.catalog = catalog;
  for (const mode of ["paid", "free", "paid"]) {
    await run(mode);
    assert.equal(sessions.get("root").metadata[routingKey].mode, mode);
  }
});

test("cycles fail without mutation and malformed metadata is ignored", async () => {
  const { context, sessions, run } = fixture();
  sessions.get("root").parentID = "child";
  await run("paid");
  assert.deepEqual(context.updates, []);
  assert.equal(context.toasts.at(-1).variant, "error");
  for (const models of [null, [], 1, "bad"]) {
    assert.equal(
      routedModel(
        { [routingKey]: { version: 1, mode: "free", models } },
        "build",
      ),
      undefined,
    );
  }
});

test("roles share real model IDs with independent variants; old session aliases resolve without catalog entries", () => {
  assert.equal(paidModels.plan.id, paidModels["*"].id);
  assert.equal(paidModels.summary.id, paidModels["*"].id);
  assert.equal(paidModels.explore.id, paidModels.title.id);
  for (const [id, target, variant] of [
    ["gpt-6.1-sol-plan", "gpt-6.1-sol", "xhigh"],
    ["gpt-6.1-sol-high", "gpt-6.1-sol", "high"],
    ["gpt-6-luna-max", "gpt-6-luna", "max"],
  ]) {
    const ref = { providerID: "openai", id };
    assert.deepEqual(canonicalModel(ref), {
      providerID: "openai",
      id: target,
      variant,
    });
    assert.equal(canonicalModel({ ...ref, variant: "low" }).variant, "low");
    assert.equal(
      canonicalModel({ ...ref, variant: "default" }).variant,
      variant,
    );
    assert.deepEqual(canonicalModel({ ...ref, providerID: "other" }), {
      ...ref,
      providerID: "other",
    });
    const state = routingState("paid");
    state.models.plan = ref;
    assert.deepEqual(
      routedModel({ [routingKey]: state }, "plan"),
      canonicalModel(ref),
    );
  }
});
