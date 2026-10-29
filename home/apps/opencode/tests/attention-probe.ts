// Test-only sink: exercise the real notification plugin without audio/hardware.
// Every other TUI API (events, router, cache, plugin loader) is native.
import { Plugin } from "@opencode/plugin/tui";
import { appendFileSync, readFileSync, writeFileSync, renameSync } from "node:fs";
import { join } from "node:path";

export default Plugin.define({
	id: "test.attention-probe",
	setup(context) {
		const pane = process.env.KITTY_WINDOW_ID!;
		const base = join(process.env.XDG_STATE_HOME!, `attention-${pane}`);
		const original = context.attention.notify;
		context.attention.notify = async (request) => {
			appendFileSync(`${base}.jsonl`, JSON.stringify({ type: "attention", sound: typeof request.sound === "object" ? request.sound.name : null, route: context.ui.router.current() }) + "\n");
			return { ok: true, notification: true, sound: true };
		};
		const events = ["session.execution.started", "session.execution.succeeded", "session.execution.failed", "session.execution.interrupted", "permission.asked"] as const;
		const dispose = events.map(type => context.data.on(type, event => {
			appendFileSync(`${base}.jsonl`, JSON.stringify({ type: "event", event: type, sessionID: event.data.sessionID }) + "\n");
		}));
		let command = "";
		const timer = setInterval(() => {
			try {
				const next = readFileSync(`${base}.route`, "utf8").trim();
				if (next !== command) {
					command = next;
					context.ui.router.navigate(next === "home" ? { type: "home" } : { type: "session", sessionID: next });
				}
			} catch { /* No requested navigation. */ }
			writeFileSync(`${base}.state.tmp`, JSON.stringify({ route: context.ui.router.current(), plugins: true }));
			renameSync(`${base}.state.tmp`, `${base}.state`);
		}, 50);
		return () => {
			clearInterval(timer);
			context.attention.notify = original;
			dispose.forEach(cleanup => cleanup());
		};
	},
});
