import { appendFile, mkdir } from "node:fs/promises";
import { join } from "node:path";

type PermissionRequest = {
	id: string;
	permission: string;
	patterns?: string[];
};

const stateHome =
	process.env.XDG_STATE_HOME ?? join(process.env.HOME ?? ".", ".local", "state");
const historyPath = join(stateHome, "opencode", "permission-history.jsonl");
const requests = new Map<string, PermissionRequest>();

export default async () => ({
	event: async ({ event }: { event: any }) => {
		if (event.type === "permission.asked") {
			requests.set(event.properties.id, event.properties);
			return;
		}

		if (event.type !== "permission.replied") return;
		const request = requests.get(event.properties.requestID);
		if (!request) return;

		await mkdir(join(stateHome, "opencode"), { recursive: true });
		await appendFile(
			historyPath,
			JSON.stringify({
				time: new Date().toISOString(),
				permission: request.permission,
				patterns: request.patterns ?? [],
				response: event.properties.reply,
			}) + "\n",
		);
		requests.delete(event.properties.requestID);
	},
});
