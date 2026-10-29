import { spawn } from "node:child_process";
import { open } from "node:fs/promises";
import type { Plugin } from "@opencode-ai/plugin";
import { notificationsMuted } from "@notificationState@";

type NotificationKind = "permission" | "success" | "error";
type PendingNotification = { kind: "success" | "error"; key: string };
type Failure = { name: string; data?: unknown };
type SessionState = {
	status: "idle" | "busy" | "retry";
	user?: { id: string; created: number };
	latest?: {
		id: string;
		created: number;
		completed: boolean;
		summary?: boolean;
		error?: string;
	};
	pending?: PendingNotification;
	inFlight?: PendingNotification;
	notified: Set<string>;
	permissions: Map<string, "pending" | "replied">;
};

const sounds: Record<NotificationKind, string> = {
	permission: "@bellSound@",
	success: "@sound@",
	error: "@errorSound@",
};

function playSound(sound: string) {
	if (notificationsMuted()) return;
	try {
		const player = spawn("@player@", [sound], { stdio: "ignore" });
		player.on("error", () => {});
		player.unref();
	} catch {
		// Audio availability must not affect the session or visual attention.
	}
}

async function requestAttention(isCurrent: () => boolean) {
	const windowID = process.env.KITTY_WINDOW_ID;
	if (!windowID || !/^\d+$/.test(windowID)) return;
	try {
		const tty = await open("/dev/tty", "w");
		try {
			if (!isCurrent()) return;
			// No BEL and no remote-control reply: urgency is independent of audio.
			await tty.write(`\x1bP@kitty-cmd${JSON.stringify({
				cmd: "kitten",
				version: [0, 14, 2],
				no_response: true,
				payload: { match: `id:${windowID}`, kitten: "@silentAttention@", args: [] },
			})}\x1b\\`);
		} finally {
			await tty.close();
		}
	} catch {
		// Headless backends have no controlling terminal. Audio still works.
	}
}

async function notify(kind: NotificationKind, isCurrent: () => boolean) {
	if (!isCurrent()) return;
	playSound(sounds[kind]);
	await requestAttention(isCurrent);
}

function newState(status: SessionState["status"] = "idle"): SessionState {
	return { status, notified: new Set(), permissions: new Map() };
}

function errorSignature(error: Failure) {
	return JSON.stringify([error.name, error.data]);
}

export default (async ({ client }) => {
	const sessions = new Map<string, SessionState>();
	function stateFor(sessionID: string) {
		let state = sessions.get(sessionID);
		if (!state) {
			state = newState();
			sessions.set(sessionID, state);
		}
		return state;
	}

	function schedule(state: SessionState, notification: PendingNotification) {
		if (state.notified.has(notification.key)) return;
		// Retain the same object through duplicate error/message cleanup events.
		if (state.pending?.key !== notification.key) state.pending = notification;
	}

	async function flush(sessionID: string, state: SessionState) {
		const notification = state.pending;
		if (!notification || state.inFlight === notification) return;
		// Reserve before the SDK await; repeated idle must not start a second lookup.
		state.inFlight = notification;
		const isCurrent = () => sessions.get(sessionID) === state && state.pending === notification;
		try {
			const { data: session } = await client.session.get({ path: { id: sessionID } });
			if (!session || session.parentID || !isCurrent()) return;
			state.notified.add(notification.key);
			await notify(notification.kind, isCurrent);
		} catch {
			// A deleted session or unavailable backend must not interrupt OpenCode.
		} finally {
			if (state.pending === notification) state.pending = undefined;
			if (state.inFlight === notification) state.inFlight = undefined;
		}
	}

	return {
		event: async ({ event }) => {
			if (event.type === "session.deleted") {
				sessions.delete(event.properties.info.id);
				return;
			}

			if (event.type === "permission.asked") {
				const request = event.properties;
				const state = stateFor(request.sessionID);
				if (state.permissions.has(request.id)) return;
				state.permissions.set(request.id, "pending");
				await notify("permission", () =>
					sessions.get(request.sessionID) === state && state.permissions.get(request.id) === "pending");
				return;
			}

			if (event.type === "permission.replied") {
				const state = sessions.get(event.properties.sessionID);
				if (state?.permissions.has(event.properties.requestID)) {
					state.permissions.set(event.properties.requestID, "replied");
				}
				return;
			}

			if (event.type === "message.updated") {
				const message = event.properties.info;
				let state = stateFor(message.sessionID);
				if (message.role === "user") {
					if (state.user?.id === message.id ||
						(state.user && message.time.created < state.user.created)) return;
					// Replace the record so in-flight notifications from the old prompt expire.
					// A queued prompt does not change the running session's status.
					state = newState(state.status);
					state.user = { id: message.id, created: message.time.created };
					sessions.set(message.sessionID, state);
					return;
				}
				if ((state.user && message.parentID !== state.user.id) ||
					(state.latest && message.time.created < state.latest.created)) return;
				state.latest = {
					id: message.id, created: message.time.created,
					completed: !!message.time.completed, summary: message.summary,
					error: message.error && errorSignature(message.error),
				};
				if (message.summary || message.error?.name === "MessageAbortedError") {
					state.pending = undefined;
				} else if (message.error) {
					schedule(state, { kind: "error", key: `message:${message.id}:error` });
					if (state.status === "idle") await flush(message.sessionID, state);
				} else if (message.time.completed && message.finish === "stop") {
					schedule(state, { kind: "success", key: `message:${message.id}:success` });
				} else {
					state.pending = undefined;
				}
				return;
			}

			if (event.type === "session.error") {
				const { sessionID, error } = event.properties;
				if (!sessionID || !error) return;
				const state = stateFor(sessionID);
				if (error.name === "MessageAbortedError") {
					state.pending = undefined;
					return;
				}
				const message = state.latest;
				if (message?.summary && state.status !== "idle") return;
				const signature = errorSignature(error);
				const belongsToMessage = message && (!message.completed || message.error === signature);
				// Runtime bus IDs distinguish separate early failures and deduplicate replays.
				const eventID = (event as typeof event & { id?: string }).id;
				const key = belongsToMessage ? `message:${message.id}:error` : `event:${eventID ?? signature}`;
				schedule(state, { kind: "error", key });
				if (state.status === "idle") await flush(sessionID, state);
				return;
			}

			if (event.type === "session.status") {
				const state = stateFor(event.properties.sessionID);
				state.status = event.properties.status.type;
				// The closing prompt loop emits busy even after a completed answer.
				if (state.status !== "idle" && state.pending?.kind === "error") state.pending = undefined;
				return;
			}

			if (event.type === "session.idle") {
				const state = stateFor(event.properties.sessionID);
				state.status = "idle";
				await flush(event.properties.sessionID, state);
			}
		},
	};
}) satisfies Plugin;
