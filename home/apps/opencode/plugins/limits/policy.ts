// Provider percentages, not token counts or catalogue prices.
export type Window = {
  key: string;
  remaining: number;
  seconds: number;
  resetAt: number;
};
export type Snapshot = { observedAt: number; windows: Window[] };
export type BudgetState = {
  snapshot?: Snapshot;
  latched: Record<string, number>;
  ignored: Record<string, number>;
};
export const checkpointKey = "local.checkpoint";
export const emptyBudget = (): BudgetState => ({
  latched: {},
  ignored: {},
});

export function parseUsage(value: any, now = Date.now()): Snapshot | undefined {
  const windows: Window[] = [];
  for (const key of ["primary_window", "secondary_window"]) {
    const item = value?.rate_limit?.[key];
    if (
      !item ||
      !Number.isFinite(item.used_percent) ||
      item.used_percent < 0 ||
      item.used_percent > 100 ||
      !Number.isFinite(item.limit_window_seconds) ||
      item.limit_window_seconds <= 0 ||
      !Number.isFinite(item.reset_at) ||
      item.reset_at <= 0
    )
      continue;
    windows.push({
      key,
      remaining: 100 - item.used_percent,
      seconds: item.limit_window_seconds,
      resetAt: item.reset_at,
    });
  }
  return windows.length ? { observedAt: now, windows } : undefined;
}

export function thresholds(active: number, seconds = 18000) {
  // Continue conservatively beyond the agreed 1–3 workers; never reserve >50%.
  const wrap = Math.min(50, 15 + 5 * (Math.max(1, active) - 1));
  // One observed workload consumed 3 weekly pp per 22 five-hour pp. Round each
  // threshold independently; worker dependence remains, with integer-percent steps.
  const scale = seconds === 604800 ? 3 / 22 : 1;
  return {
    wrap: Math.round(wrap * scale),
    warn: Math.round((wrap + 10) * scale),
  };
}

export function recover(state: BudgetState, snapshot: Snapshot) {
  for (const item of snapshot.windows) {
    for (const group of [state.latched, state.ignored]) {
      const previous = group[item.key];
      if (
        previous !== undefined &&
        (item.remaining > 95 ||
          (snapshot.observedAt >= previous * 1000 && item.resetAt > previous))
      ) {
        delete group[item.key];
      }
    }
  }
  state.snapshot = snapshot;
}

export function windowMode(state: BudgetState, item: Window, active: number) {
  if (state.ignored[item.key] !== undefined) return "normal";
  const { wrap, warn } = thresholds(active, item.seconds);
  if (state.latched[item.key] !== undefined || item.remaining <= wrap)
    return "wrap";
  return item.remaining <= warn ? "warn" : "normal";
}

export function budgetMode(state: BudgetState, active: number) {
  let warning = false;
  for (const item of state.snapshot?.windows ?? []) {
    const mode = windowMode(state, item, active);
    if (mode === "wrap") state.latched[item.key] ??= item.resetAt;
    if (mode === "warn") warning = true;
  }
  return Object.keys(state.latched).length
    ? "wrap"
    : warning
      ? "warn"
      : "normal";
}

export function resetBudget(state: BudgetState, active = 1) {
  // Explicit override lasts for the observed windows, not until the next poll.
  for (const item of state.snapshot?.windows ?? [])
    if (
      state.latched[item.key] !== undefined ||
      item.remaining <= thresholds(active, item.seconds).warn
    )
      state.ignored[item.key] = item.resetAt;
  state.latched = {};
}

export function windowLabel(seconds: number) {
  return seconds === 604800
    ? "week"
    : seconds % 3600 === 0
      ? `${seconds / 3600}h`
      : `${Math.ceil(seconds / 60)}m`;
}

export const checkpointRequest =
  "Prepare a handoff checkpoint for the current task. Do not expand scope. " +
  "Review the work, fix blocking findings, then review again; repeat until there are no known handoff blockers. " +
  "Respect existing permissions: this does not authorize builds, deployment, or extra agents. " +
  "If Git is available and there are task changes, create a local commit containing only those changes " +
  "(this request authorizes that local checkpoint commit, but never a push). " +
  "Without Git, bring the code/text to a coherent stopping point. " +
  "Report completed checks, unrun checks, limitations, and where to resume. " +
  "In Plan mode do not edit or commit; hand off the reviewed plan instead. " +
  "Call checkpoint_ready only after review passes and the handoff is actually ready, then stop. " +
  "If budget or a blocker prevents readiness, leave the checkpoint pending and explain the blocker.";
