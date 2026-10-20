import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { saveSubqueryUsage } from "../lib/task-usage.ts";

test("usage ledger keeps all assistant steps, whitelists counters, and is private", async () => {
	const directory = await mkdtemp(join(tmpdir(), "opencode-accounting-"));
	const previous = process.env.XDG_STATE_HOME;
	process.env.XDG_STATE_HOME = directory;
	try {
		const entries = [1, 2].map((step) => ({ info: {
			id: `m${step}`, role: "assistant", providerID: "p", modelID: "m",
			tokens: { input: step * 10, output: step, reasoning: 0, cache: { read: 100, write: 0 }, private: "SECRET" },
			cost: 0, time: { completed: step },
		}, parts: [{ text: "SECRET" }] }));
		await saveSubqueryUsage({ session: { messages: async (args: any) => {
			assert.equal(args.path.id, "child");
			assert.ok(args.signal instanceof AbortSignal);
			return { data: [{ info: { role: "user", text: "SECRET" } }, ...entries] };
		} } }, { parentSessionID: "parent", childSessionID: "child", started: 1 });
		const path = join(directory, "opencode/task-usage/child.json");
		const raw = await readFile(path, "utf8");
		assert.ok(!raw.includes("SECRET"));
		assert.equal(JSON.parse(raw).messages.length, 2);
		assert.equal((await stat(path)).mode & 0o777, 0o600);
		await assert.rejects(saveSubqueryUsage({ session: { messages: async () => ({
			data: entries, response: { headers: new Headers({ link: '<next>; rel="next"' }) },
		}) } }, { parentSessionID: "parent", childSessionID: "partial", started: 1 }), /paginated/);
	} finally {
		if (previous === undefined) delete process.env.XDG_STATE_HOME;
		else process.env.XDG_STATE_HOME = previous;
		await rm(directory, { recursive: true, force: true });
	}
});
