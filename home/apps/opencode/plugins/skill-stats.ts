import { Plugin } from "@opencode/plugin";

export default Plugin.define({
	id: "local.skill-stats",
	async setup(context) {
		let warned = false;
		function warn() {
			if (!warned) console.warn("skill-stats: recording incomplete; storage or query lookup unavailable");
			warned = true;
		}
		const hook = await context.tool.hook("execute.after", async (event) => {
			if (event.tool !== "skill") return;
			const skill = (event.input as { id?: unknown } | null)?.id;
			if (typeof skill !== "string") return;
			const key = `calls/${encodeURIComponent(event.sessionID)}/${encodeURIComponent(event.messageID)}/${encodeURIComponent(event.id)}`;
			try {
				if (await context.storage.get(key)) return;
				let queryID: string | null = null;
				let lastQuery: string | null = null;
				let model: { providerID: string; id: string; variant?: string } | null = null;
				try {
					const messages = await context.session.context({ sessionID: event.sessionID });
					const index = messages.findIndex(message => message.id === event.messageID && message.type === "assistant");
					const assistant = messages[index];
					if (assistant?.type === "assistant") model = { ...assistant.model };
					// Ignore later delivered/steering messages and never read another session.
					for (let i = index - 1; i >= 0; i--) {
						const message = messages[i];
						if (message.type !== "user") continue;
						queryID = message.id;
						lastQuery = message.text;
						break;
					}
				} catch { warn(); }
				// Upsert by call identity: duplicate deliveries/reloads cannot add counts.
				// Only the query is copied; never persist tool output or error contents.
				await context.storage.set(key, {
					version: 1, sessionID: event.sessionID, messageID: event.messageID,
					toolCallID: event.id, skill, status: event.status, agent: event.agent,
					time: Date.now(), queryID, lastQuery, model,
				});
			} catch { warn(); }
		});
		return () => hook.dispose();
	},
});
