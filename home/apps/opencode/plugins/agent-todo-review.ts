// Shared, versioned native-form transport. Only the scrollable presenter emits
// the proposal-bound Submit value; a clipped stock question cannot save by accident.
export const REVIEW = "agent-todo-review/v1\n";
export const SUBMIT = "agent-todo-submit/v1:";
export type ReviewNote = { id: string; title: string; text: string };
export type ReviewDescriptor = {
  version: 1;
  token: string;
  notes: { id: string; title: string; key: string }[];
  summary: string;
};

export function reviewQuestions(
  notes: ReviewNote[],
  summary: string,
  token: string,
) {
  const descriptor: ReviewDescriptor = {
    version: 1,
    token,
    notes: notes.map(({ id, title }, i) => ({ id, title, key: `q${i}` })),
    summary,
  };
  return [
    ...notes.map((note, i) => ({
      header: String(i + 1),
      question: note.text,
      options: [],
      multiple: false,
    })),
    {
      header: "Todo decision",
      question: REVIEW + JSON.stringify(descriptor),
      options: [{ label: "Reject", description: "Nothing will be saved." }],
      multiple: false,
    },
  ];
}

export function readReview(form: {
  metadata?: Record<string, unknown>;
  fields: readonly { key: string; type: string; description?: string }[];
}): ReviewDescriptor | undefined {
  if (form.metadata?.kind !== "question") return;
  const last = form.fields.at(-1);
  if (!last?.description?.startsWith(REVIEW)) return;
  try {
    const value = JSON.parse(last.description.slice(REVIEW.length));
    if (
      value.version !== 1 ||
      typeof value.token !== "string" ||
      !/^[a-f0-9]{64}$/.test(value.token) ||
      typeof value.summary !== "string" ||
      !Array.isArray(value.notes) ||
      value.notes.length + 1 !== form.fields.length ||
      last.key !== `q${value.notes.length}` ||
      last.type !== "string" ||
      !value.notes.every(
        (note: ReviewDescriptor["notes"][number], i: number) =>
          typeof note.id === "string" &&
          typeof note.title === "string" &&
          note.key === `q${i}` &&
          form.fields[i].key === note.key &&
          form.fields[i].type === "string",
      ) ||
      new Set(value.notes.map((note: { id: string }) => note.id)).size !==
        value.notes.length
    )
      return;
    return value;
  } catch {
    return;
  }
}

export function reviewAnswer(
  notes: ReviewNote[],
  token: string,
  answers: string[][],
) {
  const valid =
    Array.isArray(answers) &&
    answers.length === notes.length + 1 &&
    answers.every(
      (answer) =>
        Array.isArray(answer) &&
        answer.length <= 1 &&
        answer.every((s) => typeof s === "string"),
    );
  if (!valid)
    return {
      status: "revise" as const,
      feedback: [],
      batchFeedback: "",
      invalid: true,
    };
  const selected = answers.at(-1)?.[0] ?? "";
  const feedback = notes.flatMap(({ id, title }, i) => {
    const text = answers[i]?.[0] ?? "";
    return text.trim() ? [{ id, title, feedback: text }] : [];
  });
  const batchFeedback =
    selected === SUBMIT + token || selected === "Reject" ? "" : selected;
  return {
    status:
      selected === "Reject"
        ? ("declined" as const)
        : selected === SUBMIT + token && !feedback.length
          ? ("approved" as const)
          : ("revise" as const),
    feedback,
    batchFeedback,
  };
}
