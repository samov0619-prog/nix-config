import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

// Keep a normal focused search/read result intact, but never let one accidental
// broad command become a permanently large part of a live session.
const maxInlineChars = 12_000;
const headChars = 6_000;
const tailChars = 2_000;

const safePathPart = (value: string) => value.replace(/[^A-Za-z0-9._-]/g, "_");

export const OutputGovernor = async () => {
	const stateHome = process.env.XDG_STATE_HOME || join(process.env.HOME || ".", ".local", "state");
	const artifactRoot = join(stateHome, "opencode", "tool-artifacts");

	return {
		"tool.execute.after": async (
			input: { tool: string; sessionID: string; callID: string },
			output: { title: string; output: string; metadata?: Record<string, unknown> },
		) => {
			if (output.output.length <= maxInlineChars) return;

			const directory = join(artifactRoot, safePathPart(input.sessionID));
			const artifactPath = join(directory, `${safePathPart(input.callID)}.txt`);
			const originalChars = output.output.length;
			await mkdir(directory, { recursive: true });
			await writeFile(artifactPath, output.output, "utf8");

			const omittedChars = originalChars - headChars - tailChars;
			output.metadata = {
				...output.metadata,
				outputGovernor: {
					artifactPath,
					originalChars,
					omittedChars,
				},
			};
			output.output =
				`[Large ${input.tool} result preserved at ${artifactPath} (${originalChars} characters). ` +
				"The conversation contains only a preview. Use `rlm` with this path for further analysis.]\n\n" +
				output.output.slice(0, headChars) +
				`\n\n...[${omittedChars} characters omitted; full result is at the path above]...\n\n` +
				output.output.slice(-tailChars);
		},
	};
};
