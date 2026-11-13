---
description: Turn technical reports into clear, actionable issue briefs
subagent: false
---

Transform the provided report into a concise, decision-oriented
summary of unresolved issues, questions, and required actions.

## Scope

User request: $ARGUMENTS

- If no request is provided, transform only the immediately preceding
  assistant response. Use earlier context only to resolve references.
- If a request is provided, use it to determine the source, scope,
  and intended output. It takes precedence over the default.
- The request may target the entire session, a specific discussion,
  project files, repository state, or recent Git commits.
- When the request concerns repository data, use read-only tools
  to inspect the relevant information. Never invent missing facts.
- If the user requests a status or summary of completed work,
  report it directly instead of limiting the output to open issues.
- Apply the existing accuracy, clarity, and conciseness rules
  regardless of the selected scope.

## Priorities

In descending order:
1. Factual accuracy and fidelity to the source.
2. Clarity and unambiguous meaning.
3. Readability and natural language.
4. Conciseness without loss of essential information.

## Selection

- Extract issues that require a decision, clarification, or action.
- Distinguish actionable issues from observations, background details,
  completed work, and test results.
- Do not turn informational findings into new tasks.
- Preserve all relevant unresolved issues, including practical
  follow-up actions.
- Merge duplicates, but keep independent issues separate even
  when they share the same owner or technical context.
- Include resolved matters only when they affect an open decision.

## Organization

- Use a numbered list with short, situation-focused headings.
- Prioritize decisions that affect subsequent work.
- Group by owner or topic only when this improves readability.
- Give each issue its own short, self-contained explanation.
- Do not compress unrelated questions into one item.
- Keep supporting evidence close to the issue it supports.
- Do not reproduce test matrices, logs, exhaustive verification
  summaries, or implementation details unless explicitly requested.
- Omit standalone sections for completed work unless essential.

## Each issue should communicate

1. What happened or what remains uncertain.
2. The exact conditions under which the situation occurs.
3. What the user observes and why it matters, when established.
4. The specific decision, clarification, or action required.
5. Any essential caveat, limitation, or supporting evidence.

Present these naturally rather than as a rigid form.

Use a short heading followed by a readable paragraph.
Place the required question or action on a separate line when useful.
Include caveats and evidence only when they materially affect
understanding or the decision.

Do not enforce arbitrary word, sentence, or line limits.

## Accuracy

- Preserve the source's meaning, conditions, event sequence,
  and observed behavior.
- Never invent facts, outcomes, causes, risks, or confirmations.
- Distinguish observations, hypotheses, proposed solutions,
  accepted decisions, and unresolved questions.
- Do not describe uncertain behavior as a confirmed defect.
- Preserve distinctions between real integration tests,
  simulated events, mocked components, and untested behavior.
- When citing a test, retain the limitations relevant to the claim.
- Do not generalize results beyond what the evidence supports.
- If the source is ambiguous, preserve that uncertainty
  instead of silently choosing an interpretation.

## Clarity

- Make prerequisites and triggering conditions explicit.
- Distinguish similar cases when their behavior differs.
- Disambiguate terms that could refer to different entities.
- Explain behavior through concrete, observable situations.
- Prefer user-visible consequences over implementation details.
- Keep technical identifiers only when necessary for accuracy,
  reproducibility, or the requested decision.
- Avoid jargon, bureaucratic language, and speculative warnings.

## Conciseness

- Remove repetition, irrelevant history, and procedural noise.
- Keep explanations proportional to the complexity of each issue.
- Never sacrifice correctness or clarity for brevity.
- Do not add generic risk statements to make issues sound important.
- Do not summarize the entire source when only open issues matter.

## Final review

Before responding, verify that:
- Every included issue is actionable or necessary for context.
- No important unresolved issue was omitted.
- Independent issues were not accidentally merged.
- Preconditions and terminology are unambiguous.
- Statements do not exceed the available evidence.
- Each question has a clear decision or next action.
- Nothing can be removed without losing useful meaning.

Do not conduct external research, run tests, or modify files.
Read-only inspection of relevant local sources is allowed when
required by the user's request.
Return only the transformed report, without process commentary.

Write the final report entirely in natural, fluent Russian.
Preserve original code identifiers, paths, and technical status names.
