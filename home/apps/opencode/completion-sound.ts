import { spawn } from "node:child_process";
import type { Plugin } from "@opencode-ai/plugin";

function playSound(sound: string) {
	// Home Manager substitutes store paths; playback must not capture the TUI.
	const player = spawn("@player@", [sound], { stdio: "ignore" });
	player.on("error", () => {
		// Audio availability must not affect the session.
	});
	player.unref();
}

export default (async ({ client }) => {
	const pending = new Map<string, { key: string; sound: string }>();
	const notified = new Map<string, string>();
	const latest = new Map<string, { id: string; summary?: boolean }>();
	let errorSequence = 0;

	function scheduleError(sessionID: string, error?: { name: string }) {
		const message = latest.get(sessionID);
		if (!error || error.name === "MessageAbortedError" || message?.summary) return;
		pending.set(sessionID, {
			key: `error:${message?.id ?? ++errorSequence}`,
			sound: "@errorSound@",
		});
	}

	return {
		event: async ({ event }) => {
			if (event.type === "message.updated") {
				const message = event.properties.info;
				pending.delete(message.sessionID);
				latest.set(message.sessionID, {
					id: message.id,
					summary: message.role === "assistant" && message.summary,
				});
				if (message.role === "assistant" && message.error) {
					scheduleError(message.sessionID, message.error);
					return;
				}
				if (
					message.role === "assistant" &&
					message.time.completed &&
					message.finish === "stop" &&
					!message.error &&
					!message.summary
				) {
					pending.set(message.sessionID, {
						key: `success:${message.id}`,
						sound: "@sound@",
					});
				}
				return;
			}

			if (event.type === "session.deleted") {
				const sessionID = event.properties.info.id;
				pending.delete(sessionID);
				notified.delete(sessionID);
				latest.delete(sessionID);
				return;
			}

			if (event.type === "session.error") {
				const sessionID = event.properties.sessionID;
				if (sessionID) {
					pending.delete(sessionID);
					scheduleError(sessionID, event.properties.error);
				}
				return;
			}

			if (event.type === "session.status") {
				// The closing prompt loop emits busy even after a completed answer.
				// Continued work invalidates transient errors, not successful completion.
				if (
					event.properties.status.type !== "idle" &&
					pending.get(event.properties.sessionID)?.key.startsWith("error:")
				) {
					pending.delete(event.properties.sessionID);
				}
				return;
			}

			if (event.type !== "session.idle") return;
			const sessionID = event.properties.sessionID;
			const notification = pending.get(sessionID);
			pending.delete(sessionID);
			if (!notification || notified.get(sessionID) === notification.key) return;
			// Reserve before the SDK await: cleanup can emit a second idle meanwhile.
			notified.set(sessionID, notification.key);

			try {
				const { data: session } = await client.session.get({
					path: { id: sessionID },
				});
				if (!session || session.parentID) return;
				playSound(notification.sound);
			} catch {
				// A deleted session or unavailable backend must not interrupt OpenCode.
			}
		},
	};
}) satisfies Plugin;
