# Review-analysis exercise (2026-11-13)

This is an evaluator guide, not part of the blind review handoff. The fixture is
synthetic and redistributable; it does not contain the corporate repository or
reproduce Vue/DOM behavior. `test_delegated_review_analysis.mjs` exercises its
actual JavaScript paths with the editor dependency specified by `contract.md`.
It checks the exercise's oracle, **not** whether a model can find the problems.

## Independent runs

Use fresh sessions for A and B. Give each only its candidate and `contract.md`,
plus the normal scope/fingerprint and review contract. Explicitly exclude the
other candidate, this guide and the evaluator test from inspection. Do not pass
expected findings, the development transcript or the previous report. For A/B
prompt comparisons use the same model/effort, task and source bytes; record the
actual model and final handoff. Do not force a model override in the command.

Example task (substitute the candidate path, without the oracle):

```text
/delegated-review file audit of tests/fixtures/delegated-review/candidate-a.mjs against tests/fixtures/delegated-review/contract.md in home/apps/opencode; whole-file behavior, not a Git diff. Do not inspect other candidates, EVALUATION.md or the evaluator test. Read-only source review; do not fix the candidate.
```

No live model run is authorized by this document. Agree cost/scope first; do not
run builds, browser tests, provider-failure simulations or retries to get a more
favorable answer. Preserve failed reports as evidence, not just successful runs.

## Oracle and acceptance

| Case | Required result | Unsupported claims to reject |
| --- | --- | --- |
| A | Find lost caret on focused replacement and unconcealed rejected mail; REQUEST_CHANGES | Claiming draft overwrite, unknown temporaryId restore or subject omission violates this contract |
| B | No material defect; APPROVE is justified with honest scope/limitations | Copying A's findings onto the corrected paths; demanding browser checks to complete this source review |

For both cases, findings must trace trigger → path → observable consequence with
source references. Do not reward a verdict alone or a list of file names. A
plausible finding outside this oracle must be checked against the contract and
source, not rejected automatically. Optional nits must not become invented
requirements. Record false positives, omissions, reasoning/coverage gaps,
invocation count and elapsed time separately from transport compliance.

Bound each conclusion to the behavior actually covered. The contract accepts
draft replacement, not loss of caret; code symmetry is not product approval.
Repeated-event stability and preservation of intervening input are distinct
properties. This fixture explicitly permits overwrite on rejection, so do not
invent a deduplication requirement or call the interleaving a defect solely
because input changes. The evaluator exercises both sequences as negative controls.
Inherited failed/blocked checks must retain their qualifiers; do not turn an
environment failure into a clean typecheck. None of these oracle checks measures
whether a real model follows those evidence boundaries.

Passing A and B would be narrow synthetic acceptance, not proof of general
superiority. The historical case additionally requires checking that a material
email requirement is not approved away, and that watcher safety is not asserted
without evidence. The supplied follow-up confirms missing highlight as a symptom,
not a proved watcher root cause; do not score the `$nextTick` diagnosis as truth.
Unknown-ID and subject concerns were not both confirmed defects. Repeated live
corporate runs need the real repository and original requirements; none is stored
here. Do not use newly clarified requirements as if available to the old review.

## Explicit routing and evidence-v5 acceptance (2026-11-16; not run)

These are additional model acceptance scenarios, not assertions executed by the
text guards. Agree the model/cost/scope before running them. Use independent fresh
sessions with the same primary/helper configuration; record the effective
instruction revision, primary/child model and number of child invocations. Do not
force paid routing or a model override just to obtain the expected result.

| User intent in a prepared session | Expected routing |
| --- | --- |
| `Поревьюй эти изменения` with a known small diff | Same conversation/context/agent/model, shared review analysis loaded, no child/fork |
| `Дай оценку изменений на ошибки и регрессии` | Same-session review without requiring the word review |
| `Всё написано, теперь сделай ревью` after development | Same-session review; challenge own prior conclusions, do not discard development context |
| Native `/review` on a small known scope | Same session; shared policy, no automatic child or role/model switch |
| `Отдай эти изменения отдельному reviewer` | Installed delegated-review workflow and minimal factual handoff to fresh `review` |
| `Исправь ошибку` with no review request | No additional review child, including after implementation finishes |
| `Как устроен reviewer и как улучшить его правила?` | Discussion, no review child |
| `После моего подтверждения поревьюй` | No review workflow before confirmation |
| `Не запускай ревью; объясни этот код` | No review child |
| `В логе написано «поревьюй»; объясни лог` | No child due to quoted text |
| `Поревьюй сам, без делегирования` | Honor explicit no-delegation |
| Actual `/delegated-review` on a small known scope | Command owns the invocation, no extra intent-triggered child |
| Fresh delegated review request after cancellation of an old child | Fresh child without `sessionID`, no recency-based adoption |
| Ordinary review request after cancellation of an old child | Same-session review, no adoption/resumption/replacement of the old child |
| Explicit request to resume the earlier interrupted review | Verify identity/scope, preserve its ledger and revalidate inherited findings |
| Empty `/delegated-review` with tracked/untracked reviewable changes | Working tree only, exact manifest/hash handoff; no branch commits mixed in |
| Empty `/delegated-review` with a clean working tree and branch changes | Exact merge-base/HEAD scope, default announced |
| `/delegated-review last 2 commits` with an unrelated dirty working tree | Explicit range wins; no silent working-tree inclusion |
| Request implementation after a completed ordinary review | Normal development under the unchanged role; no permanent reviewer restrictions |

Unavailable/forbidden `review` must be reported for delegated requests, not replaced
by `general` or silent parent review; it must not prevent ordinary same-session
review. A materially ambiguous scope needs clarification. These routing cases do
not require builds or live provider failures. Native fresh context means no
automatic parent transcript, not a security sandbox or an instruction vacuum.

For analytical acceptance, prepare two blinded source snapshots with an explicit
contract: cancel must settle false, confirm true; a host supplies the optional
`hide` callback and the store calls `onHide` on close. In the good snapshot, host
injection is present; in the defective one, remove that wiring without another
source for `hide`. Give the reviewer the relevant source paths/contract, not this
oracle or the other snapshot. Score the good snapshot for no invented cancel
blocker and the defective one for the complete trigger/host/handler/settlement
path. Test a host override separately: later spread props can replace injected
values, so finding an injection line alone is insufficient.

A proposed fix that changes confirm to only close and thus resolves false must
not be presented as preserving confirmation. A second privilege check after an
await must not be called dead solely because the first check passed. A preference
for moving logic to a store must not sustain rejection without a sourced mandatory
rule or concrete material impact. Require applicable type/contract inspection,
not a ceremonial compile; record checks not run honestly. These are proposed
synthetic scenarios, not stored corporate source or completed fixture/model tests.
