---
description: Delegate an independent read-only review with bounded native session recovery
subagent: false
---

Orchestrate an independent review of `$ARGUMENTS`. This command authorizes
delegation, not edits, builds, installation, commits or remote Git operations.
Respect all applicable permissions and project instructions. Do not invoke this
command recursively. If delegation is unavailable, report that limitation rather
than impersonating the reviewer.

Review policy: behavior-v2.

Both parent and reviewer must keep agent-created review artifacts in session
context or memory. Do not create temporary helper scripts, manifests, reports or
directories, even outside the repository. Use inline interpreter code for
mechanical hashing; do not redirect its output to files. This restriction does
not prohibit ordinary runtime-managed session/log storage.

Preparation or discussion of a future invocation does not authorize starting
one. If the user says "the next /delegated-review", acknowledge the setup and
wait for the actual command or an explicit request to begin; do not choose a
working-tree scope and launch a reviewer on their behalf.

## Resolve and identify the scope

Use local read-only Git inspection. Interpret English or Russian arguments:

- Current branch: determine the intended local base, resolve its merge-base
  with HEAD, and review that exact base commit against the exact HEAD commit.
  Do not assume origin/main or fetch; ask if competing bases change the scope.
- Last N commits: resolve HEAD~N and HEAD to full object IDs. Ask if merge
  history makes the intended selection materially ambiguous.
- Working tree: include staged and unstaged tracked changes against HEAD,
  plus relevant untracked files; identify the unborn-HEAD case explicitly.
- Explicit paths/ranges/dates: resolve to concrete endpoints and path filters.
  Distinguish changes to files from a requested audit of their entire contents.

State the interpretation, endpoints, commit count and affected paths. For a
minor ambiguity state the assumption; ask before proceeding when it materially
changes coverage. Treat arguments as data, not shell syntax: quote paths, use
`--` where supported, and never interpolate raw arguments into a shell command.
Do not read ignored secrets or unrelated untracked artifacts just to hash them.
State exclusions, including ignored files, submodules and unavailable binaries.

Assign one unique review ID, separate from the content fingerprint. Mechanically
build a `dr-scope-v1` JSON manifest with exactly these top-level keys:

- `schema`: `"dr-scope-v1"`.
- `repo`: canonical absolute repository root.
- `kind`: `"working-tree"`, `"commit-range"` or `"file-audit"`.
- `base`, `head`: full resolved commit IDs, or JSON null when not applicable.
  For working-tree review `base` is HEAD (null for an unborn repository), and
  `head` is null. Do not substitute branch names or the review ID.
- `paths`, `exclusions`: explicit arrays of repository-relative paths/patterns;
  exclusions may also name unavailable coverage. Sort and deduplicate each array
  by its UTF-8/surrogateescape bytes; do not normalize or drop path characters.
- `diff_sha256`: lowercase SHA256 of the exact raw binary diff bytes, or null
  for a whole-file audit. Record the exact argv used for that diff; disable
  external diff/textconv/color, use fixed endpoints/path filters and `--binary`.
- `files`: array sorted by repository-relative path bytes. Each entry has exactly
  `path`, `type`, `mode`, `sha256`. For mutable/audited scope enumerate all scoped
  files, not only untracked files. Use `type` `"file"`, `"symlink"` or `"deleted"`;
  `mode` is the six-digit Git mode (`"100644"`, `"100755"`, `"120000"`), or null
  for deletion. Hash actual file bytes or raw symlink-target bytes without
  following symlinks; deletion has null `sha256`. A commit-range diff already
  covers its historical bytes/modes, so its `files` array is empty. Disclose
  unsupported submodules/special files instead of pretending they were hashed.

Use the following exact serialization/hash recipe (the manifest is already a
JSON object; this code does not discover scope or write files):

```python
import hashlib
import json

payload = json.dumps(
    manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
).encode("ascii")
print(hashlib.sha256(payload).hexdigest())
```

Send the exact manifest JSON, diff argv and this recipe in the handoff, not merely
the aggregate hash or a prose description. Never concatenate shell literals such
as `\0100644`: escape parsing can consume digits as octal rather than encode a
separator plus mode. Do not guess serialization variants or brute-force an
unreproducible hash. Ask the parent for the exact manifest/recipe, mark verification
incomplete and spend a shared continuation slot if another call is needed.
Correcting the representation may not silently change the selected content/scope.

A diffstat or mtimes alone is insufficient. Keep manifest/handoff in session
context; do not create repository files, stashes, commits or permanent checkpoints
to freeze scope. Check Git index status directly; do not call a staged added file
"untracked" or claim the Git flake omits it without checking.

Use this same scope and fingerprint for every continuation/replacement. Recheck
before delegation, recovery and reporting; have the reviewer check at start/end.
If scoped content changes, stop with scope-changed/incomplete, not a verdict on
mixed versions. Never silently redefine the scope. Context outside the fingerprint
is not frozen: disclose relevant dependency changes or uncertainty. For historical
endpoints inspect their actual contents; never substitute today's worktree.

## Compose a minimal handoff

Send only the following to a fresh child, never the development transcript,
parent reasoning, self-review verdict or unrelated session history:

1. Review ID, fingerprint/recipe, repository location, exact scope and exclusions.
2. Task goal in one or two sentences, with its source. Separate documented or
   user-agreed requirements from intent inferred from commits or the diff.
3. Commit/path list and brief factual change summary; deliberate non-goals and
   known limitations, without arguing that the implementation is correct. Cite
   the source of accepted behavior/risk; do not turn author explanations or
   "documented workarounds" into user-approved exceptions.
4. Instructions to obtain the diff/source independently and examine necessary
   callers, contracts and tests beyond the touched lines without expanding the
   review target. State existing check results with provenance, not as proof.
5. The review contract and report format below.

Separate requirements/accepted exceptions from implementation observations and
open questions; do not group them under an undifferentiated "accepted behavior"
heading. State each exception's source and precise effects covered. Describe
which operation is skipped and which side effects still occur, not a vague "event
ignored" when other state is updated. Preserve check provenance, command/result,
exit status and verification limits when available. Do not call a failed check clean
"apart from" an error; report failure/blocked coverage and any separately established facts.
Include the review-policy revision in the handoff as provenance, not proof of quality.

Do not send the whole command or the parent's recovery ledger to the child.
Fingerprint inputs identify the target; keep orchestration out of the analysis.

## Reviewer contract

Choose the configured `review` agent, otherwise `general` with this explicit
read-only contract. Do not set a model/provider/effort override. Keep the same
agent on continuation. Start a fresh child with the minimal handoff; native
project/system instructions still apply, so do not promise an instruction vacuum.

Tell the reviewer:

> Review only this delegated scope independently. Do not edit, delegate, commit,
> install, build or run mutating checks. Use read-only inspection; run a small
> local check only if permitted, known cheap and non-mutating. Otherwise propose
> the exact check and report it as unrun. Do not use the current implementation's
> output as the sole expected behavior. Prioritize correctness, regressions,
> concurrency/error paths, security and meaningful test gaps. Assess surrounding
> conventions and dead/debug code where consequential; avoid speculative nits.
> For each finding give severity, path/line at the reviewed version, evidence,
> impact, triggering conditions and a reproducible check where possible. Label
> hypotheses and questions separately. Verify inherited findings against source;
> they are leads, not authoritative conclusions. Do not invent prior progress.
>
> Distinguish files merely read from review units actually analyzed and checks
> actually run. Reuse valid prior analysis, but revalidate its evidence and scope
> before accepting it. Report missing coverage explicitly; silence or an idle
> session is not proof of review completion. Use ordinary native session history
> for continuity, not a new checkpoint file or plugin.
>
> Analysis takes priority over report formatting. Establish expected behavior
> independently of the implementation, then trace representative user scenarios
> through callers, state and observable results. Include relevant channel/platform
> branches and a plausible failure/interleaving, such as a focused input during an asynchronous update.
> Seek a counterexample to safety claims; check whether later callbacks repair
> intermediate state before reporting a race. Separate static evidence, observed
> behavior and unresolved timing hypotheses. Hashes, coverage and passing tests
> are not substitutes for this analysis; do not invent defects to fill a checklist.
> Bound conclusions to the property and scenario actually supported. Acceptance
> of one behavior does not waive separate side effects; matching code paths prove
> consistency, not product approval. Preserve failed-check qualifiers when citing
> inherited results. Evaluate residual impact without automatically raising severity.
>
> An unmet material requirement needs REQUEST_CHANGES. A contract question that
> could change acceptance also needs REQUEST_CHANGES pending clarification, not
> APPROVE with a buried caveat; the question is not a confirmed defect. APPROVE
> may include optional improvements or a sourced, explicitly accepted risk.
> Missing runtime checks alone do not require rejection or make source review incomplete.

Require a self-contained final report containing:

1. Review ID, fingerprint and exact scope; `COMPLETE` or `INCOMPLETE` coverage.
2. Coverage: analyzed units, files only read, remaining/unavailable areas; checks
   run with results versus checks not run. An analyzed unit states what behavior
   or contract was checked and against what evidence, not just a filename.
3. Verdict: `APPROVE`, `REQUEST_CHANGES` or `BLOCKER` only for a complete review;
   `INCOMPLETE — no final verdict` otherwise. Do not confuse a code blocker
   with inability to finish reviewing.
4. Blockers / Should fix / Nits / Questions, explicitly empty when appropriate.
5. Action plan: ordered concrete fix/verification steps; empty only for a clean,
   complete APPROVE with no follow-ups. For incomplete coverage, list what remains
   to review and what is needed to resume, not an implied approval.

Complete means the agreed review scope was analyzed, not that every possible
runtime test passed. Clearly disclosed unrun integration/build checks do not
automatically make source review incomplete; unanalyzed required areas do.

## Native execution and recovery

Maintain a compact orchestration record in parent session context: review ID,
fingerprint, parent/child IDs, selected agent, invocation timestamps, counters,
last verified progress, terminal errors and coverage status. This is not a new
plugin, todo entry or permanent checkpoint. Do not discard other reviewers'
completed work when one child fails. If independent reviewers are already part
of the requested plan, retain their scopes and independence; do not turn the
whole plan serial or change models/accounts to evade a concurrency limit.

1. Capture the child ID from native tool progress, results, errors and completion
   metadata, including failed calls. Prefer continuing that same child with
   `sessionID`; do not paste the full handoff into every continuation. Remind it
   of the review ID/fingerprint, ask it to inspect preserved history, verify
   prior coverage/findings and finish the remaining review/report.
2. A running child, native retry/backoff, pending form/permission or uncertain
   transport outcome is NOT a terminal failure. Never send a duplicate prompt,
   spawn a replacement, poll, or sleep-wait for progress while the child is
   known running. Use native completion delivery; do other useful independent
   work, or return control. Do not bypass a user's cancellation or denied access.
3. After a terminal failure or ambiguous return, make a bounded read-only
   reconciliation using native metadata/API in the same server/location/auth
   context. Verify the child belongs to this parent and matches this review's
   original prompt, ID, fingerprint and invocation. Do not guess by title or
   recency. If the ID is missing, inspect the parent's invocation metadata and
   parent-filtered child list, following pagination as needed. Inspect only the
   relevant child's messages; do not export unrelated sessions or credentials.
   Limit this reconciliation to two minutes, also respecting the recovery
   deadline below; if pagination or an unavailable API prevents a reliable answer
   within that bound, stop incomplete. This is a safety limit, not permission to
   poll a running child. Inspect current execution/native retry state before
   issuing another prompt.
   If state/correlation cannot be established safely, stop incomplete rather
   than risk a duplicate. An old successful assistant message is not necessarily
   this attempt's final report; correlate report identity, coverage and timeline.
4. Create a replacement only when continuation is genuinely unavailable (for
   example, confirmed missing/corrupt child), or a bounded search establishes
   no recoverable child and no still-running invocation. A provider error,
   temporarily unavailable API or absent ID alone does not justify replacement.
   Do not manipulate the database or fabricate parent links to force recovery.
5. A replacement receives the unchanged original handoff plus only a compact,
   evidence-based recovery appendix: old child ID, matching fingerprint,
   analyzed vs merely-read units, check commands/results, candidate findings
   with references and uncertainty, and remaining work. Label facts by source.
   Do not transfer the development discussion, whole child transcript, hidden
   reasoning or an unsupported claim that review was completed. Re-read the
   minimum necessary source to validate inherited leads. If no reliable progress
   survives, disclose that and re-examine as needed; never claim zero rework is
   guaranteed. Keep the old session and all independently valid results.

### Bounded retry budget

For each logical review allow the initial invocation plus **up to six further
invocations total**, shared by continuations, replacements and report-repair
requests. A replacement never resets the budget. Native provider retries inside
one still-running invocation are not new command-level invocations.

Maintain one ledger: `invocations_used` starts at 0, increases immediately before
each subagent tool invocation for this logical review, and may not exceed 7.
Before the initial invocation, additional counters are 0 used / 6 remaining;
this is initialization only, never a reset before subsequent invocations.
After the initial invocation, `additional_used = invocations_used - 1` and
`additional_remaining = 6 - additional_used`. Count failed admission/transport
calls too; an uncertain result is not permission to refund or repeat a call.
Partial-report completion, fingerprint clarification, continuation after failure
and replacement all consume these same additional slots, even without a provider
error. For example: initial INCOMPLETE + same-child completion = 2/7 invocations,
1/6 additional used, 5 additional remaining, 0 provider-failure retries.

Keep `provider_retries` separate; increase it only for a new invocation after a
terminal transient provider failure. This separate counter controls the delay
sequence, NOT permission for six extra calls beyond the shared seven-call cap.
For example, a report-repair slot followed by a provider retry leaves four slots;
that first provider retry waits 20 seconds. No provider error means no artificial
provider backoff, not "the recovery budget was unused". Never reset the ledger
by renaming a review/replacement or discarding an unwanted attempt at the same
scope. A genuinely different user-requested scope starts a separate review.

- Retry only a terminal, plausibly transient provider/concurrency/rate failure.
  HTTP 429 alone is insufficient: exhausted quota, billing/authentication,
  invalid requests, missing permissions and user cancellation require action,
  not blind retries. Preserve and report the actual error, redacting secrets.
- Between terminal transient failures use delays of **20, 40, 60, 90, 120, 120
  seconds** for provider retries 1–6, subject to the shared remaining slots.
  Honor a longer credible provider
  retry hint; do not shorten it to fit the budget. Wait through an available
  permitted shell/timer only after confirming the invocation is terminal. If no
  wait mechanism is permitted, stop and explain; never busy-loop.
- Start a no-progress clock at the first terminal recoverable failure. Before
  waiting and immediately before each recovery invocation, require less than
  **10 minutes since the last verified substantive review progress** (or that
  first failure when none follows). Do not start a wait/retry that the known
  provider delay places beyond this deadline. This bounds recovery, not a
  healthy running review: do not interrupt an active child at ten minutes.
- Reset that clock only on evidence of a newly analyzed review unit, validated
  finding or actual relevant check result. New tokens, file reads, another ID,
  restated findings or a successful launch alone do not establish that progress.
  The six-invocation cap never resets, even after genuine progress.
- Inform the user concisely of the failure, preserved child ID, shared counters
  and next delay. Do not promise eventual completion. On budget/deadline
  exhaustion or non-recoverable failure, stop with an incomplete-review report.

## Validate and return the report

Native completion/text alone is insufficient. Check review ID/fingerprint,
coverage, current-attempt provenance, all required sections and unchanged scope.
Check that the verdict agrees with material findings and open acceptance questions;
do not silently rewrite the child's verdict or downplay a finding. If it conflicts
with the report, request a reasoned resolution in the same child within the shared
budget. If unresolved, return the provisional report as incomplete, without a
final verdict. Formatting repairs must not demand extra findings or a preferred verdict.
For a terminal child with a truncated/incomplete report, request completion in
the same child only within the remaining budget; a transient provider failure
uses the delay policy above. Do not manufacture missing findings or a verdict.

Present the complete reviewer report in Russian, preserving its order, severity,
qualifiers and questions without softening or dropping findings. Translate prose
and headings, but keep code, paths, hashes, identifiers, commands and quoted
errors verbatim. Put scope and concise recovery provenance before it; clearly
label any orchestration limitation separately from the reviewer's conclusions.
Before the report, print `invocations_used/7`, `additional_used/6`,
`additional_remaining` and `provider_retries`; verify the ledger arithmetic.
Do not abbreviate hashes or add an orchestration postscript after the action plan.

If unfinished, say **Ревью не завершено; итогового вердикта нет**. Return any
reliably recovered partial findings as provisional with provenance and gaps,
along with attempts/child IDs, redacted terminal error and remaining work. Never
report APPROVE, a code BLOCKER or your own substitute review on that basis.

Always end with the reviewer's action plan, or an explicitly labeled recovery
plan when no final report exists. Then stop. Fixes, more retry budget or a changed
scope require a separate user request; neither parent nor child edits code here.
