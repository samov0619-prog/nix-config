import assert from "node:assert/strict";
import childProcess from "node:child_process";
import { EventEmitter } from "node:events";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import fs from "node:fs/promises";
import { registerHooks, syncBuiltinESMExports } from "node:module";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, mock, test } from "node:test";
import { notificationsMuted, setNotificationsMuted } from "../notification-state.ts";

const stateHome = mkdtempSync(join(tmpdir(), "opencode-mute-test-"));
process.env.XDG_STATE_HOME = stateHome;
process.env.KITTY_WINDOW_ID = "42";
after(() => rmSync(stateHome, { recursive: true, force: true }));
const played = [];
const terminal = [];
mock.method(childProcess, "spawn", (...args) => {
	played.push(args);
	return Object.assign(new EventEmitter(), { unref() {} });
});
const originalOpen = fs.open;
mock.method(fs, "open", async (path, ...args) => path === "/dev/tty" ? {
	write: async (text) => terminal.push(text),
	close: async () => {},
} : originalOpen(path, ...args));
syncBuiltinESMExports();
registerHooks({
	resolve(specifier, context, nextResolve) {
		if (specifier === "@notificationState@") {
			return { url: new URL("../notification-state.ts", import.meta.url).href, shortCircuit: true };
		}
		return nextResolve(specifier, context);
	},
});
const { default: commandPlugin } = await import("../notification-commands.ts");
const { default: createNotifications } = await import("../notifications.ts");
const { default: createPermissions } = await import("../permission-stats.ts");

test("local slash commands mute all sounds, retain silent urgency and permission history, then unmute", async () => {
	const commands = [];
	const toasts = [];
	await commandPlugin.tui({
		keymap: { registerLayer: (layer) => commands.push(...layer.commands) },
		ui: { dialog: { clear() {} }, toast: (toast) => toasts.push(toast) },
	});
	assert.deepEqual(commands.map((command) => [command.slashName, command.namespace]), [
		["mute", "palette"], ["unmute", "palette"],
	]);
	const completion = await createNotifications({
		client: { session: { get: async () => ({ data: { id: "root" } }) } },
	});
	const permissions = await createPermissions();
	const answer = async (id, error) => {
		await completion.event({ event: { type: "message.updated", properties: { info: {
			id, sessionID: "root", role: "assistant", finish: "stop",
			time: { created: 1, completed: 2 }, ...(error ? { error: { name: "APIError" } } : {}),
		} } } });
		await completion.event({ event: { type: "session.idle", properties: { sessionID: "root" } } });
	};
	const ask = async (id) => {
		const input = { event: { type: "permission.asked", properties: {
			id, sessionID: "root", permission: "bash", patterns: ["test"],
		} } };
		await completion.event(input);
		await permissions.event(input);
	};

	assert.equal(notificationsMuted(), false);
	await answer("before-mute");
	await ask("before-mute");
	assert.equal(played.length, 2);
	assert.equal(terminal.length, 2, "success and permission both request attention");

	commands[0].run();
	commands[0].run();
	assert.equal(notificationsMuted(), true);
	await answer("muted-success");
	await answer("muted-error", true);
	assert.equal(played.length, 2, "both MP3 notifications stay silent");
	await ask("muted-permission");
	const sequence = terminal.at(-1);
	assert.ok(!sequence.includes("\x07"), "no audible BEL while muted");
	assert.ok(sequence.startsWith("\x1bP@kitty-cmd") && sequence.endsWith("\x1b\\"));
	const packet = JSON.parse(sequence.slice("\x1bP@kitty-cmd".length, -2));
	assert.equal(packet.cmd, "kitten");
	assert.equal(packet.no_response, true);
	assert.equal(packet.payload.match, "id:42", "target the requesting terminal, not the focused window");
	assert.equal(packet.payload.kitten, "@silentAttention@");
	assert.equal(terminal.length, 5, "all three muted events still request attention");
	await permissions.event({ event: { type: "permission.replied", properties: {
		requestID: "muted-permission", reply: "once",
	} } });
	const history = JSON.parse(readFileSync(join(stateHome, "opencode/permission-history.jsonl"), "utf8"));
	assert.equal(history.permission, "bash");
	assert.equal(history.response, "once");
	const reloadedNotifications = await createNotifications({ client: {} });
	await reloadedNotifications.event({ event: { type: "permission.asked", properties: {
		id: "after-reload", sessionID: "root", permission: "edit", patterns: ["test"],
	} } });
	assert.ok(!terminal.at(-1).includes("\x07"), "mute persists across plugin instances");

	commands[1].run();
	commands[1].run();
	assert.equal(notificationsMuted(), false);
	await answer("after-unmute");
	await answer("after-unmute-error", true);
	await ask("after-unmute");
	assert.deepEqual(played.map((call) => call[1][0]), [
		"@sound@", "@bellSound@", "@sound@", "@errorSound@", "@bellSound@",
	]);
	assert.ok(terminal.every((sequence) => !sequence.includes("\x07")));
	assert.ok(toasts.every((toast) => toast.variant === "info"));
});

test("muting during the session lookup suppresses already queued audio without replay after unmute", async () => {
	played.length = 0;
	const lookup = Promise.withResolvers();
	const plugin = await createNotifications({
		client: { session: { get: async () => {
			await lookup.promise;
			return { data: { id: "root" } };
		} } },
	});
	await plugin.event({ event: { type: "message.updated", properties: { info: {
		id: "pending", sessionID: "root", role: "assistant", finish: "stop",
		time: { created: 1, completed: 2 },
	} } } });
	const idle = plugin.event({ event: { type: "session.idle", properties: { sessionID: "root" } } });
	setNotificationsMuted(true);
	lookup.resolve();
	await idle;
	setNotificationsMuted(false);
	await plugin.event({ event: { type: "session.idle", properties: { sessionID: "root" } } });
	assert.equal(played.length, 0);
});
