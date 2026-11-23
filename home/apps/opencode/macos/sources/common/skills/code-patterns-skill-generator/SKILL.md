---
name: code-patterns-skill-generator
description: Creating or updating project skills about code conventions, recipes for adding entities, or code review checklists. Use when the user explicitly asks for such a skill, not for skills unrelated to the project's code; it researches the code and writes `.opencode/skills/<name>/SKILL.md`.
---

# Code Patterns Skill Generator

Use this workflow when creating or updating a skill that describes how code is written in the current project.

## Skill Format

Every skill you write MUST match the format of this skill: the rules and the skeleton below.

- Frontmatter: use `name` and a clear `description`. V2 also accepts `metadata`, `license`, and `compatibility`; add them only for a concrete need. Use `metadata.opencode/autoinvoke: false` for an explicitly manual skill.
- The directory or file path determines the skill ID; `name` is only its display label. For portable IDs, use lowercase letters, digits, and single hyphens, up to 64 characters, aligned with the folder name. This is a convention, not a V2 discovery requirement. Start a recipe with a verb: `add-page`, `add-api-endpoint`.
- `description`: one line, up to 1024 characters. The first sentence lists trigger topics and keywords, including class, function, and component names from the code. The second sentence starts with `Use when` or `Use to` and says what the skill defines.
- `# Title` in Title Case, then one sentence: `Use this workflow when ...` for a recipe, `Use these rules when ...` for a convention, `Use this checklist when ...` for a checklist.
- The most important rules come first.
- Body in English. Short sentences, one rule per item. Commands, paths, and names in inline code. Emphasis in caps: `ALWAYS`, `NEVER`, `DO NOT`.
- Add `##` sections only when the skill has several parts. Keep it under ~400 lines; move long catalogs and large tables to `references/<topic>.md`.
- End with a paragraph of prohibitions and the limits of the skill.

```markdown
---
name: <skill-name>
description: <Trigger topics and keywords>. Use when <tasks>; <what the skill defines>.
---

# <Skill Title>

Use this workflow when <task>.

1. Create `<path>` following `<reference file>`.
2. Register it in `<path>`.
3. Run `<check command>`.

DO NOT <antipattern>. DO NOT use this workflow for <neighbor case>; use `<other-skill>` instead.
```

Choose the body by skill type:

| Type | When | Body |
| --- | --- | --- |
| Recipe | "how to add X": page, endpoint, entity | numbered steps with real files |
| Convention | how to write a kind of code | `## Reference Files`, `## Rules`, `## Avoid`, `## Exceptions`, `## Checks` |
| Checklist | how to review code on a topic | numbered yes/no questions and the fix for "no" |

If the topic can be phrased as "how to add X", ALWAYS write a recipe: the model follows steps more precisely than rules.

## Create

1. Clarify the topic. One topic, one skill. If it is unclear, ask; DO NOT guess.
2. Read `AGENTS.md`; its rules also apply to examples in the skill. Read `README.md`, dependency manifests (`package.json`, `pyproject.toml`, `go.mod`, ...), and linter, formatter, and alias configs.
3. Read the frontmatter of every `.opencode/skills/*/SKILL.md`. If the topic is already covered, switch to Update. If the topic needs only 2–3 rules, add a section to a fitting existing skill instead.
4. Search code read-only with OpenCode's `grep` and discover paths with `glob`. If those tools are unavailable and shell is permitted, use `rg` and `fd`, not `grep` or `find`. Search first, then read the relevant context through its outcome.
5. If several approaches exist, count each within a declared scope, for example `rg -l '<approach>' <src> | wc -l`. Frequency is evidence of a convention, not correctness: check project requirements, supported APIs, version applicability, and known exceptions before classifying an approach as current or legacy.
6. Pick 1–3 reference files: the cleanest typical examples. Check with `grep` that their naming, exports, and wrappers match the majority. If a reference file is in the minority, show the counts and ask which style is correct.
7. For every `ALWAYS` or `NEVER` rule, search for violations. Example: rule "only the wrapper" → search for direct library calls. List ALL violations with paths; DO NOT filter them yourself. Ask for each: a valid exception (→ `## Exceptions` with a sample file) or legacy (→ `## Avoid`).
8. Find the check commands (typecheck, lint, test) in `package.json` scripts, `Makefile`, or similar.
9. Show the draft: `name`, `description`, reference files, rules, avoid list, exceptions, counts per approach, and the full list of violations with paths. Ask which approach is correct and which is legacy. Stop and wait for the answer.
10. Write `.opencode/skills/<name>/SKILL.md`, then run the self-check below and fix every failure.
11. Report the created files and give two test phrases without the skill name: one that MUST load the skill and one that MUST NOT. V2 watches configuration and skills; use `/reload` if a forced refresh is needed, not a service restart for an ordinary file change.

## Update

1. Read the skill fully and find what changed in the code: new files and wrappers, removed or moved paths.
2. Show the list of edits. Stop and wait for confirmation.
3. Change only the affected parts; keep the structure. If the old skill does not match the format above, propose converting it.
4. If the skill exceeds ~400 lines, propose moving catalogs to `references/`.
5. Run the self-check.

## Writing Rules

- Take rules from the project's existing code and configs, not from general best practices.
- Write for the team's main model (`model` in `opencode.jsonc`); a weak model needs short, unambiguous rules.
- ALWAYS name the reference files and the real check commands (typecheck, lint, test).
- Write `ALWAYS`, `NEVER`, and "if X → do Y". DO NOT write "usually" or "preferably".
- Use only real paths, names, and APIs. If it is not found in the code, DO NOT write it.
- Prefer decision tables over paragraphs, wrong/right pairs over prose, and "repeat the structure of `<file>`" over long descriptions.
- Take examples from real files, up to 20–30 lines, with the path from the project root. If the source code violates `AGENTS.md`, fix the example.
- Imports in an example: all or none. With none, add a line above: `Imports as in <file>.` Partial imports are forbidden.
- Describe only project specifics, not general language knowledge.
- Put everything the model needs in SKILL.md; `references/` holds only catalogs.
- Refer to a neighbor skill by name instead of copying its rules.
- If two approaches exist, describe the one the user chose and put the other under `Avoid` as legacy.
- DO NOT write a generic `description` such as "development rules"; the skill cannot be selected by it.
- DO NOT put autofix commands (`--fix`, `--write`) in checks if `AGENTS.md` forbids them.
- If the skill loads too often, narrow the first sentence of `description` and remove generic keywords. If it never loads, add synonyms and names from the code.

## Self-Check

1. Does the file match the format of this skill: frontmatter, title, intro sentence for its type, final prohibitions?
2. Is the path-derived ID unique, portable, and consistent with references? Is the display name intentional and the description concise and specific? The 64/1024-character limits are authoring conventions, not runtime validation.
3. Does every path and name in the skill exist? Check with `glob`/`grep` or permitted `fd`/`rg`, not from memory.
4. Is every "example of X is in Y" and "for X see Y" verified in the actual source: does Y really contain X?
5. Do the examples follow `AGENTS.md`, even where the source code does not? Are imports all or none?
6. Is every found violation listed under `Exceptions` or `Avoid`?
7. Do the rules agree with the skill's own examples? Reread each rule against each example.
8. Does the skill name its reference files and real check commands?
9. Did the user confirm the draft? Are project code and Git untouched?

NEVER invent paths, names, or APIs. NEVER write files before the user confirms the draft. DO NOT change project code or run Git operations; change only `.opencode/skills/`. DO NOT use this workflow for skills that are not about the project's code; say so to the user.
