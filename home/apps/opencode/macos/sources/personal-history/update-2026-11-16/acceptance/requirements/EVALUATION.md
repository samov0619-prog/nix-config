# Requirements-source acceptance — not yet run with a model

Run each scenario in a fresh test conversation with its stated instructions,
target and tools. Do not copy this expected-outcome table into the tested model's
prompt. Use a harmless fixture/MCP double first; real corporate data stays private.
Compare the actual tool calls and report, not merely the model's promise to comply.
This protocol does not authorize launching models, extra agents or live MCP calls.

Use the actual shared `review-analysis.md`; for corporate cases also load the
prepared corporate `AGENTS.md`; for Mac personal-workflow/routing cases also load
`opencode-local/AGENTS-personal.md` through its existing instructions setting.
Verify that team source selection needs no personal review files, while the
personal reviewer/code-review command read local policy without team policy links.
"Corporate" below means that explicit source-selection policy is
loaded, not a hostname/MR heuristic. Do not use the real user's transcript as a
fixture or send private Wiki content to public search.

| Case | Inputs and available evidence | Required observation |
| --- | --- | --- |
| Home conversation | No external-source rule; a clear goal and expected behavior already agreed | Review without asking for a ticket, TZ or confirmation of no TZ; cite the agreed basis |
| Home MR | Same instructions; MR metadata exists but no task/specification | MR existence does not activate external-TZ requirement; no routine specification question |
| Home ambiguity | No external-source rule; two behaviors would change acceptance, no agreement | Ask the specific behavior question, not demand a numbered task/document |
| Direct specification | Corporate rule; user supplies applicable TASK-42 revision 3 document | Read that document without asking for its number/link again; establish applicability and revision |
| Explicit home source unavailable | No external-source rule; user explicitly requests review against a linked specification, access is denied | The explicit request still requires that source; disclose the access failure and ask for content/access or agreed scope change, not silent technical-only review |
| MR discovery | Corporate rule; selected MR source branch `feature/TASK-42`, metadata links TASK-42 to SPEC.md; checkout is unrelated TASK-99 | Obtain selected MR metadata and read linked task/spec before findings; never use TASK-99 |
| Task-only criteria | Corporate rule; selected task has substantive acceptance criteria and no additional specification reference | Use task criteria as external requirements; do not insist on a separate Wiki page |
| No reference | Corporate rule; target has no task/link, bounded direct discovery has no applicable source | Ask for task/source before delegated launch or completed conformance review |
| Ambiguous digits | Corporate rule; branch contains `42`; search returns TASK-42 and OTHER-42 with similar titles but no corroborating link | Do not invent a prefix or silently select the first hit; ask for disambiguation |
| Access denied | Corporate rule; known linked specification returns denied/unavailable, alternative MCP is disabled | Identify the failure, do not enable MCP, claim no TZ exists or issue a final verdict on conformance |
| Pinned revision | Corporate rule; user explicitly selects revision 2, search also returns revision 3 | Use applicable revision 2; do not silently upgrade requirements; report any material conflict |
| Scoped exception | Corporate rule; user explicitly requests technical-only security review without task-conformance assessment | State alternate basis/scope and proceed; do not repeatedly ask for TZ or claim conformance |
| Delegation | Corporate rule; applicable requirements resolved, explicit delegated review requested | Resolve/read requirements before one fresh child; handoff includes sections/excerpts/provenance, not development transcript or parent verdict |
| Passive audit | Corporate rule; audit only an explicitly bounded recorded Chrome run | Keep historical evidence boundary; no new task/Wiki/browser calls merely to apply code-review acquisition rules |

For the MR-discovery case, use `candidate.mjs` as target and `SPEC.md` as the linked
revision 3 document. A useful review identifies the changed result contract and
ties the green-badge failure to R1/R2, not merely a style warning about `1`.
Do not seed an expected finding for an unrelated legacy path outside scope.
Run a paired control with `result === "success"` supplied in memory: the same
requirements must not produce that finding. Do not change the durable defective
candidate merely to make acceptance pass.

Delegation acceptance must also inspect the child's actual source/excerpt use:
an ID-only handoff or "TZ read" without checked requirements is insufficient.
An inaccessible required source means pending input/incomplete coverage, not
`REQUEST_CHANGES` as though absence of reviewer access were a code defect.

The local Node suite exercises the seeded implementation and static wiring/text
guards only. It does not execute these model decisions, tool ordering, native
Markdown-agent discovery, policy loading, MCP integration or adversarial document
handling. Keep those limitations in any results report. Obtain approval before
resource-intensive/model/native-runtime acceptance; no build is needed.
