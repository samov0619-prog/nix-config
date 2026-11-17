# Personal Rules

These personal rules take precedence over shared rules where they conflict.

## Goals and Approach

- Before materially increasing complexity or scope, separate the user's goal from
  the current implementation idea. Check whether an existing capability, a more
  direct approach or a smaller change already meets the actual requirements.
- Surface a substantially simpler viable alternative before elaborating the more
  complex solution: explain its coverage, limitations and unverified assumptions.
  Scale this check to the work and cost of error; do not turn each routine local
  decision into research or a request for confirmation.
- Simplicity is a preference, not a veto on the user's ideas. Learning,
  experimentation, convenience, control and independence can be explicit goals;
  do not optimize them away or assume that the fewest components is always best.
- When alternatives materially change the outcome, scope or maintenance burden,
  briefly show the choice and recommend an approach. Clarify only a consequential
  unresolved choice; otherwise proceed with a justified approach within the request.
- Once the user makes an informed choice, help implement it without repeating
  settled objections unless new material facts appear. This does not waive project
  constraints, permissions or the need for operational approval.

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
  `~/.config/opencode-local/review-system.md`. Existing team command/agent symlinks
  are discovery entrypoints only, not ownership of personal policy. The shared
  `AGENTS.md` selects required task/specification sources independently of these
  workflows; do not move personal routing or analysis criteria into that file.
- Review authorizes no fixes, builds, installation or commits and does not relax
  permissions or Plan restrictions. Discussion, quotations, future/negated requests
  and ordinary development/self-checks do not launch a review workflow. A command
  owns its reviewer invocation: do not launch a duplicate or delegate recursively.

## Search Tools

- ALWAYS use OpenCode's `grep` and `glob` tools for file searches.
- In shell commands, ALWAYS use `rg` instead of `grep` and `fd` instead of `find`.

## Code Comments

- Follow the project's documentation conventions, including required API docs
  and machine-readable annotations.
- Avoid comments that merely restate nearby code. Add comments when they clarify
  non-obvious intent, invariants, trade-offs, external constraints or pitfalls.
- Keep comments affected by your changes accurate. Update or remove explanations
  made stale by those changes; preserve unrelated meaningful comments.
- Do not expand the task into comment cleanup or unrelated refactoring. Preserve
  required legal notices and tool directives.

## Shell

- My interactive shell is Fish. Write user commands in Fish: `set name value`
  and `(command)`. Use POSIX/Bash syntax only when explicitly prefixed with `bash -c`.

## Git Approvals

- Create Git commits ONLY after a separate explicit user request to commit the
  current task changes. Review, completion and checkpoint requests do not authorize
  a commit. Without that request, leave changes uncommitted and report their state.
- Obtain explicit approval before rewriting history, integrating commits, changing
  the checkout, discarding files, mutating saved stashes or deleting/force-updating
  refs and worktrees. A general fix/review request does not authorize these actions.
- Keep approval-sensitive Git mutations at Ask; do not request or save Always
  approval for them. Use explicit subcommands and separate flags, not aliases,
  wrappers or combined options to bypass approval. Inspection and comparisons do
  not need mutation approval.
