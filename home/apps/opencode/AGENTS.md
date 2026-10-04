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

## Git Workflow

- Before creating a branch or commit, ALWAYS inspect the user's style with `git log --author="$(git config user.name)" --oneline --branches --remotes -n 15` and follow it.
- ONLY ask for a task or ticket number when that history establishes it as the user's convention.
- NEVER run Git operations against a remote, including `git push`, `git pull`, and `git fetch`. The user performs all remote operations, including those that require authentication. Ask the user to sync when remote state is required.

## User Actions

- When the user needs to take an action after agent work, ALWAYS provide a clear, ordered plan for verification, deployment, diagnosis, or other follow-up. Aim for no more than 10 steps.
