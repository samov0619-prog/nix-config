import { z } from "zod";
// type Plugin из @opencode-ai/plugin — type-only, стирается Bun'ом; `client` инжектится,
// поэтому рантайму снова нужен только zod.

const rlmReminder =
	"RLM is installed. Before repeated read/grep/glob calls, you MUST use `rlm` for logs, " +
	"directories, repository-wide analysis, unknown-size files, or more than two related files.";

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
		"experimental.chat.system.transform": async (
			_: { sessionID: string },
			output: { system: string[] },
		) => {
			output.system.push(rlmReminder);
		},
		tool: {
			rlm_subquery: {
				description:
					"Delegate semantic analysis of a large local file or directory to the configured small model. " +
					"Pass its path, never its contents: the child session can use only `rlm`, and the parent receives " +
					"only the final answer. For pure extraction use the `rlm` tool directly.",
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
					context: { sessionID: string },
				) {
					const model =
						parseModel(process.env.RLM_SUBQUERY_MODEL) ??
						smallModel ??
						sessionModels.get(context.sessionID);
					if (!model) {
						return "[rlm_subquery: parent session model is unavailable]";
					}
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
								// The child has no direct read/bash access, so the source never enters
								// the parent session as a large tool argument.
								tools: { rlm: true, rlm_subquery: false },
								parts: [
									{
										type: "text",
											text:
												"Analyze the local source at this path using the `rlm` tool before answering. " +
												"Do not answer from the path alone. Extract only the evidence needed for the question, " +
												"then answer tersely.\n\n" +
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
						await client.session.delete({ path: { id } }).catch(() => {});
					}
				},
			},
		},
	};
};
