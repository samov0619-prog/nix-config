import { Plugin } from "@opencode/plugin";

export function offlineEnvironment(env: Record<string, string | undefined>) {
	// Git refuses transport initialization before contacting any remote. Also
	// prevent ordinary read commands in a partial clone from fetching objects.
	env.GIT_ALLOW_PROTOCOL = "";
	env.GIT_NO_LAZY_FETCH = "1";
	env.GIT_TERMINAL_PROMPT = "0";
}

export default Plugin.define({
	id: "local.git-offline",
	async setup(context) {
		const hook = await context.shell.hook("create.before", ({ env }) => offlineEnvironment(env));
		return () => hook.dispose();
	},
});
