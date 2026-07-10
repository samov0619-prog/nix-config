import { z } from "zod";

// ─── RLM Вариант 1: depth-0 ─────────────────────────────────────────────
// «Context as a variable in a REPL» (arXiv:2512.24601). Тяжёлый ввод грузится
// в Python-переменную `ctx` и в контекст LLM НЕ попадает; модель print-ит только срез.
// tool() из @opencode-ai/plugin — это passthrough (return input), tool.schema = zod,
// поэтому обходимся плоским объектом + zod (единственная рантайм-зависимость).
export default {
	description:
		"RLM REPL. For files/dirs too large to read into context. Loads `path` as a Python " +
		"variable `ctx` (str for a file; dict{relpath: text} for a dir), then runs your `code` " +
		"against it. print() ONLY the relevant slice — that is all that enters the conversation. " +
		"Prefer this over grep+read loops on big inputs; token cost stays flat regardless of size.",
	args: {
		path: z
			.string()
			.describe("Absolute or ~ path to a file or directory to load as ctx"),
		code: z
			.string()
			.describe(
				"Python code; `ctx` holds the content; print() the slice you need",
			),
	},
	async execute(args: { path: string; code: string }) {
		const prelude = [
			"import os, re, sys, io, json",
			"p = os.path.expanduser(sys.argv[1])", // путь через argv, не вклеиваем в исходник
			"def _load(p):",
			"    if os.path.isdir(p):",
			"        d = {}",
			"        for root, _, files in os.walk(p):",
			"            for f in files:",
			"                fp = os.path.join(root, f)",
			"                try: d[os.path.relpath(fp, p)] = open(fp, encoding='utf-8', errors='replace').read()",
			"                except Exception: pass",
			"        return d",
			"    return open(p, encoding='utf-8', errors='replace').read()",
			"ctx = _load(p)",
		].join("\n");
		const script = prelude + "\n" + args.code;
		// Bun.$ экранирует интерполяции как отдельные аргументы (нет shell-инъекции).
		// `code` — произвольный Python by design: локально, с правами bash-тула (permission.bash=ask прикрывает).
		const out = await Bun.$`python3 -c ${script} ${args.path}`
			.text()
			.catch((e: unknown) => String(e));
		return out.length > 100_000
			? out.slice(0, 100_000) + "\n...[truncated]"
			: out;
	},
};
