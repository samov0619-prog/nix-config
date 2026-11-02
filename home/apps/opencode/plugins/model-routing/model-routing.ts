// Shared by the small upstream patch, local commands and Nix settings.
import models from "./routing-models.json" with { type: "json" };
export const routingKey = "local.model-routing";
export type ModelRef = { providerID: string; id: string; variant?: string };
export type Routing = {
  version: 1;
  mode: "free" | "paid";
  models: Record<string, ModelRef>;
  overrides?: Record<string, Record<string, ModelRef>>;
};

// A single role table feeds the commands, core resolver and TUI. No provider fallback.
export const paidModels: Record<string, ModelRef> = models;

// Read old session references without keeping selectable aliases in the catalog
// or rewriting the user's database/history. Explicit non-default variants win.
export function canonicalModel(model: ModelRef): ModelRef {
  if (model.providerID !== "openai") return model;
  const legacy: Record<string, ModelRef> = {
    "gpt-6.1-sol-plan": {
      providerID: "openai",
      id: "gpt-6.1-sol",
      variant: "xhigh",
    },
    "gpt-6.1-sol-high": {
      providerID: "openai",
      id: "gpt-6.1-sol",
      variant: "high",
    },
    "gpt-6-luna-max": {
      providerID: "openai",
      id: "gpt-6-luna",
      variant: "max",
    },
  };
  const replacement = legacy[model.id];
  return replacement
    ? {
        ...replacement,
        // SessionInfo materializes a missing stored variant as "default".
        variant:
          model.variant && model.variant !== "default"
            ? model.variant
            : replacement.variant,
      }
    : model;
}

export function routingState(mode: Routing["mode"]): Routing {
  return {
    version: 1,
    mode,
    models:
      mode === "free"
        ? { "*": { providerID: "opencode", id: "big-pickle" } }
        : structuredClone(paidModels),
  };
}

// Only explicitly configured model identities imply a helper stack. Unknown
// models require a user choice; provider names and catalog prices are not policy.
export function helperMode(model: ModelRef): Routing["mode"] | undefined {
  const ref = canonicalModel(model);
  if (ref.providerID === "opencode" && ref.id === "big-pickle") return "free";
  if (
    Object.values(paidModels).some(
      (item) => item.providerID === ref.providerID && item.id === ref.id,
    )
  )
    return "paid";
}

export function selectedRouting(
  metadata: unknown,
  mode: Routing["mode"],
  scope: string,
  role: string,
  model: ModelRef,
): Routing {
  const previous = routing(metadata);
  const overrides = previous?.overrides;
  return {
    ...routingState(mode),
    overrides: {
      ...overrides,
      [scope]: { ...overrides?.[scope], [role]: canonicalModel(model) },
    },
  };
}

export function routing(metadata: unknown): Routing | undefined {
  if (!metadata || typeof metadata !== "object") return;
  const value = (metadata as Record<string, unknown>)[routingKey] as
    Routing | undefined;
  if (
    value?.version !== 1 ||
    !["free", "paid"].includes(value.mode) ||
    !value.models ||
    typeof value.models !== "object" ||
    Array.isArray(value.models)
  )
    return;
  return value;
}

export function routedModel(
  metadata: unknown,
  role: string,
  sessionID?: string,
  rootID?: string,
): ModelRef | undefined {
  const state = routing(metadata);
  const scope = sessionID && sessionID === rootID ? "$root" : sessionID;
  const model =
    (scope ? state?.overrides?.[scope]?.[role] : undefined) ??
    state?.models[role] ??
    state?.models["*"];
  if (
    !model ||
    typeof model.providerID !== "string" ||
    !model.providerID ||
    typeof model.id !== "string" ||
    !model.id
  )
    return;
  if (model.variant !== undefined && typeof model.variant !== "string") return;
  return canonicalModel(model);
}
