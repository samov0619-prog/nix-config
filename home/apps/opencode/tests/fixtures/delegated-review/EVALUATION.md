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
