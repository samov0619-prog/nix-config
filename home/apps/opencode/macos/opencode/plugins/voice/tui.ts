import { Plugin } from "@opencode/plugin/tui";
import { readFile, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import { VoiceRuntime, type Settings } from "./voice-runtime.ts";

export function setup(context: Plugin.Context, runtime = new VoiceRuntime()) {
	const file = join(process.env.OPENCODE_CONFIG_DIR ?? join(process.env.XDG_CONFIG_HOME ?? join(homedir(), ".config"), "opencode"), "voice.json");
	let settings: Settings = { model: join(homedir(), ".cache/opencode-voice/ggml-base.bin"), language: "auto", mic: ":0", hotkey: "ctrl+r" };
	let phase: "idle" | "recording" | "transcribing" = "idle";
	let disposed = false;
	let generation = 0;
	const notify = (message: string, variant: "info" | "error" | "success" = "info") => {
		if (!disposed) context.ui.toast.show({ title: "Local voice", message, variant });
	};
	const ready = readFile(file, "utf8").then(text => {
		const data = JSON.parse(text);
		for (const key of ["model", "language", "mic", "hotkey"] as const)
			if (typeof data[key] === "string") settings[key] = data[key];
	}).catch(error => { if (error.code !== "ENOENT") notify(`voice.json: ${error.message}`, "error"); });

	async function toggle() {
		await ready;
		if (phase === "transcribing") return;
		if (phase === "recording") {
			phase = "transcribing";
			runtime.stop();
			notify("Transcribing locally…");
			return;
		}
		// V2 has no public appendPrompt API. Capture the focused OpenTUI textarea,
		// then refuse insertion if the user changes focus/route while recording.
		const input = context.renderer.currentFocusedRenderable as any;
		if (!input || typeof input.insertText !== "function" || typeof input.plainText !== "string") {
			notify("Focus the main prompt, then press the recording key", "error");
			return;
		}
		const route = JSON.stringify(context.ui.router.current());
		const current = ++generation;
		phase = "recording";
		notify("Recording. Press the recording key again to transcribe.");
		try {
			const text = await runtime.record(settings);
			if (disposed || current !== generation) return;
			if (!text.trim()) throw new Error("Transcription was empty");
			if (JSON.stringify(context.ui.router.current()) !== route || context.renderer.currentFocusedRenderable !== input || input.isDestroyed) {
				await context.ui.dialog.prompt({ title: "Transcription — prompt changed; copy the text", value: text });
				return;
			}
			input.insertText(text.trim() + " ");
			notify("Transcribed; review the prompt before sending", "success");
		} catch (error) {
			if (current === generation) notify(error instanceof Error ? error.message : String(error), "error");
		} finally { phase = "idle"; }
	}

	async function configure() {
		await ready;
		if (phase !== "idle") { notify("Stop or cancel recording first", "error"); return; }
		for (const [key, title] of [["model", "Whisper model — absolute local path"], ["language", "Language (auto, ru, en…)"], ["mic", "AVFoundation microphone (:0, :1…)"], ["hotkey", "Recording key (restart OpenCode after changing)"]] as const) {
			const value = await context.ui.dialog.prompt({ title, value: settings[key] });
			if (value === undefined) return;
			settings[key] = value.trim();
		}
		await writeFile(file, JSON.stringify(settings, null, 2) + "\n", { mode: 0o600 });
		notify("Voice settings saved", "success");
	}
	function cancel() {
		generation++;
		runtime.cancel();
		// Keep new recording disabled until the previous process and cleanup settle.
		if (phase !== "idle") phase = "transcribing";
	}
	// Bind after loading the user's hotkey. Layers clean themselves up on dispose.
	void ready.then(() => {
		if (disposed) return;
		context.keymap.layer(() => ({ mode: "global", commands: [
			{ id: "local.voice", title: "Toggle local voice recording", bind: settings.hotkey, palette: true, slash: { name: "voice" }, run: toggle },
			{ id: "local.voice.settings", title: "Local voice settings", palette: true, slash: { name: "voice-settings" }, run: configure },
			{ id: "local.voice.cancel", title: "Cancel local voice", palette: true, slash: { name: "voice-stop" }, run: cancel },
		] }));
	});
	return () => { disposed = true; cancel(); };
}

export default Plugin.define({ id: "local.voice", setup });
