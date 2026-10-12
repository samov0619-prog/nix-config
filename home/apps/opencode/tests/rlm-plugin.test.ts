import assert from "node:assert/strict";
import test from "node:test";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { RLM } from "../rlm-plugin.ts";

test("subqueries preserve model routing, report limits, and clean up child sessions", async () => {
	const previous = process.env.RLM_SUBQUERY_MODEL;
	const previousState = process.env.XDG_STATE_HOME;
	const state = await mkdtemp(join(tmpdir(), "rlm-usage-"));
	process.env.XDG_STATE_HOME = state;
	delete process.env.RLM_SUBQUERY_MODEL;
	let request: any;
	let creates = 0;
	let deletes = 0;
	let fail = false;
	let failUsage = false;
	const plugin = await RLM({ client: { session: {
		create: async () => { creates++; return { data: { id: "child" } }; },
		prompt: async (value: any) => {
			request = value;
			if (fail) throw new Error("provider failed");
			return { data: { parts: [{ type: "text", text: "Partial evidence: source.ts:12" }] } };
		},
		messages: async () => {
			if (failUsage) throw new Error("usage unavailable");
			return { data: [{ info: {
				id: "msg_child", role: "assistant", providerID: "copilot", modelID: "small",
				tokens: { input: 10, output: 4, reasoning: 2, cache: { read: 20, write: 0 } },
				cost: 0, time: { completed: 123 },
			}, parts: [{ type: "text", text: "PRIVATE_CONTENT" }] }] };
		},
		delete: async () => { deletes++; },
	} } });
	const run = () => plugin.tool.rlm_subquery.execute({
		path: "/source/api", question: "Compare handlers", extraction_hint: "Include only error paths",
	}, { sessionID: "parent", messageID: "msg_parent" });
	try {
		assert.equal("experimental.chat.system.transform" in plugin, false);
		assert.match(await run(), /model is unavailable/);
		assert.equal(creates, 0);
		await plugin["chat.message"]({ sessionID: "parent", model: { providerID: "copilot", modelID: "main" } });
		await run();
		assert.deepEqual(request.body.model, { providerID: "copilot", modelID: "main" });
		await plugin.config({ small_model: "copilot/small" });
		assert.equal(await run(), "Partial evidence: source.ts:12");
		assert.deepEqual(request.body.model, { providerID: "copilot", modelID: "small" });
		assert.deepEqual(request.body.tools, { rlm: true, rlm_subquery: false });
		const prompt = request.body.parts[0].text;
		assert.ok(prompt.includes("Path: /source/api"));
		assert.ok(prompt.includes("Extraction hint: Include only error paths"));
		assert.ok(prompt.includes("Do not infer absence from a partial result"));
		assert.ok(prompt.includes("Do not modify files"));
		process.env.RLM_SUBQUERY_MODEL = "other/override";
		await run();
		assert.deepEqual(request.body.model, { providerID: "other", modelID: "override" });
		fail = true;
		await assert.rejects(run, /provider failed/);
		assert.equal(deletes, creates);
		const raw = await readFile(join(state, "opencode/task-usage/child.json"), "utf8");
		const saved = JSON.parse(raw);
		assert.equal(saved.parentSessionID, "parent");
		assert.equal(saved.parentMessageID, "msg_parent");
		assert.equal(saved.messages[0].tokens.input, 10);
		assert.ok(!raw.includes("PRIVATE_CONTENT"));
		fail = false;
		failUsage = true;
		await run();
		assert.equal(deletes, creates - 1, "retain child when usage cannot be recorded");
	} finally {
		if (previous === undefined) delete process.env.RLM_SUBQUERY_MODEL;
		else process.env.RLM_SUBQUERY_MODEL = previous;
		if (previousState === undefined) delete process.env.XDG_STATE_HOME;
		else process.env.XDG_STATE_HOME = previousState;
		await rm(state, { recursive: true, force: true });
	}
});
