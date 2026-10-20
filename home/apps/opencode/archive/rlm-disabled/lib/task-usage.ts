import { mkdir, rename, writeFile } from "node:fs/promises";
import { join } from "node:path";

// Retain accounting only: never persist prompts, tool arguments, or source text.
export async function saveSubqueryUsage(client: any, input: {
	parentSessionID: string; parentMessageID?: string; childSessionID: string; started: number;
}) {
	const response = await client.session.messages({
		path: { id: input.childSessionID }, signal: AbortSignal.timeout(10_000),
	});
	if (!Array.isArray(response?.data)) throw new Error("Child usage unavailable");
	if (response.response?.headers?.get("link")?.includes('rel="next"')) {
		throw new Error("Child usage is paginated; retain session rather than record partial usage");
	}
	const number = (value: unknown) => typeof value === "number" && Number.isFinite(value) ? value : undefined;
	const messages = response.data.map((entry: any) => entry.info)
		.filter((info: any) => info?.role === "assistant")
		.map((info: any) => ({
			id: info.id, providerID: info.providerID, modelID: info.modelID,
			tokens: info.tokens ? {
				input: number(info.tokens.input), output: number(info.tokens.output),
				reasoning: number(info.tokens.reasoning),
				cache: { read: number(info.tokens.cache?.read), write: number(info.tokens.cache?.write) },
			} : undefined,
			cost: number(info.cost), completed: number(info.time?.completed),
		}));
	const directory = join(process.env.XDG_STATE_HOME || join(process.env.HOME || ".", ".local", "state"),
		"opencode", "task-usage");
	await mkdir(directory, { recursive: true, mode: 0o700 });
	const file = join(directory, `${input.childSessionID.replace(/[^A-Za-z0-9_-]/g, "_")}.json`);
	const temporary = `${file}.${process.pid}.tmp`;
	await writeFile(temporary, JSON.stringify({ version: 1, ...input, finished: Date.now(), messages }), { mode: 0o600 });
	await rename(temporary, file);
}
