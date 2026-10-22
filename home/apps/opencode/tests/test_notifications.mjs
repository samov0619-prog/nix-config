import assert from "node:assert/strict";
import childProcess from "node:child_process";
import { EventEmitter } from "node:events";
import { mkdtempSync, rmSync } from "node:fs";
import fs from "node:fs/promises";
import { registerHooks, syncBuiltinESMExports } from "node:module";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, mock, test } from "node:test";

const stateHome = mkdtempSync(join(tmpdir(), "opencode-completion-test-"));
process.env.XDG_STATE_HOME = stateHome;
after(() => rmSync(stateHome, { recursive: true, force: true }));
registerHooks({
	resolve(specifier, context, nextResolve) {
		if (specifier === "@notificationState@") {
			return { url: new URL("../notification-state.ts", import.meta.url).href, shortCircuit: true };
		}
		return nextResolve(specifier, context);
	},
});

const calls = [];
const terminal = [];
let failAudio = false;
let failAttention = false;
mock.method(childProcess, "spawn", (...args) => {
	if (failAudio) throw new Error("player unavailable");
	calls.push(args);
	const child = new EventEmitter();
	child.unref = () => {};
	// Exercise the error handler too: playback must remain harmless without audio.
	queueMicrotask(() => child.emit("error", new Error("no audio device")));
	return child;
});
mock.method(fs, "open", async () => {
	if (failAttention) throw new Error("no controlling terminal");
	return { write: async (text) => terminal.push(text), close: async () => {} };
});
process.env.KITTY_WINDOW_ID = "42";
syncBuiltinESMExports();
const { default: createPlugin } = await import("../notifications.ts");

test("only completed root answers notify, once each, after idle", async () => {
	calls.length = 0;
	const plugin = await createPlugin({
		client: {
			session: {
				get: async ({ path: { id } }) => {
					if (id === "unavailable") throw new Error("backend unavailable");
					return { data: { id, ...(id === "child" ? { parentID: "root" } : {}) } };
				},
			},
		},
	});
	const event = (type, properties) => plugin.event({ event: { type, properties } });
	const message = (sessionID, id, extra = {}) =>
		event("message.updated", {
			info: {
				sessionID, id, role: "assistant", finish: "stop",
				time: { created: 1, completed: 2 }, ...extra,
			},
		});
	const idle = (sessionID) => event("session.idle", { sessionID });

	await idle("root");
	await message("root", "streaming", { time: { created: 1 } });
	await idle("root");
	await message("root", "tool", { finish: "tool-calls" });
	await idle("root");
	await message("child", "child-answer");
	await idle("child");
	await message("root", "compaction", { summary: true });
	await idle("root");
	await message("root", "aborted", { error: { name: "MessageAbortedError" } });
	await idle("root");
	await message("root", "length", { finish: "length" });
	await idle("root");
	assert.equal(calls.length, 0);

	await message("root", "answer-1");
	assert.equal(calls.length, 0, "wait until the whole session is idle");
	await idle("root");
	assert.equal(calls.length, 1);
	await idle("root");
	await message("root", "answer-1");
	await idle("root");
	assert.equal(calls.length, 1, "duplicate updates do not replay the sound");

	await message("root", "answer-2");
	await Promise.all([idle("root"), idle("root")]);
	assert.equal(calls.length, 2, "the next answer notifies exactly once");

	await message("root", "stale-answer");
	await message("root", "new-prompt", { role: "user" });
	await idle("root");
	await message("root", "before-error");
	await event("session.error", { sessionID: "root" });
	await idle("root");
	await message("deleted", "answer");
	await event("session.deleted", { info: { id: "deleted" } });
	await idle("deleted");
	await message("unavailable", "answer");
	await idle("unavailable");
	assert.equal(calls.length, 2);
	assert.deepEqual(calls[0], ["@player@", ["@sound@"], { stdio: "ignore" }]);
});

test("closing busy status preserves the completed answer until idle", async () => {
	calls.length = 0;
	const plugin = await createPlugin({
		client: { session: { get: async () => ({ data: { id: "root" } }) } },
	});
	const event = (type, properties) => plugin.event({ event: { type, properties } });
	await event("message.updated", {
		info: {
			id: "answer", sessionID: "root", role: "assistant", finish: "stop",
			time: { created: 1, completed: 2 },
		},
	});
	// SessionPrompt.runLoop sets busy before checking that the last answer is done.
	await event("session.status", { sessionID: "root", status: { type: "busy" } });
	await event("session.status", { sessionID: "root", status: { type: "idle" } });
	await event("session.idle", { sessionID: "root" });
	assert.deepEqual(calls, [["@player@", ["@sound@"], { stdio: "ignore" }]]);
});

for (const status of ["busy", "retry"]) {
	test(`recoverable errors stay silent when a new prompt arrives during ${status}`, async () => {
		calls.length = 0;
		terminal.length = 0;
		const plugin = await createPlugin({
			client: { session: { get: async () => ({ data: { id: "root" } }) } },
		});
		const event = (type, properties) => plugin.event({ event: { type, properties } });
		await event("message.updated", { info: {
			id: "old-user", sessionID: "root", role: "user", time: { created: 1 },
		} });
		await event("session.status", { sessionID: "root", status: { type: status } });
		await event("message.updated", { info: {
			id: "queued-user", sessionID: "root", role: "user", time: { created: 2 },
		} });
		await event("session.error", {
			sessionID: "root", error: { name: "ContextOverflowError" },
		});
		assert.equal(calls.length, 0, "the queued prompt does not make the run idle");
		assert.equal(terminal.length, 0, "a recoverable error must not request attention");

		await event("session.status", { sessionID: "root", status: { type: "busy" } });
		await event("message.updated", { info: {
			id: "summary", parentID: "queued-user", sessionID: "root", role: "assistant",
			summary: true, finish: "stop", time: { created: 3, completed: 4 },
		} });
		await event("message.updated", { info: {
			id: "answer", parentID: "queued-user", sessionID: "root", role: "assistant",
			finish: "stop", time: { created: 5, completed: 6 },
		} });
		assert.equal(calls.length, 0, "the recovered answer still waits for idle");
		await event("session.idle", { sessionID: "root" });
		assert.deepEqual(calls, [["@player@", ["@sound@"], { stdio: "ignore" }]]);
		assert.equal(terminal.length, 1, "only the completed answer requests attention");
	});
}

test("overlapping error cleanup cannot notify twice while session lookup is pending", async () => {
	calls.length = 0;
	const lookup = Promise.withResolvers();
	const plugin = await createPlugin({
		client: { session: { get: async () => {
			await lookup.promise;
			return { data: { id: "root" } };
		} } },
	});
	const event = (type, properties) => plugin.event({ event: { type, properties } });
	const failed = {
		id: "failed-answer", sessionID: "root", role: "assistant",
		time: { created: 1 }, error: { name: "APIError" },
	};
	await event("session.status", { sessionID: "root", status: { type: "busy" } });
	await event("message.updated", { info: failed });
	const firstIdle = event("session.idle", { sessionID: "root" });
	await event("message.updated", {
		info: { ...failed, time: { created: 1, completed: 2 } },
	});
	const cleanupIdle = event("session.idle", { sessionID: "root" });
	lookup.resolve();
	await Promise.all([firstIdle, cleanupIdle]);
	assert.deepEqual(calls, [["@player@", ["@errorSound@"], { stdio: "ignore" }]]);
});

test("terminal root errors use the error sound, without retry or cleanup duplicates", async () => {
	calls.length = 0;
	const plugin = await createPlugin({
		client: {
			session: {
				get: async ({ path: { id } }) => ({
					data: { id, ...(id === "child" ? { parentID: "root" } : {}) },
				}),
			},
		},
	});
	const event = (type, properties) => plugin.event({ event: { type, properties } });
	const message = async (sessionID, id, extra = {}) => {
		if (!extra.time?.completed) {
			await event("session.status", { sessionID, status: { type: "busy" } });
		}
		await event("message.updated", {
			info: { sessionID, id, role: "assistant", time: { created: 1 }, ...extra },
		});
	};
	const failure = (sessionID, error = { name: "APIError" }) =>
		event("session.error", { sessionID, error });
	const idle = (sessionID) => event("session.idle", { sessionID });

	await message("root", "failed-answer");
	await failure("root");
	assert.equal(calls.length, 0, "wait until the failed run becomes idle");
	await idle("root");
	assert.deepEqual(calls, [["@player@", ["@errorSound@"], { stdio: "ignore" }]]);
	await message("root", "failed-answer", {
		error: { name: "APIError" }, time: { created: 1, completed: 2 },
	});
	await idle("root");
	await failure("root");
	await idle("root");
	assert.equal(calls.length, 1, "message cleanup and repeated errors do not replay");

	await message("root", "second-failure");
	await failure("root");
	await Promise.all([idle("root"), idle("root")]);
	assert.equal(calls.length, 2, "a new failed answer notifies once");

	await message("child", "child-failure");
	await failure("child");
	await idle("child");
	await message("root", "compaction", { summary: true });
	await failure("root");
	await idle("root");
	await message("root", "cancelled");
	await failure("root", { name: "MessageAbortedError" });
	await idle("root");
	await failure(undefined);
	await idle("root");
	assert.equal(calls.length, 2, "child, compaction and cancellation stay silent");

	await message("root", "recovered-overflow");
	await failure("root", { name: "ContextOverflowError" });
	await message("root", "recovered-overflow", {
		finish: "stop", time: { created: 1, completed: 2 },
	});
	await idle("root");
	assert.equal(calls.length, 3);
	assert.equal(calls.at(-1)[1][0], "@sound@", "successful recovery uses the success sound");

	await message("root", "retry");
	await failure("root");
	await event("session.status", { sessionID: "root", status: { type: "retry" } });
	await idle("root");
	await message("root", "new-prompt", { role: "user" });
	await event("session.status", { sessionID: "root", status: { type: "busy" } });
	await failure("root");
	await event("session.deleted", { info: { id: "root" } });
	await idle("root");
	assert.equal(calls.length, 3, "retry and deleted session do not notify a stale error");
});

test("permission, success and error share one audio path and silent terminal attention", async () => {
	calls.length = 0;
	terminal.length = 0;
	const plugin = await createPlugin({
		client: { session: { get: async () => ({ data: { id: "root" } }) } },
	});
	const event = (type, properties) => plugin.event({ event: { type, properties } });
	const permission = { id: "request", sessionID: "child", permission: "bash", patterns: ["test"] };
	await event("permission.asked", permission);
	await event("permission.asked", permission);
	await event("permission.replied", { sessionID: "child", requestID: "request", reply: "once" });
	await event("permission.asked", permission);
	await event("message.updated", { info: {
		id: "answer", sessionID: "root", role: "assistant", finish: "stop",
		time: { created: 1, completed: 2 },
	} });
	await event("session.idle", { sessionID: "root" });
	await event("session.error", { sessionID: "root", error: { name: "APIError" } });
	assert.deepEqual(calls.map((call) => call[1][0]), ["@bellSound@", "@sound@", "@errorSound@"]);
	assert.equal(terminal.length, 3);
	for (const sequence of terminal) {
		assert.ok(!sequence.includes("\x07"), "OpenCode never emits an audible BEL");
		const packet = JSON.parse(sequence.slice("\x1bP@kitty-cmd".length, -2));
		assert.equal(packet.no_response, true);
		assert.equal(packet.payload.match, "id:42");
	}
});

for (const invalidation of ["new prompt", "deleted session", "cancelled run", "retry"]) {
	test(`a pending SDK lookup cannot notify after ${invalidation}`, async () => {
		calls.length = 0;
		terminal.length = 0;
		const lookup = Promise.withResolvers();
		const plugin = await createPlugin({ client: { session: { get: async () => {
			await lookup.promise;
			return { data: { id: "root" } };
		} } } });
		const event = (type, properties) => plugin.event({ event: { type, properties } });
		await event("session.status", { sessionID: "root", status: { type: "busy" } });
		await event("message.updated", { info: {
			id: "answer", sessionID: "root", role: "assistant", finish: "stop",
			time: { created: 1, completed: 2 },
			...(invalidation === "retry" ? { error: { name: "APIError" } } : {}),
		} });
		const idle = event("session.idle", { sessionID: "root" });
		if (invalidation === "new prompt") {
			await event("message.updated", { info: {
				id: "new-user", sessionID: "root", role: "user", time: { created: 3 },
			} });
		} else if (invalidation === "deleted session") {
			await event("session.deleted", { info: { id: "root" } });
		} else if (invalidation === "cancelled run") {
			await event("session.error", { sessionID: "root", error: { name: "MessageAbortedError" } });
		} else {
			await event("session.status", { sessionID: "root", status: { type: "retry" } });
		}
		lookup.resolve();
		await idle;
		assert.equal(calls.length, 0);
		assert.equal(terminal.length, 0);
	});
}

test("late message cleanup from an old prompt cannot replace the current answer", async () => {
	calls.length = 0;
	const plugin = await createPlugin({ client: { session: { get: async () => ({ data: { id: "root" } }) } } });
	const event = (type, properties) => plugin.event({ event: { type, properties } });
	await event("message.updated", { info: {
		id: "new-user", role: "user", sessionID: "root", time: { created: 3 },
	} });
	await event("message.updated", { info: {
		id: "new-answer", role: "assistant", parentID: "new-user", sessionID: "root",
		finish: "stop", time: { created: 4, completed: 5 },
	} });
	await event("message.updated", { info: {
		id: "old-answer", role: "assistant", parentID: "old-user", sessionID: "root",
		error: { name: "APIError" }, time: { created: 1, completed: 6 },
	} });
	await event("session.idle", { sessionID: "root" });
	assert.deepEqual(calls.map((call) => call[1][0]), ["@sound@"]);
});

test("early errors notify while already idle; replay IDs deduplicate without hiding new failures", async () => {
	calls.length = 0;
	terminal.length = 0;
	const plugin = await createPlugin({ client: { session: { get: async () => ({ data: { id: "root" } }) } } });
	const error = { name: "UnknownError", data: { message: "Command not found" } };
	const failure = (id) => plugin.event({ event: {
		id, type: "session.error", properties: { sessionID: "root", error },
	} });
	await failure("event-1");
	assert.equal(calls.length, 1, "no future idle event is needed");
	await failure("event-1");
	assert.equal(calls.length, 1, "a replay of the same bus event stays silent");
	await failure("event-2");
	await failure("event-1");
	assert.equal(calls.length, 2, "a distinct failed operation with the same error still notifies");
	assert.equal(terminal.length, 2);
});

test("audio and attention failures are independent", async () => {
	calls.length = 0;
	terminal.length = 0;
	const plugin = await createPlugin({ client: {} });
	const permission = (id) => plugin.event({ event: { type: "permission.asked", properties: {
		id, sessionID: "root", permission: "bash", patterns: ["test"],
	} } });
	try {
		failAudio = true;
		await permission("no-audio");
		assert.equal(terminal.length, 1);
		failAudio = false;
		failAttention = true;
		await permission("no-terminal");
		assert.equal(calls.length, 1);
	} finally {
		failAudio = false;
		failAttention = false;
	}
});
