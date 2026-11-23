# Global Rules

## Tool Output Selection

- Choose the most concise representation that preserves the evidence needed
  for the task. Do not assume that readable output is lossless or that raw
  output is more useful.
- For claims that depend on exact code, configuration values, identifiers,
  error text or write preconditions, inspect the relevant source or exact
  structured fields rather than relying on a paraphrase.
- Use summaries and previews to navigate. If conversion or truncation may omit
  a decision-relevant detail, verify it with a targeted lookup; do not load
  the entire raw artifact when a small excerpt or field selection is enough.

## Requirements Sources

- For code review under this corporate policy, establish the external task
  requirements/specification (TZ) before assessing task conformance. This rule
  comes from this `AGENTS.md`, not from the existence of an MR or a work-like
  hostname/branch. Use a supplied task/document first; otherwise discover it from
  the selected MR's description, title and source branch, or from the selected
  local branch/range when that is the review target. Never substitute the current
  checkout's task for an unrelated MR.
- Use XTracker for current corporate tasks. Use available, permitted read-only
  issue-tracker/Wiki MCP tools to read the task and its linked requirements.
  The configuration may expose `MCP-XTRACKER`, `MCP-WIKI` and `MCP-GITLAB`;
  discover actual tools and respect
  disabled/unavailable servers rather than guessing methods or enabling them.
  A task's own substantive acceptance criteria may be the requirements; a separate
  Wiki page is not mandatory when no additional specification is referenced.
- Verify the source's task relationship and relevant product/platform/release and
  revision from links, metadata and contents. A number in a branch, matching
  digits with another prefix or a similar document title is a lead, not proof.
  Read applicable acceptance criteria and API/UI contracts, not just search previews.
- If direct discovery does not identify an unambiguous applicable source, ask for
  the task/link or the specific ambiguity before claiming task conformance.
  If a source is evident and accessible, use it without asking the user to repeat
  it. An access failure is not proof that no TZ exists. Do not silently substitute
  code-inferred intent for required external requirements.
- A task without external requirements or an explicitly technical-only review is
  possible: use an explicit user agreement for this task, record its scope and
  alternate requirements basis, and do not ask again while it still applies.
  Missing required sources mean incomplete requirements coverage, not a code bug
  or permission to claim task conformance. Keep source IDs/revisions/sections and
  agreed clarifications with the assessment; check material requirements even
  when code looks technically sound.

## Git Workflow

These corporate rules take precedence over general Git workflow defaults.

- Create Git commits ONLY after a separate explicit user request to commit the
  current task changes. Review, completion and checkpoint requests do not authorize
  a commit. Without that request, leave changes uncommitted and report their state.
- Keep `git commit` permission at Ask; do not request or save Always approval for it.
- ALWAYS match my personal branch and commit style.
- Before creating a branch or commit, discover it via this command:
  `git log --author="$(git config user.name)" --oneline --branches --remotes -n 15`
- FOLLOW ONLY these patterns, UNLESS explicitly told to work on someone else's branch or style.
- ALWAYS ASK for the task/ticket number if missing in the context, BEFORE creating a branch/commit.
- The ticket identifier must come ONLY from the user's discovered git history or from
  what the user explicitly provides. Otherwise, ASK.
- NEVER ATTEMPT remote Git operations, including `git push`, `git pull`, and `git fetch`.
  All network syncs must be done by me manually, including operations requiring authentication.
- IF remote sync is critical AND I haven't mentioned updating it (e.g. "synced"), ALWAYS ASK me to sync.

## Task Log

- Create or update a task log ONLY when the user explicitly asks («создай лог», «обнови лог»).
  Then load the `task-summary-log` skill: one short summary per task in `./promptLogs/`
  of the project the log is for.
- For a requested log, ask for the XTracker task key if missing in the context.
  The key is optional: continue without it if the user declines or has none.
- ALWAYS write the log in English.
- Get the date only with `date -u +%Y-%m-%d`. NEVER write secrets into the log.
