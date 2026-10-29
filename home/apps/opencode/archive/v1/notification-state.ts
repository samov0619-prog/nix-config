import { existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

function stateDirectory() {
	const stateHome =
		process.env.XDG_STATE_HOME ?? join(process.env.HOME ?? ".", ".local", "state");
	return join(stateHome, "opencode");
}

export function notificationsMuted() {
	return existsSync(join(stateDirectory(), "notifications-muted"));
}

export function setNotificationsMuted(muted: boolean) {
	const directory = stateDirectory();
	const path = join(directory, "notifications-muted");
	if (muted) {
		mkdirSync(directory, { recursive: true });
		writeFileSync(path, "", { mode: 0o600 });
	} else {
		rmSync(path, { force: true });
	}
}
