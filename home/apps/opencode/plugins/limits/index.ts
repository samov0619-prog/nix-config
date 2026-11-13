import { Plugin } from "@opencode/plugin";
import { createHash, randomUUID } from "node:crypto";
import { mkdir, readFile, rename, unlink, writeFile } from "node:fs/promises";
import { join } from "node:path";
import {
  budgetMode,
  checkpointKey,
  emptyBudget,
  parseUsage,
  recover,
  resetBudget,
  thresholds,
  windowMode,
  type BudgetState,
} from "./policy.ts";
import { Limits } from "./rpc.ts";
import { coalescedWriter } from "./writer.ts";

const TTL = 60_000;
type Worker = {
  account?: string;
  quotaSupported?: boolean;
  running: boolean;
  waits: Set<string>;
};
type Pool = {
  state: BudgetState;
  loaded: Promise<void>;
  pending?: Promise<void>;
  lastAttempt: number;
  save: () => Promise<void>;
  file: string;
};

// Plugin setup is location-scoped. Share caches, in-flight fetches and the worker
// registry across all locations in this server, not across TUI tabs or machines.
const sharedKey = Symbol.for("local.limits.v1");
const shared = ((globalThis as any)[sharedKey] ??= {
  pools: new Map<string, Pool>(),
  workers: new Map<string, Worker>(),
  listeners: new Map<() => void, Plugin.Context>(),
  publishPending: false,
}) as {
  pools: Map<string, Pool>;
  workers: Map<string, Worker>;
  listeners: Map<() => void, Plugin.Context>;
  publishPending: boolean;
  observer?: { owner: () => void; abort: AbortController };
};
function publish() {
  if (shared.publishPending) return;
  shared.publishPending = true;
  queueMicrotask(() => {
    shared.publishPending = false;
    // RPC events reach all clients/locations. Emit once, not once per setup.
    shared.listeners.keys().next().value?.();
  });
}

function worker(id: string) {
  let value = shared.workers.get(id);
  if (!value) {
    value = { running: false, waits: new Set() };
    shared.workers.set(id, value);
  }
  return value;
}
export function activeWorkers(account: string) {
  let count = 0;
  for (const item of shared.workers.values())
    if (item.account === account && item.running && !item.waits.size) count++;
  return count;
}

const countedAccount = (item?: Worker) =>
  item?.running && !item.waits.size ? item.account : undefined;

function waitFor(id: string, key: string, waiting: boolean) {
  const item = shared.workers.get(id);
  if (!item) return;
  const before = countedAccount(item);
  if (waiting) item.waits.add(key);
  else item.waits.delete(key);
  if (before !== countedAccount(item)) publish();
}

function lifecycle(event: { type: string; data: any }) {
  // 2.1.4's Promise adapter ignores subscribe({ types }). Filter BEFORE touching
  // worker state: text deltas, metadata and our own RPC events must be no-ops.
  switch (event.type) {
    case "credential.switched":
      if (event.data.integrationID === "openai") publish();
      break;
    case "session.execution.started": {
      const item = worker(event.data.sessionID);
      const before = countedAccount(item);
      item.running = true;
      if (before !== countedAccount(item)) publish();
      break;
    }
    case "session.execution.succeeded":
    case "session.execution.failed":
    case "session.execution.interrupted": {
      const item = shared.workers.get(event.data.sessionID);
      const before = countedAccount(item);
      shared.workers.delete(event.data.sessionID);
      if (before) publish();
      break;
    }
    case "permission.asked":
      waitFor(event.data.sessionID, event.data.id, true);
      break;
    case "permission.replied":
      waitFor(event.data.sessionID, event.data.requestID, false);
      break;
    case "form.created":
      waitFor(event.data.form.sessionID, event.data.form.id, true);
      break;
    case "form.replied":
    case "form.cancelled":
      waitFor(event.data.sessionID, event.data.id, false);
      break;
  }
}

function observe() {
  if (shared.observer) return;
  const source = shared.listeners.entries().next().value;
  if (!source) return;
  const [owner, ctx] = source;
  const observer = { owner, abort: new AbortController() };
  shared.observer = observer;
  void (async () => {
    for await (const event of ctx.event.subscribe({
      signal: observer.abort.signal,
    })) {
      if (observer.abort.signal.aborted) break;
      lifecycle(event);
    }
  })()
    .catch(() => {
      if (!observer.abort.signal.aborted)
        console.warn(
          "limits: lifecycle stream unavailable; active worker count may be incomplete",
        );
    })
    .finally(() => {
      if (shared.observer === observer) shared.observer = undefined;
    });
}

async function poolFor(account: string) {
  let pool = shared.pools.get(account);
  if (!pool) {
    const directory = join(
      process.env.XDG_STATE_HOME ??
        join(process.env.HOME ?? ".", ".local/state"),
      "opencode/limits",
    );
    pool = {
      state: emptyBudget(),
      loaded: Promise.resolve(),
      lastAttempt: 0,
      save: async () => {},
      file: join(directory, `${account}.json`),
    };
    const target = pool;
    target.save = coalescedWriter(async () => {
      const temporary = `${target.file}.${randomUUID()}`;
      try {
        await mkdir(join(target.file, ".."), { recursive: true, mode: 0o700 });
        // Persist only the current schema, including when a hot reload reused an
        // older in-memory pool with fields this version no longer consumes.
        const content = JSON.stringify({
          version: 1,
          snapshot: target.state.snapshot,
          latched: target.state.latched,
          ignored: target.state.ignored,
        });
        await writeFile(temporary, content, { mode: 0o600, flag: "wx" });
        await rename(temporary, target.file);
      } catch {
        /* Optional telemetry must not break a model call or log private data. */
      } finally {
        await unlink(temporary).catch(() => {});
      }
    });
    target.loaded = (async () => {
      try {
        const value = JSON.parse(await readFile(target.file, "utf8"));
        // Read only our versioned, bounded, non-secret budget records.
        if (value.version !== 1) return;
        for (const key of ["latched", "ignored"] as const)
          for (const name of ["primary_window", "secondary_window"])
            if (Number.isFinite(value[key]?.[name]))
              target.state[key][name] = value[key][name];
        const snapshot = value.snapshot;
        if (
          Number.isFinite(snapshot?.observedAt) &&
          Array.isArray(snapshot.windows)
        ) {
          const parsed = parseUsage(
            {
              rate_limit: Object.fromEntries(
                snapshot.windows.map((item: any) => [
                  item.key,
                  {
                    used_percent: 100 - item.remaining,
                    limit_window_seconds: item.seconds,
                    reset_at: item.resetAt,
                  },
                ]),
              ),
            },
            snapshot.observedAt,
          );
          target.state.snapshot = parsed;
        }
      } catch {
        /* Missing/corrupt cache is unknown, never 100% available. */
      }
    })();
    shared.pools.set(account, target);
  }
  await pool.loaded;
  return pool;
}

function persist(pool: Pool) {
  return pool.save();
}

async function identity(ctx: Plugin.Context) {
  const connection = await ctx.integration.connection.active("openai");
  if (!connection) return;
  const credential = await ctx.integration.connection.resolve(connection);
  if (
    credential?.type !== "oauth" ||
    !["chatgpt-browser", "chatgpt-headless", "chatgpt-token-sharing"].includes(
      credential.methodID,
    )
  )
    return;
  const accountID = credential.metadata?.accountID;
  const key = createHash("sha256")
    .update(
      typeof accountID === "string"
        ? accountID
        : connection.type === "credential"
          ? connection.id
          : JSON.stringify(connection),
    )
    .digest("hex");
  // Token-sharing grants target api.openai.com, not the legacy ChatGPT usage
  // endpoint. Revisit openai/codex#54219 before enabling a replacement source.
  return {
    key,
    credential,
    accountID,
    quotaSupported: credential.methodID !== "chatgpt-token-sharing",
  };
}

async function refresh(
  pool: Pool,
  auth: NonNullable<Awaited<ReturnType<typeof identity>>>,
) {
  if (!auth.quotaSupported) return;
  if (pool.pending) return pool.pending;
  if (
    Date.now() -
      Math.max(pool.lastAttempt, pool.state.snapshot?.observedAt ?? 0) <
    TTL
  )
    return;
  pool.lastAttempt = Date.now();
  const startedAt = pool.lastAttempt;
  pool.pending = (async () => {
    try {
      const headers: Record<string, string> = {
        authorization: `Bearer ${auth.credential.access}`,
        accept: "application/json",
      };
      if (typeof auth.accountID === "string")
        headers["chatgpt-account-id"] = auth.accountID;
      const response = await fetch(
        "https://chatgpt.com/backend-api/wham/usage",
        {
          headers,
          redirect: "error",
          signal: AbortSignal.timeout(5000),
        },
      );
      if (!response.ok) {
        await response.body?.cancel();
        return;
      }
      // Do not persist/log the response (it includes account identifiers/email).
      const reader = response.body?.getReader();
      if (!reader) return;
      const chunks: Uint8Array[] = [];
      let size = 0;
      try {
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          size += value.length;
          if (size > 64 * 1024) return;
          chunks.push(value);
        }
        const snapshot = parseUsage(
          JSON.parse(Buffer.concat(chunks).toString("utf8")),
        );
        if (snapshot && (pool.state.snapshot?.observedAt ?? 0) <= startedAt) {
          recover(pool.state, snapshot);
          await persist(pool);
          publish();
        }
      } finally {
        await reader.cancel().catch(() => {});
      }
    } catch {
      /* Keep the last sample, visibly dated; no retries or credential logs. */
    }
  })().finally(() => {
    pool.pending = undefined;
  });
  return pool.pending;
}

function tokenSharingStatus(account: string) {
  return {
    available: false,
    reason: "token-sharing-quota-unavailable",
    active: activeWorkers(account),
    mode: "normal",
    windowModes: {},
    thresholds: [],
    snapshot: null,
  };
}

export async function setup(ctx: Plugin.Context) {
  const registrations: { dispose(): Promise<void> }[] = [];
  let alive = true;
  const rpc = await ctx.rpc.register(Limits, {
    status: async () => {
      const auth = await identity(ctx).catch(() => undefined);
      if (!auth) return { available: false, active: 0 };
      if (!auth.quotaSupported) return tokenSharingStatus(auth.key);
      const pool = await poolFor(auth.key);
      await refresh(pool, auth);
      const active = activeWorkers(auth.key);
      const before = JSON.stringify(pool.state.latched);
      const mode = budgetMode(pool.state, active);
      if (before !== JSON.stringify(pool.state.latched)) await persist(pool);
      // A credential may change while legacy I/O is in flight. Never return
      // the old account's percentages; ask clients to read the new identity.
      const current = await identity(ctx).catch(() => undefined);
      if (
        !current ||
        current.key !== auth.key ||
        current.quotaSupported !== auth.quotaSupported
      ) {
        publish();
        return current && !current.quotaSupported
          ? tokenSharingStatus(current.key)
          : {
              available: false,
              active: current ? activeWorkers(current.key) : 0,
            };
      }
      return {
        available: true,
        active,
        mode,
        windowModes: Object.fromEntries(
          (pool.state.snapshot?.windows ?? []).map((item) => [
            item.key,
            windowMode(pool.state, item, active),
          ]),
        ),
        thresholds: (pool.state.snapshot?.windows ?? []).map((item) => ({
          key: item.key,
          ...thresholds(active, item.seconds),
        })),
        snapshot: pool.state.snapshot ?? null,
      };
    },
    reset: async () => {
      const auth = await identity(ctx);
      if (!auth || !auth.quotaSupported) return { reset: false };
      const pool = await poolFor(auth.key);
      if (!pool.state.snapshot) return { reset: false };
      resetBudget(pool.state, activeWorkers(auth.key));
      await persist(pool);
      publish();
      return { reset: true };
    },
  });
  registrations.push(rpc);
  const notify = () => {
    if (alive) void rpc.events.emit("updated", {}).catch(() => {});
  };
  const cleanup = async () => {
    alive = false;
    shared.listeners.delete(notify);
    if (shared.observer?.owner === notify) {
      shared.observer.abort.abort();
      shared.observer = undefined;
      observe();
    }
    if (!shared.listeners.size) shared.workers.clear();
    await Promise.all(registrations.map((item) => item.dispose()));
  };
  shared.listeners.set(notify, ctx);
  try {
    observe();

    registrations.push(
      await ctx.session.hook("context", async (event) => {
        const item = worker(event.sessionID);
        const previousAccount = countedAccount(item);
        item.running = true;
        if (event.model.providerID !== "openai") {
          item.account = undefined;
          if (previousAccount) publish();
          return;
        }
        const auth = await identity(ctx).catch(() => undefined);
        if (!auth) {
          item.account = undefined;
          if (previousAccount) publish();
          return;
        }
        item.account = auth.key;
        item.quotaSupported = auth.quotaSupported;
        const workerChanged = previousAccount !== countedAccount(item);
        if (!auth.quotaSupported) {
          if (workerChanged) publish();
          return;
        }
        const pool = await poolFor(auth.key);
        await refresh(pool, auth);
        const active = activeWorkers(auth.key);
        const latchCount = Object.keys(pool.state.latched).length;
        budgetMode(pool.state, active);
        const latchChanged =
          Object.keys(pool.state.latched).length !== latchCount;
        // Observation only: never add budget instructions to the model request.
        if (latchChanged) await persist(pool);
        if (workerChanged || latchChanged) publish();
      }),
    );
    registrations.push(
      await ctx.session.hook("experimental.ws.receive", async (event) => {
        if (
          event.model.providerID !== "openai" ||
          !event.frame.includes('"codex.rate_limits"')
        )
          return;
        const item = shared.workers.get(event.sessionID);
        const account = item?.account;
        if (!account || item.quotaSupported === false) return;
        try {
          const value = JSON.parse(event.frame);
          if (value.type !== "codex.rate_limits") return;
          const limits = value.rate_limits;
          const convert = (window: any) =>
            window && {
              used_percent: window.used_percent,
              limit_window_seconds: window.window_minutes * 60,
              reset_at: window.resets_at,
            };
          const snapshot =
            parseUsage(value) ??
            parseUsage({
              rate_limit: {
                primary_window: convert(limits?.primary),
                secondary_window: convert(limits?.secondary),
              },
            });
          if (!snapshot) return;
          const pool = await poolFor(account);
          // A partial notification must not make an old weekly sample look fresh
          // or hide a known window. Leave it to the bounded HTTP fallback.
          if (
            pool.state.snapshot?.windows.some(
              (old) =>
                !snapshot.windows.some((current) => current.key === old.key),
            )
          )
            return;
          recover(pool.state, snapshot);
          await persist(pool);
          publish();
        } catch {
          /* Unknown/malformed notifications do not affect the stream. */
        }
      }),
    );
    registrations.push(
      await ctx.tool.hook("execute.before", async (event) => {
        if (event.tool !== "checkpoint_ready") {
          const session = await ctx.session.get({ sessionID: event.sessionID });
          if ((session.metadata?.[checkpointKey] as any)?.ready)
            await ctx.session.update({
              sessionID: event.sessionID,
              metadata: {
                ...session.metadata,
                [checkpointKey]: { ready: false },
              },
            });
        }
        if (event.tool === "subagent") {
          waitFor(event.sessionID, event.id, true);
        }
      }),
    );
    registrations.push(
      await ctx.tool.hook("execute.after", (event) => {
        if (event.tool === "subagent") {
          waitFor(event.sessionID, event.id, false);
        }
        return Promise.resolve();
      }),
    );
    registrations.push(
      await ctx.session.hook("prompt", async (event) => {
        const session = await ctx.session.get({ sessionID: event.sessionID });
        if ((session.metadata?.[checkpointKey] as any)?.ready)
          await ctx.session.update({
            sessionID: event.sessionID,
            metadata: {
              ...session.metadata,
              [checkpointKey]: { ready: false },
            },
          });
      }),
    );
    registrations.push(
      await ctx.tool.transform((editor) => {
        editor.add({
          name: "checkpoint_ready",
          // The checkpoint instruction calls this tool directly, not via Code Mode.
          options: { codemode: false },
          description:
            "Mark a requested handoff checkpoint ready only AFTER review → fixes → repeat review finds no known handoff blockers. Create a Git commit only if the user separately explicitly requested it; otherwise leave reviewed changes uncommitted and identify them in the handoff. Finish a coherent code/text boundary. Provide checks/limitations and a resume plan. Never claim unrun checks passed. This does not authorize edits, builds, extra agents or commits in Plan mode. Then stop at the checkpoint.",
          input: {
            type: "object",
            properties: {
              summary: { type: "string", minLength: 1, maxLength: 2000 },
              review: { type: "string", minLength: 1, maxLength: 2000 },
              checks: { type: "string", minLength: 1, maxLength: 2000 },
              resume: { type: "string", minLength: 1, maxLength: 2000 },
              reviewPassed: { const: true, type: "boolean" },
              commit: {
                type: "string",
                maxLength: 200,
                description:
                  "Local commit ID, or why no commit was made (not requested, no Git, no changes, reviewed Plan); identify any uncommitted task changes.",
              },
            },
            required: [
              "summary",
              "review",
              "checks",
              "resume",
              "reviewPassed",
              "commit",
            ],
            additionalProperties: false,
          },
          execute: async (input, context) => {
            const value = input as Record<string, unknown>;
            if (
              value.reviewPassed !== true ||
              ["summary", "review", "checks", "resume", "commit"].some(
                (key) =>
                  typeof value[key] !== "string" ||
                  !(value[key] as string).trim(),
              )
            )
              throw new Error(
                "A reviewed handoff, checks/limitations, resume plan and commit explanation are required.",
              );
            const session = await ctx.session.get({
              sessionID: context.sessionID,
            });
            await ctx.session.update({
              sessionID: context.sessionID,
              metadata: {
                ...session.metadata,
                [checkpointKey]: { ready: true, at: Date.now(), ...value },
              },
            });
            return {
              content:
                "Checkpoint ready (agent-reported reviewed handoff, not independent verification). Stop here. Budget warnings are unchanged.",
            };
          },
        });
      }),
    );

    return cleanup;
  } catch (error) {
    await cleanup().catch(() => {});
    throw error;
  }
}

export default Plugin.define({ id: "local.limits", setup });
