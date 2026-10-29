import { Plugin } from "@opencode/plugin/tui";
import { open } from "node:fs/promises";
import { sessionAttention } from "@sessionAttention@";

// Audio belongs exclusively to opencode.notifications / attention.sound.
export async function requestAttention() {
	const pane = process.env.KITTY_WINDOW_ID;
	if (!pane || !/^\d+$/.test(pane)) return;
	try {
		const tty = await open("/dev/tty", "w");
		try {
			await tty.write(`\x1bP@kitty-cmd${JSON.stringify({
				cmd: "kitten", version: [0, 14, 2], no_response: true,
				payload: { match: `id:${pane}`, kitten: "@silentAttention@", args: [] },
			})}\x1b\\`);
		} finally { await tty.close(); }
	} catch { /* Optional desktop integration must never interrupt the session. */ }
}

export default Plugin.define({
	id: "local.quiet-urgency",
	setup(context) {
		const dispose = [
			"permission.asked", "form.created", "session.execution.succeeded",
			"session.execution.failed", "session.execution.interrupted",
		].map((type) => context.data.on(type, (event) => {
			const sessionID = event.type === "form.created" ? event.data.form.sessionID : event.data.sessionID;
			if (sessionAttention(context, sessionID)) void requestAttention();
		}));
		return () => dispose.forEach((cleanup) => cleanup());
	},
});
