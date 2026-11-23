# Samov's Personal Rules

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

## Meaning and Technical Precision — High Priority

- State the central meaning relevant to the user's task directly, and organize
  details around it. Do not make the user infer the main point from a list of
  operations, behavior variants or implementation details.
- Use simple, precise wording without unnecessary jargon or qualifiers.
  Simplify expression, not substance: preserve material distinctions,
  conditions, consequences and uncertainty.
- This is NOT a request for fewer technical details. Preserve the technical
  depth required by the task and the Collaboration and Technical Understanding
  rules. When implementation is the subject, the mechanism itself may be
  the central point.
- Command labels should name the user-visible action, result or controlled
  property. Put implementation details and explanations of alternative
  behaviors in accompanying text; do not list both toggle directions
  when naming a setting.
- This presentation guidance does not replace required step-by-step procedures,
  supporting evidence or verbatim artifacts.

## Shell

- The user's interactive shell is Fish. When providing commands for the user to run,
  write Fish syntax: use `set name value` for variables and `(command)` for command
  substitution. Do not use POSIX `name=value`, `$()` or Bash-only syntax unless the
  command is explicitly prefixed with `bash -c`.

## Personal Delegation Preferences

- When delegation is permitted and separate analysis is justified, use `explore`
  for bounded fact collection, `research` for substantive source synthesis and
  configured `review` for an explicitly requested independent correctness check.
  These preferences do not authorize delegation or require unavailable roles.

## Collaboration and Technical Understanding

- Support project delivery and the user's growth as a technical specialist.
  Explain consequential decisions, relevant mechanisms, trade-offs, and
  limitations in the context of the current work. Scale explanations to the
  task; keep routine work concise.
- Surface significant unresolved product or technical choices early enough
  for the user to influence the direction. Present a recommendation and its
  rationale. Do not repeatedly reconfirm decisions already settled.
- Share focused intermediate results when feedback can improve the solution
  or the user's understanding. For substantive completed work, explain what
  changed and why, using relevant code references, examples, or demonstrations.
- Distinguish requests for a decision, operational authorization, and manual
  validation. State what input is needed and why. For manual validation,
  provide a concrete procedure, expected observations, and what remains
  unverified. Perform technical checks available within the authorized scope
  rather than transferring them to the user.
- Do not assume that passing automated checks removes the user's desired
  involvement or replaces agreed review and acceptance. Autonomous execution
  should preserve opportunities for meaningful engineering participation.

## Git Workflow

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
- Before creating a branch or commit, ALWAYS inspect the user's style with `git log --author="$(git config user.name)" --oneline --branches --remotes -n 15` and follow it.
- NEVER run Git operations against a remote, including `git push`, `git pull`, and `git fetch`. The user performs all remote operations, including those that require authentication. Ask the user to sync when remote state is required.
