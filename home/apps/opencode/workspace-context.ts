import type { TuiPluginModule } from "@opencode-ai/plugin/tui";
import { mkdirSync, readFileSync, renameSync, unlinkSync, writeFileSync } from "node:fs";
import { join } from "node:path";

// The TUI route identifies the viewed session, including idle sessions and
// navigation without a prompt. Backend message events cannot identify that.
export default {
	id: "local:workspace-context",
	tui: async (api) => {
		const runtime = process.env.XDG_RUNTIME_DIR;
		const pane = process.env.KITTY_WINDOW_ID;
		if (process.platform !== "linux" || !runtime || !pane || !/^\d+$/.test(pane)) return;
		let start: string;
		try {
			const stat = readFileSync(`/proc/${process.pid}/stat`, "utf8");
			start = stat.slice(stat.lastIndexOf(")") + 2).split(/\s+/)[19];
			if (!start) return;
		} catch { return; }
		const directory = join(runtime, "hypr-spaces", "apps");
		const path = join(directory, `${process.pid}.json`);
		const temporary = `${path}.tmp`;
		let previous = "";
		const publish = () => {
			try {
				const route = api.route.current;
				const id = route.name === "session" ? route.params?.sessionID : undefined;
				const session = typeof id === "string" ? api.state.session.get(id) : undefined;
				const payload = JSON.stringify({
					app: "opencode", pane, start,
					title: session?.title || "",
					cwd: session?.directory || api.state.path.directory,
				});
				if (payload === previous) return;
				mkdirSync(directory, { recursive: true, mode: 0o700 });
				writeFileSync(temporary, payload, { mode: 0o600 });
				renameSync(temporary, path);
				previous = payload;
			} catch { /* Optional desktop metadata must never interrupt the TUI. */ }
		};
		publish();
		const timer = setInterval(publish, 500);
		timer.unref?.();
		api.lifecycle.onDispose(() => {
			clearInterval(timer);
			for (const file of [path, temporary]) {
				try { unlinkSync(file); } catch { /* Already removed or never published. */ }
			}
		});
	},
} satisfies TuiPluginModule;
