import { spawn, type ChildProcess } from "node:child_process";
import { access, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

export type Settings = { model: string; language: string; mic: string; hotkey: string };

// Local ffmpeg + whisper.cpp only. No OpenCode/V1 SDK or cloud transcription.
export class VoiceRuntime {
	private child?: ChildProcess;
	private directory?: string;
	private cancelled = false;
	private stopRequested = false;

	private run(command: string, args: string[], recording = false): Promise<string> {
		return new Promise((resolve, reject) => {
			let output = "", errors = "", settled = false;
			const child = spawn(command, args, { stdio: ["pipe", "pipe", "pipe"] });
			child.stdin?.on("error", () => {}); // Recorder may exit before the stop key.
			this.child = child;
			if (recording && this.stopRequested) child.stdin?.end("q\n");
			let timer: ReturnType<typeof setTimeout>;
			const finish = (error?: Error) => {
				if (settled) return;
				settled = true;
				clearTimeout(timer);
				if (this.child === child) this.child = undefined;
				error ? reject(error) : resolve(output.trim());
			};
			child.stdout?.on("data", chunk => { output += chunk; });
			child.stderr?.on("data", chunk => { errors = (errors + chunk).slice(-4000); });
			child.on("error", error => finish(error));
			child.on("close", code => finish(this.cancelled ? new Error("Recording cancelled") :
				code !== 0 && !(recording && code === 255) ? new Error(errors || `${command}: exit ${code}`) : undefined));
			timer = setTimeout(() => {
				child.kill("SIGKILL");
				finish(new Error(`${command}: timed out`));
			}, recording ? 10 * 60_000 : 120_000);
		});
	}

	async record(settings: Settings): Promise<string> {
		if (process.platform !== "darwin") throw new Error("This recorder targets macOS AVFoundation");
		this.cancelled = false;
		this.stopRequested = false;
		try {
			await access(settings.model);
			if (this.cancelled) throw new Error("Recording cancelled");
			this.directory = await mkdtemp(join(tmpdir(), "opencode-voice-"));
			if (this.cancelled) throw new Error("Recording cancelled");
			const file = join(this.directory, "recording.wav");
			await this.run("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", "-f", "avfoundation",
				"-i", settings.mic || ":0", "-ac", "1", "-ar", "16000", file], true);
			if (this.cancelled) throw new Error("Recording cancelled");
			return await this.run("whisper-cli", ["-m", settings.model, "-f", file, "-np", "-nt", "-l", settings.language || "auto"]);
		} finally {
			await this.cleanup();
		}
	}

	stop() { this.stopRequested = true; this.child?.stdin?.end("q\n"); }
	cancel() { this.cancelled = true; this.child?.kill("SIGKILL"); }
	private async cleanup() {
		if (this.directory) await rm(this.directory, { recursive: true, force: true });
		this.directory = undefined;
	}
}
