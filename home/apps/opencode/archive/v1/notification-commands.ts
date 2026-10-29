import type { TuiPluginModule } from "@opencode-ai/plugin/tui";
import { setNotificationsMuted } from "@notificationState@";

const commands = [
	{
		name: "mute",
		muted: true,
		title: "Mute OpenCode sounds",
		message: "OpenCode sounds muted; workspace alerts remain enabled",
	},
	{
		name: "unmute",
		muted: false,
		title: "Unmute OpenCode sounds",
		message: "OpenCode sounds enabled",
	},
];

export default {
	id: "local:notification-commands",
	tui: async (api) => {
		api.keymap.registerLayer({
			commands: commands.map((command) => ({
				name: `notifications.${command.name}`,
				title: command.title,
				category: "Notifications",
				namespace: "palette",
				slashName: command.name,
				run() {
					api.ui.dialog.clear();
					try {
						setNotificationsMuted(command.muted);
						api.ui.toast({
							variant: "info",
							message: command.message,
						});
					} catch {
						api.ui.toast({ variant: "error", message: "Could not save sound setting" });
					}
				},
			})),
		});
	},
} satisfies TuiPluginModule;
