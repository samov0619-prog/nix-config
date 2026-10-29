import { Plugin } from "@opencode/plugin/tui";
import { routingKey, routingState } from "./model-routing.ts";

// Export the setup separately so commands can be tested against the public V2 API.
export function setup(context: Plugin.Context) {
	let switching = false;
	async function switchMode(mode: "free" | "paid") {
		if (switching) return;
		switching = true;
		try {
			const route = context.ui.router.current();
			let session = route.type === "session"
				? await context.client.session.get({ sessionID: route.sessionID })
				: undefined;
			const seen = new Set<string>();
			while (session?.parentID) {
				if (seen.has(session.id)) throw new Error("Cyclic session parent chain");
				seen.add(session.id);
				session = await context.client.session.get({ sessionID: session.parentID });
			}
			const state = routingState(mode);
			// Check every required model and variant before changing the durable policy.
			const location = session?.location ?? context.location ?? context.data.location.default();
			await context.data.location.model.sync(location);
			const catalog = context.data.location.model.list(location) ?? [];
			for (const model of Object.values(state.models)) {
				const info = catalog.find((item) => item.providerID === model.providerID && item.id === model.id);
				if (!info || (model.variant && !info.variants.some((item) => item.id === model.variant))) {
					throw new Error(`Model unavailable: ${model.providerID}/${model.id}${model.variant ? `#${model.variant}` : ""}`);
				}
			}
			if (session) {
				await context.client.session.update({
					sessionID: session.id,
					metadata: { ...session.metadata, [routingKey]: state },
				});
			} else {
				session = await context.client.session.create({ location, metadata: { [routingKey]: state } });
				context.ui.router.navigate({ type: "session", sessionID: session.id });
			}
			await context.data.session.sync(session.id);
			context.ui.toast.show({ title: "Model routing", message: `${mode}: subsequent requests in this session family`, variant: "success" });
		} catch (error) {
			context.ui.toast.show({ title: "Model routing", message: error instanceof Error ? error.message : String(error), variant: "error" });
		} finally {
			switching = false;
		}
	}
	// Slash autocomplete has its own mode; these commands must remain reachable.
	context.keymap.layer(() => ({ mode: "global", commands: (["free", "paid"] as const).map((mode) => ({
		id: `local.routing.${mode}`, title: `Switch to ${mode} models`, palette: true,
		slash: { name: `switch-${mode}` }, run: () => switchMode(mode),
	})) }));
}

export default Plugin.define({ id: "local.model-routing", setup });
