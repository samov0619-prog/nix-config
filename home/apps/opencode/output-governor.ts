import { mkdir, open, stat, writeFile } from "node:fs/promises";
import { join } from "node:path";

// Keep a normal focused search/read result intact, but never let one accidental
// broad command become a permanently large part of a live session.
const maxInlineChars = 12_000;
const headChars = 4_000;
const tailChars = 1_000;

const safePathPart = (value: string) => value.replace(/[^A-Za-z0-9._-]/g, "_");

const previewNativeOutput = async (path: string, size: number) => {
	const file = await open(path, "r");
	try {
		const head = Buffer.alloc(Math.min(headChars, size));
		await file.read(head, 0, head.length, 0);
		if (size <= headChars + tailChars) {
			return { head: head.toString("utf8"), tail: "", omittedBytes: 0 };
		}

		const tail = Buffer.alloc(Math.min(tailChars, size - head.length));
		await file.read(tail, 0, tail.length, size - tail.length);
		return {
			head: head.toString("utf8"),
			tail: tail.toString("utf8"),
			omittedBytes: size - head.length - tail.length,
		};
	} finally {
		await file.close();
	}
};

export const OutputGovernor = async () => {
	const stateHome = process.env.XDG_STATE_HOME || join(process.env.HOME || ".", ".local", "state");
	const artifactRoot = join(stateHome, "opencode", "tool-artifacts");

	return {
		"tool.execute.after": async (
		input: { tool: string; sessionID: string; callID: string },
		output: { title: string; output: string; metadata?: Record<string, unknown> },
	) => {
			const nativePath =
				typeof output.metadata?.outputPath === "string" && output.metadata.truncated === true
					? output.metadata.outputPath
					: undefined;
			if (nativePath) {
				try {
					const { size } = await stat(nativePath);
					if (size > maxInlineChars) {
						const preview = await previewNativeOutput(nativePath, size);
						output.metadata = {
							...output.metadata,
							outputGovernor: {
								artifactPath: nativePath,
								originalBytes: size,
								omittedBytes: preview.omittedBytes,
								native: true,
							},
						};
						output.output =
							`[Large ${input.tool} result preserved at ${nativePath} (${size} bytes). ` +
							"The conversation contains only a preview. Use `rlm` with this path for further analysis.]\n\n" +
							preview.head +
							(preview.tail
								? `\n\n...[${preview.omittedBytes} bytes omitted; full result is at the path above]...\n\n${preview.tail}`
								: "");
						return;
					}
				} catch {
					// If OpenCode has already pruned its sidecar, use the normal fallback below.
				}
			}

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
