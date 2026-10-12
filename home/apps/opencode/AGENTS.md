# Global Rules

## Discussion

- For multi-turn planning or discussion, load the `discussion-map` skill.

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
- Use `rlm` to aggregate content across files or extract evidence from a large
  source without copying the bulk into the conversation. Load the `rlm` skill
  when this workflow is needed. Do not invoke RLM merely because a directory,
  an unknown-size file, or more than two files are involved.
- If exploration repeats without new evidence or a narrower scope, change the
  approach: test a specific hypothesis or use a focused RLM query. Reuse prior
  findings instead of repeatedly retrieving the same material.
- Keep large source files and logs out of the conversation. When a tool saves a
  large result as an artifact, extract only the relevant evidence from that
  artifact. Select the narrowest useful source, never a home directory just to
  discover a filename.
- Check RLM's load report. A partial result cannot establish absence in the
  source; inspect relevant skipped files separately before making that claim.
- Use `rlm_subquery` only when semantic analysis benefits from a separate model
  and delegation is permitted. Pass a source path and a focused question, not
  copied source text. Use direct extraction for mechanical searches or counts.

## Git Workflow

- Before creating a branch or commit, ALWAYS inspect the user's style with `git log --author="$(git config user.name)" --oneline --branches --remotes -n 15` and follow it.
- ONLY ask for a task or ticket number when that history establishes it as the user's convention.
- NEVER run Git operations against a remote, including `git push`, `git pull`, and `git fetch`. The user performs all remote operations, including those that require authentication. Ask the user to sync when remote state is required.

## User Actions

- When the user needs to take an action after agent work, ALWAYS provide a clear, ordered plan for verification, deployment, diagnosis, or other follow-up. Aim for no more than 10 steps.
