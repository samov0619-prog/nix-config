# Shared review analysis

Review policy: evidence-v5.

Apply this policy while performing a requested review, in the current session or
as a delegated reviewer. It does not switch agents, select a model or authorize
delegation. An ordinary review keeps the conversation context; a delegated review
uses its supplied handoff and scoped evidence. Existing permissions and Plan
restrictions remain applicable. Review alone authorizes no fixes, builds,
installation, commits or mutating checks; propose unapproved checks instead.
These are review-task rules, not a permanent switch out of normal development.

Use the agreed scope and requirements, source, contracts and tests, not the
author's confidence or prior verdict, including your own earlier conclusions.
Distinguish documented requirements from inferred intent. Clarify materially
ambiguous scope rather than silently expanding it.

Determine the object of review from the agreed scope. For a recorded-evidence
audit, apply the supplied audit contract to the truth/support of reported claims,
not to product readiness. Source-review path/type requirements below apply only
when source code is part of that scope; do not demand source access, compilation
or live re-testing merely to complete a passive evidence audit. Its causal path is
requirement → recorded action → observed result → claim, with event/target references.
Use the audit contract's claim statuses, coverage rules and verdict criteria: an
honestly reported failing feature test can have SUPPORTED claims and an APPROVE
audit. Do not reject that audit solely because the application has a defect.
Shared evidence, uncertainty and review-only rules still apply.
For a consequential supported claim, ground every decisive causal link in the
scoped evidence, not another model's explanation. A before/after state difference
establishes a change, not who caused it or which unobserved operation occurred.
If the decisive link is missing, preserve that limitation in the claim status and
verdict; do not mark it supported while relegating necessary evidence to optional
follow-up. Do not demand unrelated extra proof when the supplied contract is met.

Analysis comes before report formatting. Establish the expected behavior from
requirements or justified invariants, then trace the changed behavior through its
callers, state updates and observable result. A fingerprint identifies the input;
a coverage list or passing test suite does not establish behavioral correctness.

Use a few risk-driven scenarios, not an exhaustive checklist: normal use and a
plausible failure/interleaving, including relevant channel/platform branches.
For asynchronous/stateful changes consider delayed or duplicate events, new user
input, focus/selection, session switching and reload/recovery where applicable.
Follow the whole transition, not just isolated helpers. Compare analogous paths
when one preserves state or applies a requirement that another omits.
Keep conclusions property-specific: repeated-event idempotence alone does not
establish safe interleaving with new user input, and restored text does not prove
preserved selection. State the scenario and evidence behind a claim of correctness.

Try a concrete counterexample to important safety claims, including your own.
Check whether a later watcher or callback repairs the intermediate state before
calling it a defect; do not assume event ordering is safe without tracing it.
Separate source reasoning from runtime observation. If a timing/DOM claim cannot
be settled statically, name the uncertainty and the smallest discriminating check,
not a confident diagnosis or an untested fix. Do not infer a bug from missing tests alone.

Before a blocking finding, trace the complete relevant implementation path from
the trigger through wiring and state transitions to the claimed observable failure.
Inspect applicable types/signatures and actual callers, wrappers, hosts/providers,
injected/default arguments and spread/override order; a value absent at one call
site may be supplied elsewhere. A partial search cannot establish absence: broaden
it when the conclusion depends on sources outside the searched area. Look for a
concrete way the existing implementation could invalidate your finding. If the
decisive path is unresolved, report the evidence gap/question, not a demonstrated
blocker. This does not require running the entire application for a source-proven bug.

Use types to understand contracts, not as proof of runtime behavior. Choose a
mechanical check when it can resolve a concrete uncertainty; inspect the project's
documented command, cost and side effects first, and reuse relevant existing results.
Compilation is not mandatory for every review, and a passing typecheck alone does
not prove runtime correctness. Even `--noEmit` may write incremental metadata.
Run only permitted, known-cheap, non-mutating checks; otherwise propose the exact
check with its purpose and limits instead of running it.

Before suggesting a fix, trace it through the original failing scenario and the
neighboring success/cancel/error paths it changes. Preserve distinctions such as
confirmation versus cancellation, and revalidate mutable state after an `await`
where relevant; observable state is not necessarily unchanged while awaiting input.
An untested sketch must be labeled as such, not presented as a verified fix.
Architecture/style preferences or a large function are not blockers by themselves:
cite an applicable mandatory project rule or concrete material impact. If a finding
is disproved, withdraw it and reassess the verdict from the remaining evidence;
do not promote an optional refactor merely to preserve rejection.

Calibrate the verdict to impact and evidence, not the number of findings. An unmet
material requirement needs REQUEST_CHANGES; a contract question that could change
acceptance also needs REQUEST_CHANGES pending clarification, not APPROVE with a
buried caveat. Such a question is not a confirmed defect. Use BLOCKER for a
demonstrated blocking defect, not simply missing runtime verification. APPROVE may
include optional improvements or an explicitly accepted risk with its source and
scope; an author's "documented workaround" alone does not establish that acceptance.
Acceptance is effect-specific: approval of one behavior does not waive separate
side effects. Matching implementation paths show consistency, not product acceptance.
Keep unsourced exemptions as observations/questions; assess residual effects by
their own impact, without automatic severity escalation.
Do not invent requirements or escalate every unknown. Distinguish source-review
completion from release/runtime acceptance; disclosed unrun checks alone do not
prevent a complete source review or require rejection.

Prioritize concrete correctness/security issues and regressions, including
callers, error handling, concurrency and meaningful missing tests. Check relevant
surrounding contracts without silently broadening the review target. Give
reviewed-version file:line evidence, impact and triggering conditions, with a
reproducible check where possible. Separate verified findings, hypotheses and
questions; do not fill a report with speculative nits. Say when no issue was
found within the coverage actually achieved, not that untested code is proven safe.
Preserve failure qualifiers and verification limits when citing inherited checks:
failed or blocked is not clean, even if the reported error predates this change.
Attribute unverified results to their source rather than treating them as your own.

Follow the requested report format. Always distinguish analyzed coverage from
mere reads, completed checks from unrun ones, and a complete review from a partial
report. For incomplete coverage give provisional findings and gaps without any final
verdict: no APPROVE, REQUEST_CHANGES or BLOCKER. For completed coverage give the
requested verdict, findings ordered by severity, questions and an actionable
plan; do not edit the implementation after reporting. When no format is supplied,
use Scope, Coverage and checks, Findings, Questions, and Action plan. Keep coverage
concise and evidence-linked, not a file-by-file assertion of safety. Finish with
concrete next steps or an explicitly empty plan when the complete review needs no follow-up.
