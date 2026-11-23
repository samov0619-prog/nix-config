---
name: task-summary-log
description: Task summary log, `./promptLogs/`, XTracker task, "создай лог", "обнови лог", summary of key changes and decisions. Use only when the user explicitly asks to create or update a task log; it writes one short summary file per task in `./promptLogs/` of the project being worked on.
---

# Task Summary Log

Use this workflow ONLY when the user explicitly asks to create or update a task log («создай лог», «обнови лог»). NEVER create or update a log on your own initiative.

ALWAYS write generated log prose in English: headings, items, and the task title, even when the user writes in Russian. Preserve supplied artifacts such as file paths, code names, commands and error messages verbatim; do not translate them unless explicitly requested.

1. Find the project the log is for: the project the session works in. Use `./promptLogs/` in ITS root. NEVER write the log into another project or into this config repository.
2. Ask for the XTracker task key if it is not in the request or context. The key is optional: if the user declines or has none, continue without it. Use the confirmed full key, such as `FBDC-123456`, not bare digits. NEVER guess it, reuse it from Git history or take it from a branch name without confirmation.
3. Look for an existing log in `./promptLogs/`: by full key `<task-key>_*.md` and by a matching short name. Also check relevant older logs with numeric filenames or previous tracker keys. Matching digits alone do not prove that two tracker tasks are the same; if identity is unclear, ASK before writing. Do not create a duplicate merely because the identifier format changed.
4. Log exists → tell the user, read it, and update it in place. Preserve its filename unless the user explicitly requests a rename. DO NOT create a second file for the same task.
5. No log → create `<task-key>_<short-name>.md`, or `YYYY-MM-DD_<short-name>.md` without a key. Short name in latin kebab-case: `FBDC-123456_add-api-endpoint.md`, `2026-10-13_add-api-endpoint.md`. Create `./promptLogs/` if missing.
6. Get the date with `date -u +%Y-%m-%d`. NEVER guess it.
7. Fill the template below in English. Before saving, check generated prose for unintended non-English text; preserve supplied artifacts.
8. Write only key nodes: what changed and why. One line per item. DO NOT list every command, file read, or prompt.
9. On update, merge: rewrite outdated items, remove resolved questions, keep one item per change. DO NOT append a history of sessions.
10. Keep the whole log under ~40 lines. Too long → merge minor items into one.
11. Build the summary from the current session. DO NOT run Git commands to collect changes unless the user allows it.

```markdown
# <task-key or "No ID">: <task title>

Updated: <YYYY-MM-DD>
Status: <In progress | Done | Paused>

## Goal

<1–2 sentences: what the task must achieve>

## Changes

- `<file or area>` — <what changed> — <why>

## Decisions

- <decision> — <why; rejected alternative, if it matters>

## Next

- <open question or next step; "none" if empty>
```

Example item in `Changes`: `src/api/user.ts` — added `GET /users/:id` endpoint — needed by the profile card.

NEVER write secrets into the log: tokens, passwords, keys, credentials → `[hidden]`; logs are committed to Git. NEVER mix several tasks in one file. Creating or updating a log does not authorize a Git commit.
