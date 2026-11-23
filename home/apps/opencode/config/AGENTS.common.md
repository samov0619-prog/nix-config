# Shared Engineering Rules

## Engineering Choices — High Priority

- Apply this rule before proposing an approach, designing a solution or making
  changes. Among solutions that meet the requirements, prefer the supported,
  conventional approach over a custom one even when the custom implementation
  seems quicker or more familiar. Any departure requires the justification below;
  do not wait for the user to request this comparison.
- Default to built-in, officially supported capabilities and documented public APIs
  before adding custom code, wrappers, hooks, patches or dependencies. Choose the
  simplest maintained solution that meets the actual requirements.
- Follow established project conventions and current upstream recommendations for
  the version in use. Treat best practices as contextual guidance, not a reason
  to overengineer, expand scope or rewrite working code; do not copy a known-bad
  pattern just because it already exists.
- Before taking a custom or unsupported path, identify the concrete requirement,
  bug or compatibility constraint that the supported approach cannot satisfy.
  Explain the evidence and maintenance trade-off; ask before introducing a
  significant long-term maintenance burden. Do not invent missing API capabilities
  or treat an undocumented workaround as supported.
- Prefer these defaults without requiring reminders from the user. Explicit task
  requirements and verified project constraints take precedence; preserve accepted
  fixes unless their removal conditions are met.

## Architecture Principles

- Prefer the simplest design that meets current requirements. Do not add speculative
  abstractions, layers or dependencies for hypothetical future needs.
- Give modules clear responsibilities: keep closely related behavior together and
  minimize coupling between independent concerns.
- Make dependencies explicit. Avoid dependency cycles, hidden shared mutable state
  and implicit cross-module coordination.
- Define clear interfaces and contracts, preserve their invariants, and handle
  failures predictably rather than hiding them.
- Keep core logic independently testable; separate external I/O and side effects
  where useful, without forcing extra layers around every small operation.
- Share code when it represents the same knowledge or rule. Do not merge unrelated
  behavior merely because its implementation looks similar.
- Respect the existing architecture and keep changes proportional to the task.
  A local request does not authorize redesign; these principles mandate no named
  methodology, folder structure or module size.

## Tools

- ALWAYS use OpenCode's `grep` and `glob` tools for file searches; they are backed by `rg`.
- In shell commands, ALWAYS use `rg` instead of `grep` and `fd` instead of `find`.

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
  a large result just because a preview was truncated. Account for pagination,
  collapsed sections and truncated output when gathering evidence. A partial
  search or unread source cannot establish absence; inspect decision-relevant
  gaps where permitted and possible, and disclose material access or coverage limits.
- Before relying on a source for a consequential claim or decision, read the
  relevant reasoning and context through to the outcome, including material
  comments, updates and caveats. Do not treat a title, opening description,
  excerpt, summary or status label as sufficient evidence by itself. Follow
  references that could materially change the conclusion, including solutions
  and alternatives; keep the investigation scoped to the task rather than
  traversing unrelated links.
- Check that evidence applies to the target version, environment and relevant
  revision. For capability claims, distinguish proposals, unmerged patches,
  merged changes and released features; verify actual availability and support
  in the target setup rather than inferring them from upstream status alone.
- Use tools for mechanical extraction, counting and transformation, without an
  extra model call. Delegate only when separate analysis is justified and
  delegation is permitted, choosing an available role appropriate to the task.
  Give the child a source scope, question and expected evidence; avoid duplicating
  its work.
- Load a skill only when its advertised description matches the current task or
  the user explicitly requests it. Reuse instructions already in the current
  context unless the skill has changed; do not reload it for every follow-up.
  Keep skill permission restrictions intact; a subagent is not a permission bypass.

## Working Files and Artifacts

- Keep durable source, tests and documentation in the project when in scope.
  Use an agreed persistent location for external artifacts needed for recovery or
  handoff: `/tmp` retention is not guaranteed.
- Minimize sensitive diagnostic data and restrict access to private directories
  and files. Do not include secrets in reports or transferable packages.
- Clean up only known disposable files created for the current task, subject to
  normal permissions. Never broadly clean old/other tasks' files or delete the
  only copy of a needed result.
- Report useful retained artifacts with their paths and purpose, not every
  scratch file. These rules do not authorize writes in read-only tasks or Plan.

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
- Define expected behavior using agreed requirements, documented contracts,
  known-good examples, or justified invariants—not solely the current
  implementation's output.
- Add fixtures and reproducible scenarios where they provide useful coverage.
  Reuse suitable test infrastructure and extend it when needed.
- Exercise actual implementation paths. Distinguish fixture/mock coverage from
  evidence about real integration, user interfaces, and target environments.
- Do not weaken checks or change expected results merely to make tests pass.
  Justify changed expectations through changed requirements or evidence that
  the previous expectation was incorrect.

## Code Comments

- Follow the project's documentation conventions, including required API docs
  and machine-readable annotations.
- Avoid comments that merely restate nearby code. Add comments when they clarify
  non-obvious intent, invariants, trade-offs, external constraints or pitfalls.
- Keep comments affected by your changes accurate. Update or remove explanations
  made stale by those changes; preserve unrelated meaningful comments.
- Do not expand the task into comment cleanup or unrelated refactoring. Preserve
  required legal notices and tool directives.

## User Actions

- When the user needs to take an action after agent work, ALWAYS provide a clear, ordered plan for verification, deployment, diagnosis, or other follow-up. Aim for no more than 10 steps.
