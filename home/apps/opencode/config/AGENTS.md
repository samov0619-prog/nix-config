# Global Rules

## Tools

- ALWAYS use OpenCode's `grep` and `glob` tools for file searches; they are backed by `rg`.
- In shell commands, ALWAYS use `rg` instead of `grep` and `fd` instead of `find`.

## Shell

- The user's interactive shell is Fish. When providing commands for the user to run,
  write Fish syntax: use `set name value` for variables and `(command)` for command
  substitution. Do not use POSIX `name=value`, `$()` or Bash-only syntax unless the
  command is explicitly prefixed with `bash -c`.

## Source Exploration

- Use `glob` for filename discovery, `grep` for targeted content searches, and
  `read` for small, selected passages. Continue direct lookups while they narrow
  the search or verify a concrete finding; there is no tool-call quota.
- If exploration repeats without new evidence or a narrower scope, change the
  approach: test a specific hypothesis or narrow the source and query. Reuse prior
  findings instead of repeatedly retrieving the same material.
- Keep large source files and logs out of the conversation. When a tool saves a
  large result as an artifact, extract only the relevant evidence from that
  artifact. Select the narrowest useful source, never a home directory just to
  discover a filename.
- Use native tool-output artifacts with targeted `grep` and `read`; do not reload
  a large result just because a preview was truncated. A partial search cannot
  establish absence; state coverage gaps and inspect missing sources when needed.
- Use tools for mechanical extraction, counting and transformation, without an
  extra model call. Delegate bounded fact collection to `explore`, substantive
  source synthesis to `research`, and independent correctness checks to `review`
  only when separate analysis is justified and delegation is permitted. Give the
  child a source scope, question and expected evidence; avoid duplicating its work.
- Load a skill only when its advertised description matches the current task or
  the user explicitly requests it. Reuse instructions already in the current
  context unless the skill has changed; do not reload it for every follow-up.
  Keep skill permission restrictions intact; a subagent is not a permission bypass.

## Formatting

- Use the project's declared formatter, configuration and version through its CLI,
  only on changed files. Do not replace tooling with model-generated reformatting.
- If no formatter is declared for that file type, preserve the existing layout;
  do not choose a global fallback. Keep lint fixes separate from formatting.

## Verification and Resources

- Leave pre-commit and pre-push verification builds to the user. Requests to
  review, verify, or commit if everything looks good do not authorize builds.
- Obtain explicit approval for the command and scope before running
  resource-intensive checks. Announce the approved work before starting it;
  never launch it silently in the background or in parallel.
- Small local unit tests, lint, and static checks that do not build the project
  may run without separate approval. Ask first when the resource cost is unknown.
- Reuse verification already performed by the user. If later changes invalidate
  its coverage, explain the gap and provide a manual verification command instead
  of starting another build.
- Clearly distinguish completed checks from checks not run. Never describe
  unbuilt or untested changes as fully verified.

## Git Workflow

- Before creating a branch or commit, ALWAYS inspect the user's style with `git log --author="$(git config user.name)" --oneline --branches --remotes -n 15` and follow it.
- ONLY ask for a task or ticket number when that history establishes it as the user's convention.
- NEVER run Git operations against a remote, including `git push`, `git pull`, and `git fetch`. The user performs all remote operations, including those that require authentication. Ask the user to sync when remote state is required.

## User Actions

- When the user needs to take an action after agent work, ALWAYS provide a clear, ordered plan for verification, deployment, diagnosis, or other follow-up. Aim for no more than 10 steps.
