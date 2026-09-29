# Global Rules

## Tools

- ALWAYS use OpenCode's `grep` and `glob` tools for file searches; they are backed by `rg`.
- In shell commands, ALWAYS use `rg` instead of `grep` and `fd` instead of `find`.

## Git Workflow

- Before creating a branch or commit, ALWAYS inspect the user's style with `git log --author="$(git config user.name)" --oneline --branches --remotes -n 15` and follow it.
- ONLY ask for a task or ticket number when that history establishes it as the user's convention.
- NEVER run `git pull` or `git push`. Ask the user to sync when remote state is required.
