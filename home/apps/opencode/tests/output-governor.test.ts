import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { OutputGovernor } from "../output-governor.ts";

const input = { tool: "tasks-confluence_confluence_get_page", sessionID: "session", callID: "call" };

test("MCP and other non-string results pass through without mutation", async () => {
	const after = (await OutputGovernor())["tool.execute.after"];
	const results = [
		undefined,
		null,
		{},
		{ content: [{ type: "text", text: "page" }], isError: false },
		{ content: [{ type: "image", data: "encoded", mimeType: "image/png" }], structuredContent: { page: 1 } },
		{ content: [{ type: "text", text: "error" }], isError: true },
		{ output: null },
		{ output: { content: "structured" } },
		// Must return before even attempting native-artifact processing.
		{ metadata: { truncated: true, outputPath: "/does-not-exist" } },
	];
	for (const result of results) {
		const before = structuredClone(result);
		await after(input, result);
		assert.deepEqual(result, before);
	}
});

test("short string results remain unchanged", async () => {
	const after = (await OutputGovernor())["tool.execute.after"];
	for (const text of ["", "page", "x".repeat(12_000)]) {
		const result = { output: text, metadata: { custom: true } };
		await after(input, result);
		assert.deepEqual(result, { output: text, metadata: { custom: true } });
	}
});

test("long string results retain a full artifact and shorten the inline output", async () => {
	const directory = await mkdtemp(join(tmpdir(), "output-governor-test-"));
	const previous = process.env.XDG_STATE_HOME;
	let after: Awaited<ReturnType<typeof OutputGovernor>>["tool.execute.after"];
	try {
		process.env.XDG_STATE_HOME = directory;
		after = (await OutputGovernor())["tool.execute.after"];
	} finally {
		if (previous === undefined) delete process.env.XDG_STATE_HOME;
		else process.env.XDG_STATE_HOME = previous;
	}
	try {
		const original = "page content\n".repeat(2_000);
		const result = { output: original, metadata: { custom: true } };
		await after(input, result);
		const path = join(directory, "opencode", "tool-artifacts", "session", "call.txt");
		assert.equal(await readFile(path, "utf8"), original);
		assert.ok(result.output.includes(path));
		assert.ok(result.output.length < 12_000);
		assert.equal(result.metadata.custom, true);
	} finally {
		await rm(directory, { recursive: true, force: true });
	}
});

test("native truncated text artifacts are reused", async () => {
	const directory = await mkdtemp(join(tmpdir(), "output-governor-native-"));
	try {
		const path = join(directory, "native.txt");
		const original = "native page\n".repeat(2_000);
		await writeFile(path, original);
		const after = (await OutputGovernor())["tool.execute.after"];
		const result = { output: "native preview", metadata: { truncated: true, outputPath: path } };
		await after(input, result);
		assert.ok(result.output.includes(path));
		assert.ok(result.output.length < 12_000);
		assert.equal(await readFile(path, "utf8"), original);
	} finally {
		await rm(directory, { recursive: true, force: true });
	}
});
