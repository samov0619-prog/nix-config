import assert from "node:assert/strict";
import childProcess from "node:child_process";
import { EventEmitter } from "node:events";
import { syncBuiltinESMExports } from "node:module";
import { mock, test } from "node:test";

const calls = [];
mock.method(childProcess, "spawn", (...args) => {
	calls.push(args);
	const child = new EventEmitter();
	child.unref = () => {};
	// Exercise the error handler too: playback must remain harmless without audio.
	queueMicrotask(() => child.emit("error", new Error("no audio device")));
	return child;
});
syncBuiltinESMExports();
const { default: createPlugin } = await import("../completion-sound.ts");

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
	const message = (sessionID, id, extra = {}) => event("message.updated", {
		info: { sessionID, id, role: "assistant", time: { created: 1 }, ...extra },
	});
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
	await failure("root");
	await event("session.deleted", { info: { id: "root" } });
	await idle("root");
	assert.equal(calls.length, 3, "retry and deleted session do not notify a stale error");
});
