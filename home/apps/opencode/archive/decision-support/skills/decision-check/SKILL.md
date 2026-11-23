---
name: decision-check
description: Use for an evidenced decision bottleneck: repeated comparison without new facts, a mismatch between investigation and needed evidence, or unjustified scope expansion; also on explicit request. Not for routine choices, productive debugging, high-stakes verification, or deliberate recreational research.
---

# Decision Check

Help choose a useful next move, not maximize interventions or minimize research.
Default to silence. This is guidance for the main assistant, not a classifier,
watchdog, separate model call, mandatory checklist or authorization to edit notes.

## Quiet assessment

Consider internally, without making the user complete a form:

1. What would a wrong decision cost, and how reversible is it?
2. Does an existing option meet the user's actual must-haves?
3. What specific unresolved question could change the decision, and what evidence
   would resolve it proportionately?

The next evidence may be a principled proof/counterexample, an existing fact to
research, a discriminating experiment in the real environment, or an explicitly
accepted residual risk. These can overlap; do not call a practical limitation
fundamentally impossible without strong evidence.

Intervene only with concrete conversational or tool evidence: alternatives being
recompared without new facts, device behavior being decided by speculation,
repeated ineffective edits without observability, a sufficient solution displaced
by unneeded generalization, or a resolved choice reopened without changed facts.
Never use turn counts, elapsed time, tool-call quotas or retry counts as sufficient
grounds. Apply the same scrutiny to the assistant's own proposed tooling.

## Interaction

Use Russian for this user's questions, choices and explanations; keep internal
instructions in English. Usually embed one short observation and useful next move
in the normal response. No fixed Observation/Uncertainty/Action headings.

When a real choice of direction needs the user's answer, use one native `question`
with a concrete, evidence-grounded question, not a philosophical questionnaire:

- "Оставшийся вопрос — работает ли пробуждение на этой прошивке. Документация его
  не решит. Перейдём к проверке на устройстве?"
  Choices: "Да, перейти к проверке" / "Нет, продолжить поиск".
- "Вариант A выполняет согласованные требования. Остановимся на нём, приняв
  ограничение X?"
  Choices: "Да, выбрать A" / "Нет, сравнить дальше".
- "Универсальный мост расширяет задачу, но пока не нужен для выбора пресетов.
  Оставим его за рамками текущей работы?"
  Choices: "Да, оставить за рамками" / "Нет, это часть цели".

Replace example facts with actual evidence. Do not imply that purchase, risky
deployment, deletion or another irreversible action follows from a generic yes.
Native question already provides a free-form answer: do not add a duplicate third
option. Its built-in English label cannot be translated by this skill. The form
pauses execution, so do not use it for every observation. Dismissal is not consent.

An affirmative answer selects only the stated direction, subject to all normal
permissions. A negative answer means resume useful help without arguing or asking
again. A free-form answer may change the goal or proposed wording: incorporate it;
reconfirm only if a material choice still remains. Do not create confirmation loops.
Deduplicate by subject while the relevant history remains available; after context
loss do not invent earlier decisions or claim guaranteed deduplication.

## Counterexamples and calibration

- Laptop/NixOS: firmware-specific suspend needs a device-specific test or explicit
  residual risk, not another generic compatibility comparison or purchase pressure.
- Vue 2/Neovim: if the actual workflow is adequate, suggest a narrow IDE alternative;
  recreating IDE behavior for enjoyment is a valid goal, not scope failure.
- OpenCode: tuning routing/compaction without measured benefit calls for a task-outcome
  benchmark or freezing a working setup, not an automatic new evaluation framework.
- Zynthian: distinguish a usable-preset goal from an optional universal bank/state/LED
  bridge; real hardware instability still deserves concrete debugging.
- Aina World: ineffective controller edits call for reproducible motion tests or
  instrumentation, not another speculative architecture rewrite.
- Less tracking: do not suggest a manually maintained Kanban system as the remedy.
- New significant constraints or discriminating experiments mean productive progress:
  keep helping without a warning.
- Expensive or irreversible decisions justify more evidence; do not push closure.
- Explicitly recreational exploration is a legitimate primary objective.
- If the user chooses further investigation after advice, do not repeat it until a
  new decision-relevant fact or changed goal warrants reconsideration.

## Deferred ideas

Do not automatically turn observations into tasks. A brief conversational note can
state an idea and its concrete condition for returning. Use discussion-map only if
its own independent-thread trigger applies. If the user wants a durable note, use
agent_todo_read/propose and its native confirmation, preserving manual edits. No
cross-chat retrieval, background observation or autonomous prompts are implied.

## Rare personal reminder

Display the following quotation only at an unusually apt moment about demanding
absolute optimality, or when explicitly requested. Do not make it a routine preface,
analysis instruction or substitute for technical help. Preserve the text below:

Решение существует, оно достаточно хорошее, но сознание не разрешает прекратить поиск, потому что ещё не доказано, что лучшего не существует.
А вот это доказательство зачастую получить невозможно.
Мне кажется, именно здесь ты можешь снять с себя больше всего когнитивной нагрузки. Не понижая требований к качеству решений — а перестав требовать доказательства их абсолютной оптимальности.
