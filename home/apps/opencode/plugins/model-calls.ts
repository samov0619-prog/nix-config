import { randomUUID } from "node:crypto";
import { constants } from "node:fs";
import { mkdir, open } from "node:fs/promises";
import { join } from "node:path";
import { Plugin } from "@opencode/plugin";

const MAX_BODY = 8 * 1024 * 1024;
const label = (value: unknown) => typeof value === "string" && /^[\w.:/@+\-]{1,160}$/.test(value) ? value : undefined;
const kinds = new Set(["primary", "title", "generate", "compaction"]);

// Never persist bodies, URLs, headers, provider errors, prompts or usage. These
// fields describe an attempt, not proof of completion or provider billing.
function wire(body: any) {
	return { wireModel: label(body?.model), effort: label(body?.reasoning?.effort ?? body?.reasoning_effort) };
}

async function requestWire(request: Request) {
	if (!request.headers.get("content-type")?.includes("json") || !request.body) return {};
	const reader = request.clone().body!.getReader();
	try {
		const chunks: Uint8Array[] = [];
		let size = 0;
		while (true) {
			const { value, done } = await reader.read();
			if (done) break;
			size += value.byteLength;
			if (size > MAX_BODY) return {};
			chunks.push(value);
		}
		return wire(JSON.parse(Buffer.concat(chunks).toString("utf8")));
	} catch {
		return {};
	} finally {
		// Do not await tee cancellation: the original body has not been consumed.
		void reader.cancel().catch(() => {});
	}
}

export default Plugin.define({
	id: "local.model-calls",
	async setup(context) {
		const directory = join(process.env.XDG_STATE_HOME ?? join(process.env.HOME ?? ".", ".local/state"), "opencode/model-calls");
		const requests = new WeakMap<Request, string>();
		let warned = false;
		async function append(sessionID: string, row: Record<string, unknown>) {
			if (!/^[\w-]{1,128}$/.test(sessionID)) return;
			try {
				await mkdir(directory, { recursive: true, mode: 0o700 });
				const file = await open(join(directory, `${sessionID}.jsonl`), constants.O_CREAT | constants.O_APPEND | constants.O_WRONLY | constants.O_NOFOLLOW, 0o600);
				try {
					await file.chmod(0o600);
					await file.writeFile(JSON.stringify({ version: 1, sessionID, time: Date.now(), ...row }) + "\n");
				} finally { await file.close(); }
			} catch {
				// Accounting must not break inference; do not log potentially private errors.
				if (!warned) console.warn("model-calls: recording unavailable; call history may be incomplete");
				warned = true;
			}
		}
		function metadata(event: any) {
			return {
				kind: kinds.has(event.kind) ? event.kind : "unknown", agent: label(event.agent),
				providerID: label(event.model.providerID), modelID: label(event.model.id), variant: label(event.model.variant),
			};
		}
		const hooks = [];
		try {
			hooks.push(await context.session.hook("http.request", async (event) => {
				const id = randomUUID();
				requests.set(event.request, id);
				await append(event.sessionID, { id, event: "attempt", transport: "http", ...metadata(event), ...await requestWire(event.request) });
			}));
			hooks.push(await context.session.hook("http.response", async (event) => {
				const id = requests.get(event.request);
				if (!id) return;
				requests.delete(event.request);
				await append(event.sessionID, { id, event: "response", status: event.response.status });
			}));
			hooks.push(await context.session.hook("experimental.ws.send", async (event) => {
				// Open Responses inference frames only; control frames are not calls.
				let body;
				try { body = JSON.parse(event.frame); } catch { return; }
				if (body?.type !== "response.create") return;
				await append(event.sessionID, { id: randomUUID(), event: "attempt", transport: "websocket", ...metadata(event), ...wire(body) });
			}));
		} catch (error) {
			await Promise.all(hooks.map(hook => hook.dispose()));
			throw error;
		}
		return () => Promise.all(hooks.map(hook => hook.dispose())).then(() => {});
	},
});
