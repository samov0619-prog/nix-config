# Synthetic message composer contract

This is a small dependency-injected JavaScript model, not a browser or Vue test.
Review the specified candidate against this contract. Do not read the evaluator
or another candidate during a blind review; do not modify the candidate.

- A rejected message replaces the draft even if the user has started a new one.
  This overwrite is intentional. The backend guarantees that a rejection never
  describes a successfully delivered message and supplies the rejected text.
- A focused editor preserves its numeric caret offset during replacement, clamped
  to the new text length. An unfocused editor must not be focused by replacement.
  The injected editor's `replaceText` resets the caret to zero; `setCaret` does not focus it.
- Rejected text is concealed in both chat and mail history until revealed.
  The mail subject is not validated by the backend and is outside word blocking.
- Send is blocked only while the draft body contains a returned forbidden word.
  Returned words are nonempty strings; the array may be absent. Matching is
  case-insensitive. Other messages do not replace the draft.

The supplied contract has no promise about Vue scheduling, native DOM selection,
network behavior, or restoring historical messages on click. Do not invent one.
