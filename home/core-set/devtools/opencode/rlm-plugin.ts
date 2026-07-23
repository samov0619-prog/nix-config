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
					"Delegate analysis of a large context slice to the configured small model and return ONLY " +
					"its answer (keeps the root context small). Use for semantic aggregation over a slice that " +
					"can't be expressed as code. For pure extraction use the `rlm` tool instead.",
				args: {
					context: z.string().describe("The slice of text to analyze"),
					question: z.string().describe("What to extract/answer over that slice"),
				},
				async execute(
					args: { context: string; question: string },
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
								tools: { rlm: false, rlm_subquery: false },
								parts: [
									{
										type: "text",
										text: `Context:\n${args.context}\n\nAnswer ONLY this, tersely:\n${args.question}`,
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
