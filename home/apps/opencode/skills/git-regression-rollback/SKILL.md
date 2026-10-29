---
name: git-regression-rollback
description: Use for a user-authorized temporary rollback of recent Git commits to investigate a regression, preserving the candidate work in a stash until verified. Not for read-only Git inspection, ordinary bug fixes, or permanent reverts.
---

# Git Regression Rollback

Use this workflow only when the user has authorized temporarily removing recent
commits to investigate a regression. A request to investigate or fix a bug does
not itself authorize moving a branch or stashing pre-existing changes. If the
rollback target or treatment of unrelated work is unclear, ask before changing
Git state.

1. Inspect status and the target commits. Obtain approval before moving unrelated changes into a stash. Once approved, preserve them separately before the rollback: `git stash push --include-untracked -m "opencode-rollback: worktree before <reason>"`.
2. Move to the known-good commit with `git reset --soft <good-revision>`, then stash the removed candidate: `git stash push -m "opencode-rollback: candidate <commits> for <reason>"`. This preserves the candidate without leaving it on the branch.
3. Identify the cause and restore the intended behavior. Review the candidate stash before reuse with `git stash show --patch <stash>`.
4. If it is still useful, apply it with `git stash apply --index <stash>`, make the required corrections, and run relevant tests. Otherwise implement the fix independently.
5. Keep the candidate stash until the replacement has passed review and tests. Then `git stash drop <stash>`. Restore or retain the separate pre-existing-work stash as appropriate.

DO NOT drop a candidate stash merely because it conflicts. Drop it only after the cause is certain and the working replacement is verified. DO NOT use this workflow for a user-requested permanent revert; preserve history with `git revert` instead.
