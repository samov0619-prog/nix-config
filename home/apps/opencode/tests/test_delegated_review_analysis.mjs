// Evaluator for a synthetic blind-review exercise, not a model-quality test.
import assert from "node:assert/strict";
import { test } from "node:test";

import { Composer as CandidateA } from "./fixtures/delegated-review/candidate-a.mjs";
import { Composer as CandidateB } from "./fixtures/delegated-review/candidate-b.mjs";

function editor(focused = true, caret = 4) {
  return {
    focused,
    caret,
    text: "new draft",
    getCaret() {
      return this.caret;
    },
    replaceText(text) {
      this.text = text;
      this.caret = 0;
    },
    setCaret(offset) {
      this.caret = offset;
    },
  };
}

test("candidate A exhibits the two seeded contract violations", () => {
  const input = editor();
  const composer = new CandidateA(input);
  composer.receive({ status: "rejected", text: "older message" });
  assert.equal(input.caret, 0); // Contract requires 4; renderer reset is not repaired.
  const message = { status: "rejected", text: "private" };
  assert.equal(composer.historyView("chat", message).concealed, true);
  assert.equal(composer.historyView("mail", message).concealed, false); // Requires true.
});

test("candidate B preserves or clamps the focused caret", () => {
  for (const [text, expected] of [["older message", 4], ["hi", 2]]) {
    const input = editor();
    const composer = new CandidateB(input);
    composer.receive({ status: "rejected", text });
    assert.equal(input.text, text);
    assert.equal(input.caret, expected);
    assert.equal(input.focused, true);
  }
});

test("candidate B conceals rejected history across both channels until revealed", () => {
  const composer = new CandidateB(editor());
  for (const channel of ["chat", "mail"]) {
    const message = { status: "rejected", text: "private" };
    assert.equal(composer.historyView(channel, message).concealed, true);
    assert.equal(composer.historyView(channel, message, true).concealed, false);
    assert.equal(
      composer.historyView(channel, { ...message, status: "delivered" }).concealed,
      false,
    );
  }
});

for (const [name, Composer] of [["A", CandidateA], ["B", CandidateB]]) {
  test(`candidate ${name}: intentional overwrite and absent words are not defects`, () => {
    const input = editor(false);
    const composer = new Composer(input);
    composer.receive({ status: "rejected", text: "old", temporaryId: "unknown" });
    assert.equal(composer.draft, "old");
    assert.equal(input.text, "old");
    assert.equal(input.focused, false);
    assert.equal(composer.canSend(), true);
    composer.receive({ status: "delivered", text: "another" });
    assert.equal(composer.draft, "old");
  });

  test(`candidate ${name}: blocking applies to the body, not the subject`, () => {
    const composer = new Composer(editor());
    composer.receive({ status: "rejected", text: "BLOCKED", words: ["blocked"] });
    assert.equal(composer.canSend(), false);
    composer.draft = "clean";
    composer.subject = "blocked";
    assert.equal(composer.canSend(), true);
  });

  test(`candidate ${name}: repeated-event stability does not imply preservation of intervening input`, () => {
    const input = editor();
    const composer = new Composer(input);
    const event = { status: "rejected", text: "old", words: ["old"] };
    composer.receive(event);
    const snapshot = [composer.draft, composer.words, input.text];
    composer.receive(event);
    assert.deepEqual([composer.draft, composer.words, input.text], snapshot);
    composer.draft = "new input";
    input.text = "new input";
    composer.receive(event);
    // This overwrite is explicitly allowed by the fixture contract, not a new bug.
    assert.equal(composer.draft, "old");
    assert.equal(input.text, "old");
  });
}
