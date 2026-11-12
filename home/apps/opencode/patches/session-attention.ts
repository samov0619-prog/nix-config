// Native notifications and quiet Kitty urgency share this policy, not a player.
// Tab lists are shared across TUI processes: membership alone is NOT ownership.
import { createHash, randomUUID } from "node:crypto";
import {
  mkdirSync, readFileSync, writeFileSync, renameSync, unlinkSync, linkSync,
  readdirSync, statSync, openSync, closeSync,
} from "node:fs";
import { join } from "node:path";

type Scope = {
  renderer: object;
  ui: {
    router: { current(): { type: string; sessionID?: string } };
    tabs: { enabled(): boolean; list(): readonly { sessionID: string }[] };
  };
  data: { session: { get(id: string): { parentID?: string } | undefined } };
};
type Client = { pid: number; start: string; token: string; roots: Record<string, string> };
type Tracker = {
  refs: number;
  routed?: string;
  selectionTime?: string;
  client: Client;
  directory: string;
  file: string;
};
// The bundled helper and the HM plugin are different modules in the same VM.
// A weak renderer key shares lifecycle/selection state without changing the host.
const key = Symbol.for("local.opencode.session-attention.v2");
const shared = globalThis as typeof globalThis & { [key]?: WeakMap<object, Tracker> };
const trackers = (shared[key] ??= new WeakMap<object, Tracker>());
const digest = (text: string) => createHash("sha256").update(text).digest("hex");
let warned = false;

function startTime(pid: number) {
  const stat = readFileSync(`/proc/${pid}/stat`, "utf8");
  return stat.slice(stat.lastIndexOf(")") + 2).split(" ")[19];
}

function root(context: Scope, id: string | undefined): string | undefined {
  const seen = new Set<string>();
  while (id && !seen.has(id)) {
    seen.add(id);
    const session = context.data.session.get(id);
    if (!session) return;
    if (!session.parentID) return id;
    id = session.parentID;
  }
}

function atomic(file: string, value: unknown, exclusive = false) {
  const temporary = `${file}.${randomUUID()}.tmp`;
  try {
    writeFileSync(temporary, JSON.stringify(value), { mode: 0o600, flag: "wx" });
    if (exclusive) linkSync(temporary, file);
    else renameSync(temporary, file);
  } finally {
    try { unlinkSync(temporary); } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
  }
}

function tracker(context: Scope) {
  let state = trackers.get(context.renderer);
  if (state) return state;
  // Linux home configuration only. No durable state, timer, daemon or fallback
  // into a public temporary directory; unavailable IPC fails closed.
  if (!process.env.XDG_RUNTIME_DIR) throw new Error("XDG_RUNTIME_DIR is missing");
  const directory = join(process.env.XDG_RUNTIME_DIR, "opencode-attention-v2");
  mkdirSync(join(directory, "clients"), { recursive: true, mode: 0o700 });
  mkdirSync(join(directory, "events"), { recursive: true, mode: 0o700 });
  const start = startTime(process.pid);
  const token = `${process.pid}-${start}-${randomUUID()}`;
  state = {
    refs: 0,
    client: { pid: process.pid, start, token, roots: {} },
    directory,
    file: join(directory, "clients", `${token}.json`),
  };
  trackers.set(context.renderer, state);
  return state;
}

function update(context: Scope, state: Tracker, explicitlySelected = false) {
  const route = context.ui.router.current();
  const routed = route.type === "session" ? route.sessionID : undefined;
  const newlySelected = routed !== state.routed || explicitlySelected;
  if (newlySelected) state.selectionTime = process.hrtime.bigint().toString();
  const selected = route.type === "session" ? root(context, route.sessionID) : undefined;
  const tabs = context.ui.tabs.enabled();
  const open = new Set(tabs ? context.ui.tabs.list().map((tab) => tab.sessionID) : []);
  if (selected) open.add(selected);
  let changed = false;
  for (const id of Object.keys(state.client.roots)) {
    if (!open.has(id)) {
      delete state.client.roots[id];
      changed = true;
    }
  }
  if (selected && (!state.client.roots[selected] || newlySelected)) {
    // CLOCK_MONOTONIC is shared across local Linux processes. Wall-clock changes
    // must not transfer ownership backwards. Merely syncing global tabs cannot claim.
    // Preserve the actual selection time if ancestry arrives later: a delayed
    // cache hydration must not steal ownership from a more recent selection.
    state.client.roots[selected] = state.selectionTime!;
    changed = true;
  }
  state.routed = routed;
  if (changed || !exists(state.file)) atomic(state.file, state.client);
}

function exists(file: string) {
  try { statSync(file); return true; } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return false;
    throw error;
  }
}

function report(error: unknown) {
  if (warned) return;
  warned = true;
  console.warn("OpenCode attention routing unavailable; suppressed to avoid duplicate notifications", error);
}

// Call update from a native Solid effect. Its dependencies are the live route,
// session ancestry and tab membership, not compositor workspace or terminal blur.
export function trackSessionAttention(context: Scope) {
  let state: Tracker | undefined;
  try { state = tracker(context); state.refs++; } catch (error) { report(error); }
  let disposed = false;
  return {
    update(explicitlySelected = false) {
      if (!state || disposed) return;
      try { update(context, state, explicitlySelected); } catch (error) { report(error); }
    },
    dispose() {
      if (!state || disposed) return;
      disposed = true;
      if (--state.refs !== 0) return;
      try { unlinkSync(state.file); } catch (error) {
        if ((error as NodeJS.ErrnoException).code !== "ENOENT") report(error);
      }
    },
  };
}

function owner(state: Tracker, sessionID: string) {
  let winner: { token: string; selected: bigint } | undefined;
  const directory = join(state.directory, "clients");
  for (const file of readdirSync(directory)) {
    if (!/^\d+-\d+-[a-f0-9-]+\.json$/.test(file)) continue;
    try {
      const client = JSON.parse(readFileSync(join(directory, file), "utf8")) as Client;
      if (!client.roots[sessionID] || startTime(client.pid) !== client.start) continue;
      const selected = BigInt(client.roots[sessionID]);
      const token = client.token;
      if (!winner || selected > winner.selected || (selected === winner.selected && token > winner.token)) {
        winner = { token, selected };
      }
    } catch (error) {
      // Exited clients and malformed/stale records are not owners. Other clients'
      // records are never rewritten or removed by this process.
      if ((error as NodeJS.ErrnoException).code === "EACCES") throw error;
    }
  }
  return winner?.token;
}

export function sessionAttention(
  context: Scope,
  sessionID: string | undefined,
  event: { id: string },
  channel: "native" | "urgency",
): boolean {
  try {
    if (!event.id) return false;
    const state = tracker(context);
    update(context, state);
    const session = root(context, sessionID);
    if (!session) return false;
    const winner = owner(state, session);
    if (!winner) return false;
    const directory = join(state.directory, "events");
    const file = join(directory, digest(`${session}\0${event.id}`));
    // Freeze one owner per event, across BOTH output channels and route races.
    // Hard-link publication is atomic and never exposes a partially written JSON.
    try { atomic(file, winner, true); } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error;
    }
    if (JSON.parse(readFileSync(file, "utf8")) !== state.client.token) return false;
    try { closeSync(openSync(`${file}.${channel}`, "wx", 0o600)); } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "EEXIST") return false;
      throw error;
    }
    return true;
  } catch (error) {
    report(error);
    return false;
  }
}
