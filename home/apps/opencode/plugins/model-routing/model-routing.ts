// Shared by the small upstream patch, local commands and Nix settings.
import models from "./routing-models.json" with { type: "json" };
export const routingKey = "local.model-routing";
export type ModelRef = { providerID: string; id: string; variant?: string };
export type Routing = {
	version: 1;
	mode: "free" | "paid";
	models: Record<string, ModelRef>;
};

// A single role table feeds the commands, core resolver and TUI. No provider fallback.
export const paidModels: Record<string, ModelRef> = models;

export function routingState(mode: Routing["mode"]): Routing {
	return {
		version: 1, mode,
		models: mode === "free"
			? { "*": { providerID: "opencode", id: "big-pickle" } }
			: structuredClone(paidModels),
	};
}

export function routing(metadata: unknown): Routing | undefined {
	if (!metadata || typeof metadata !== "object") return;
	const value = (metadata as Record<string, unknown>)[routingKey] as Routing | undefined;
	if (value?.version !== 1 || !["free", "paid"].includes(value.mode) || !value.models || typeof value.models !== "object" || Array.isArray(value.models)) return;
	return value;
}

export function routedModel(metadata: unknown, role: string): ModelRef | undefined {
	const state = routing(metadata);
	const model = state?.models[role] ?? state?.models["*"];
	if (!model || typeof model.providerID !== "string" || !model.providerID || typeof model.id !== "string" || !model.id) return;
	if (model.variant !== undefined && typeof model.variant !== "string") return;
	return model;
}
