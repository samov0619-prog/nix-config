---
name: git-regression-rollback
description: Git rollback, regression, reset, or reverting recent commits. Use to preserve rolled-back work in a stash until the regression is fixed and verified.
---

# Git Regression Rollback

Use this workflow when investigating a regression by removing recent commits.

1. Inspect status and the target commits. ALWAYS stash unrelated work first: `git stash push --include-untracked -m "opencode-rollback: worktree before <reason>"`.
2. Move to the known-good commit with `git reset --soft <good-revision>`, then stash the removed candidate: `git stash push -m "opencode-rollback: candidate <commits> for <reason>"`. This preserves the candidate without leaving it on the branch.
3. Identify the cause and restore the intended behavior. Review the candidate stash before reuse with `git stash show --patch <stash>`.
4. If it is still useful, apply it with `git stash apply --index <stash>`, make the required corrections, and run relevant tests. Otherwise implement the fix independently.
5. Keep the candidate stash until the replacement has passed review and tests. Then `git stash drop <stash>`. Restore or retain the separate pre-existing-work stash as appropriate.

DO NOT drop a candidate stash merely because it conflicts. Drop it only after the cause is certain and the working replacement is verified. DO NOT use this workflow for a user-requested permanent revert; preserve history with `git revert` instead.
