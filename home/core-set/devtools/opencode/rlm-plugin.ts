import { z } from "zod";
// type Plugin из @opencode-ai/plugin — type-only, стирается Bun'ом; `client` инжектится,
// поэтому рантайму снова нужен только zod.

export const RLM = async ({ client }: { client: any }) => ({
	tool: {
		rlm_subquery: {
			description:
				"Delegate analysis of a large context slice to a cheap sub-model and return ONLY its " +
				"answer (keeps the root context small). Use for semantic aggregation over a slice that " +
				"can't be expressed as code. For pure extraction use the `rlm` tool instead.",
			args: {
				context: z.string().describe("The slice of text to analyze"),
				question: z.string().describe("What to extract/answer over that slice"),
			},
			async execute(args: { context: string; question: string }) {
				// Изолированная под-сессия, чтобы срез не тёк в контекст корня.
				const created = await client.session.create({
					body: { title: "rlm-subquery" },
				});
				const id = created?.data?.id;
				if (!id) return "[rlm_subquery: failed to create sub-session]";
				try {
					const res = await client.session.prompt({
						path: { id },
						body: {
							// model НЕ задаём → наследует модель сессии (дефолт opencode zen).
							// Пинить дешёвую модель декларативно (синхронно с default.nix, провайдер должен быть залогинен):
							//   model: { providerID: "opencode",  modelID: "grok-code" },       // zen, бесплатно
							//   model: { providerID: "anthropic", modelID: "claude-haiku-4-5" },
							//   model: { providerID: "deepseek",  modelID: "deepseek-chat" },
              model: { providerID: "opencode", modelID: "deepseek-v4-flash-free" },
							tools: { rlm: false, rlm_subquery: false }, // не даём суб-вызову рекурсить в RLM
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
});
