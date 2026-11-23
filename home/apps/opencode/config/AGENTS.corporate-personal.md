# Personal Rules

These personal rules take precedence over shared rules where they conflict.

## Corporate Task Convention

- For Samov's new task branches and commits, use the confirmed current XTracker
  task key `FBDC-<number>` wherever the discovered style places the task key.
  Inspect personal Git history as required, but use it only for the remaining
  format: branch type, separators, wording and commit structure. Older `KT-...`
  entries do not override the current `FBDC-...` convention.
- If the current task key is missing, ask before creating a branch or commit.
  Do not reuse a task key from history, invent a number or infer a tracker migration
  from matching digits. An explicitly selected existing branch or another person's
  style is not permission to rename it or rewrite history. This convention grants
  no approval to create branches, commit or perform remote Git operations.

## Review Workflows

- These are personal workflows, not requirements for the shared team setup.
  Their analysis, delegated wrapper, command templates and reviewer source live
  in `~/.config/opencode-local/`. Read policy files directly from that directory;
  do not require policy-file links in `~/.config/opencode/`.
- Ordinary code review stays in the current conversation with its existing
  context, agent and model. Do not delegate, fork or switch roles merely because
  review is requested. First read `~/.config/opencode-local/review-analysis.md`;
  reuse it only if already loaded and unchanged. If unavailable, report the
  limitation rather than inventing a policy.
- For an explicit separate-review request, including `/delegated-review`, follow
  an applicable project override or otherwise read
  `~/.config/opencode-local/commands/delegated-review.md`. Resolve the requirements
  basis before launching one fresh configured `review` child. Preserve template
  scope defaults, fingerprints and recovery; do not override the model, adopt an
  old child for a new task or substitute `general` when `review` is unavailable.
- For an explicit passive audit of recorded Chrome-MCP claims, use an applicable
  project override or otherwise read
  `~/.config/opencode-local/commands/delegated-review-chrome.md`. Do not launch an
  ordinary reviewer first. Keep its historical evidence boundary, export/privacy
  restrictions and browser prohibition; no new task/Wiki retrieval or live retest.
- The reviewer reads `~/.config/opencode-local/review-analysis.md` and
  `~/.config/opencode-local/review-system.md`. Personal commands and agents are
  registered explicitly in the personal JSONC; no team discovery links are required. The shared
  `AGENTS.md` selects required task/specification sources independently of these
  workflows; do not move personal routing or analysis criteria into that file.
- Review authorizes no fixes, builds, installation or commits and does not relax
  permissions or Plan restrictions. Discussion, quotations, future/negated requests
  and ordinary development/self-checks do not launch a review workflow. A command
  owns its reviewer invocation: do not launch a duplicate or delegate recursively.
