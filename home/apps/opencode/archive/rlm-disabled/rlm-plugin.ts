import { z } from "zod";
import { saveSubqueryUsage } from "./lib/task-usage.ts";
// OpenCode injects the client; Zod is the only external runtime dependency.
// Global exploration policy belongs in AGENTS.md, not a second system prompt.

export const RLM = async ({ client }: { client: any }) => {
	const sessionModels = new Map<string, { providerID: string; modelID: string }>();
	let smallModel: { providerID: string; modelID: string } | undefined;

	const parseModel = (value: unknown) => {
		if (typeof value !== "string") return;
		value = value.trim();
		if (!value) return;
		const slash = value.indexOf("/");
		if (slash <= 0 || slash === value.length - 1) return;
		return { providerID: value.slice(0, slash), modelID: value.slice(slash + 1) };
	};

	return {
		"chat.message": async (input: {
			sessionID: string;
			model?: { providerID: string; modelID: string };
		}) => {
			if (input.model) sessionModels.set(input.sessionID, input.model);
		},
		config: async (config: { small_model?: unknown }) => {
			smallModel = parseModel(config.small_model);
		},
		tool: {
			rlm_subquery: {
				description:
					"Delegate semantic analysis of a large local file or directory to the configured small model. " +
					"Pass its path, never its contents: the child is instructed to extract evidence with `rlm`, " +
					"and the parent receives its text answer. Use only when delegation is permitted. " +
					"For mechanical extraction use direct tools instead.",
				args: {
					path: z.string().describe("Absolute or ~ path to the file or directory to analyze"),
					question: z.string().describe("What to extract/answer over that slice"),
					extraction_hint: z
						.string()
						.optional()
						.describe("Optional guidance for narrowing the source before analysis"),
				},
				async execute(
					args: { path: string; question: string; extraction_hint?: string },
					context: { sessionID: string; messageID?: string },
				) {
					const model =
						parseModel(process.env.RLM_SUBQUERY_MODEL) ??
						smallModel ??
						sessionModels.get(context.sessionID);
					if (!model) {
						return "[rlm_subquery: parent session model is unavailable]";
					}
					const started = Date.now();
					const created = await client.session.create({
						body: { title: "rlm-subquery" },
					});
					const id = created?.data?.id;
					if (!id) return "[rlm_subquery: failed to create sub-session]";
					try {
						const res = await client.session.prompt({
							path: { id },
							body: {
								// Prefer configured small_model; fall back to the parent's actual model.
								model,
								// Enable source extraction and disable recursive subqueries.
								// This map is not a sandbox or an exhaustive tool allowlist.
								tools: { rlm: true, rlm_subquery: false },
								parts: [
									{
										type: "text",
										text:
											"Analyze the local source at this path using the `rlm` tool before answering. " +
											"Do not answer from the path alone. Extract only the evidence needed for the question. " +
											"Inspect the load report and mention relevant skipped sources, tool failures, or " +
											"incomplete coverage in your answer. Do not infer absence from a partial result. " +
											"Do not modify files. Answer tersely with source references.\n\n" +
											`Path: ${args.path}\n` +
											`Question: ${args.question}` +
											(args.extraction_hint ? `\nExtraction hint: ${args.extraction_hint}` : ""),
									},
								],
							},
						});
						const parts = res?.data?.parts ?? [];
						const text = parts
							.filter((p: any) => p?.type === "text")
							.map((p: any) => p.text)
							.join("\n")
							.trim();
						return text || "[rlm_subquery: empty answer]";
					} finally {
						try {
							await saveSubqueryUsage(client, {
								parentSessionID: context.sessionID, parentMessageID: context.messageID,
								childSessionID: id, started,
							});
							await client.session.delete({ path: { id } }).catch(() => {});
						} catch {
							// Preserve the session if accounting fails; do not discard unrecorded usage.
							console.warn(`[rlm_subquery: usage capture failed; retained ${id}]`);
						}
					}
				},
			},
		},
	};
};
