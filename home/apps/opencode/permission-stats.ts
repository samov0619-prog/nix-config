import { appendFile, mkdir } from "node:fs/promises";
import { join } from "node:path";
import { Plugin } from "@opencode/plugin";

type PermissionRequest = {
	id: string;
	action: string;
	resources: string[];
	sessionID: string;
};

const stateHome =
	process.env.XDG_STATE_HOME ?? join(process.env.HOME ?? ".", ".local", "state");
const historyPath = join(stateHome, "opencode", "permission-history.jsonl");
export default Plugin.define({
	id: "local.permission-stats",
	setup(context) {
		const requests = new Map<string, PermissionRequest>();
		const abort = new AbortController();
		const consume = async () => {
			for await (const event of context.event.subscribe({ signal: abort.signal })) {
				if (event.type === "permission.asked") {
					requests.set(event.data.id, event.data);
					continue;
				}
				if (event.type !== "permission.replied") continue;
				const request = requests.get(event.data.requestID);
				if (!request) continue;
				requests.delete(event.data.requestID);
				try {
					await mkdir(join(stateHome, "opencode"), { recursive: true });
					await appendFile(historyPath, JSON.stringify({
						time: new Date().toISOString(),
						permission: request.action,
						patterns: request.resources,
						response: event.data.reply,
						sessionID: request.sessionID,
						requestID: request.id,
					}) + "\n", { mode: 0o600 });
				} catch (error) {
					console.warn("permission-stats: append failed", String(error));
				}
			}
		};
		void consume().catch((error) => {
			if (!abort.signal.aborted) console.warn("permission-stats: subscription failed", String(error));
		});
		return () => { abort.abort(); requests.clear(); };
	},
});
