---
description: Map task requirements to a minimal change plan and concrete checks
subagent: false
---

Analyze `$ARGUMENTS` before implementation. If arguments are empty, use the task
already established in this conversation. Ask for scope only if it cannot be
identified unambiguously; do not invent a task from unrelated repository changes.

## Boundary

- Stay in the current conversation with its existing agent and model. Respect
  applicable project instructions, permissions and Plan restrictions.
- This command authorizes read-only analysis, not implementation, live browser
  actions, tests, builds, installation, external writes, Git mutations or commits.
  Do not delegate unless separately requested or required by applicable instructions.
- Use available, permitted read-only tools for relevant sources. Do not enable
  integrations or ask for credentials. If access is missing, report the coverage gap.
- Return the analysis in the conversation. Do not create a plan file, task log,
  tracker comment or other artifact unless separately requested.

## Analysis

1. State the user-visible goal, acceptance criteria and explicit non-goals.
   Separate the required outcome from a suggested implementation. Prefer an
   existing supported capability or a smaller change when it meets the requirements.
2. Establish the requirements basis from the request, agreed clarifications and
   relevant project documentation. Follow any applicable requirement to retrieve
   an external task/specification; do not impose a corporate tracker requirement
   on other projects. Retain source identities, relevant sections and revisions.
   Read the material that supports the conclusion, not just titles or previews.
3. Inspect the relevant implementation, contracts and existing tests. Identify
   affected boundaries and actual consumers before proposing new abstractions.
   Distinguish documented requirements, observed behavior and assumptions.
4. For API/integration work, identify the target environment and contract version:
   request/response shapes, validation, errors and compatibility as relevant.
   A proposed backend MR contract is not evidence that the deployed API supports
   it. Record that dependency and how the target deployment will be checked.
5. For UI work, identify relevant loading, empty, success, error and permission
   states, along with navigation and user-data effects. Include accessibility or
   other cross-cutting requirements where applicable, not an unrelated checklist.
6. Map each material requirement to the smallest coherent change and a concrete
   verification scenario with an independently justified expected result. Reuse
   suitable tests. Separate unit/mock coverage from real integration or browser
   acceptance, and distinguish permitted lightweight checks from work needing
   separate approval. Do not invent estimates, architecture mandates or delivery
   steps that the task does not require.
7. Surface conflicting sources, missing contracts and unresolved decisions that
   materially affect correctness or scope. Do not silently choose a convenient
   interpretation. Separate blockers from assumptions that can safely remain open;
   do not ask again about decisions already settled unless new facts change them.

## Result

Lead with the proposed approach and why it meets the goal. Keep the output
proportional to the task; for a small change, a short explanation is enough.
For a substantive task, include:

- Goal, scope and requirements sources, with material access/version limitations.
- A compact mapping: requirement → affected area/change → check and expected result.
- Dependencies, risks and unresolved questions, clearly marked as blocking or not.
- An ordered implementation/verification plan, identifying any separate approvals.

Clearly distinguish inspected facts from proposals and unrun checks. Do not claim
that implementation or verification has occurred, and do not start implementing
after returning the plan without a separate request to proceed.
