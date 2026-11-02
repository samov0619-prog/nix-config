import "./plugin-loader.mjs";
import assert from "node:assert/strict";
import { test } from "node:test";
import { execFileSync } from "node:child_process";
import {
  mkdtemp,
  mkdir,
  readFile,
  writeFile,
  rm,
  symlink,
  access,
} from "node:fs/promises";
import { join } from "node:path";
const {
  todoStore,
  setupTodo,
  countRevisits,
  describeChanges,
  applyNoteChanges,
  noteReview,
  cleanNote,
} = await import("../plugins/agent-todo.ts");
const { reviewAnswer, reviewQuestions, readReview, SUBMIT, REVIEW } =
  await import("../plugins/agent-todo-review.ts");

const YES = "Submit";
const NO = "Reject";
const consent = (input) =>
  SUBMIT +
  JSON.parse(input.questions.at(-1).question.slice(REVIEW.length)).token;
const signal = () => new AbortController().signal;
async function fixture(t, initialized = true) {
  const tmp = await mkdtemp("/tmp/opencode/agent-todo-test-");
  t.after(() => rm(tmp, { recursive: true, force: true }));
  const root = join(tmp, "notes");
  const git = (...args) =>
    execFileSync("git", args, { cwd: root, encoding: "utf8" }).trim();
  if (initialized) {
    await mkdir(root);
    git("init", "--quiet", "--initial-branch=main");
    git("config", "user.name", "Todo Fixture");
    git("config", "user.email", "todo@example.invalid");
  }
  const file = join(root, "todo.md");
  return { root, file, git, store: todoStore(root) };
}
async function plugin(
  f,
  answer = YES,
  onQuestion = async () => {},
  denied = false,
) {
  const tools = new Map();
  const forms = [],
    permissions = [];
  tools.set("question", {
    execute: async (input) => {
      forms.push(input);
      await onQuestion(input, forms.length - 1);
      const selected =
        typeof answer === "function"
          ? await answer(input, forms.length - 1)
          : answer;
      return {
        output: {
          answers: Array.isArray(selected)
            ? selected
            : input.questions.map((question, i) =>
                i === input.questions.length - 1
                  ? [selected === YES ? consent(input) : selected]
                  : [],
              ),
        },
        content: "native answer",
      };
    },
  });
  const ctx = {
    session: {
      context: async () => [
        { type: "user", id: "request-1" },
        { type: "assistant", id: "message" },
      ],
    },
    permission: {
      assert: async (p) => {
        permissions.push(p);
        if (denied && p.action === "edit") throw Error("Plan denied edit");
      },
    },
    tool: {
      transform: async (fn) => {
        fn({
          get: (name) => tools.get(name),
          add: (tool) => tools.set(tool.name, tool),
        });
        return {
          dispose: async () => {
            tools.delete("agent_todo_read");
            tools.delete("agent_todo_propose");
          },
        };
      },
    },
  };
  const cleanup = await setupTodo(ctx, f.root);
  const context = {
    sessionID: "session",
    agent: "build",
    messageID: "message",
    id: "call",
    signal: signal(),
  };
  const read = async () =>
    JSON.parse(
      (await tools.get("agent_todo_read").execute({}, context)).content,
    );
  const propose = async (extra = {}) => {
    const before = await read();
    return JSON.parse(
      (
        await tools.get("agent_todo_propose").execute(
          {
            base: before.fingerprint,
            content: "# Todo\n\n- Test device\n",
            reason: "Сохранить идею проверки устройства.",
            message: "add device test note",
            ...extra,
          },
          context,
        )
      ).content,
    );
  };
  return { tools, forms, permissions, read, propose, context, ctx, cleanup };
}

test("read is lazy: no directories, Git or writes; missing native question fails open", async (t) => {
  const f = await fixture(t, false);
  assert.equal((await f.store.snapshot()).content, "");
  await assert.rejects(access(f.root));
  const p = await plugin(f);
  assert.equal((await p.read()).initialized, false);
  await assert.rejects(access(f.root));
  await p.cleanup();
  assert.equal(p.tools.size, 1);
  let added = 0;
  const cleanup = await setupTodo(
    {
      tool: {
        transform: async (fn) => {
          fn({ get: () => undefined, add: () => added++ });
          return { dispose: async () => {} };
        },
      },
    },
    f.root,
  );
  assert.equal(added, 0);
  await cleanup();
});

test("structured additions and exact replacements preserve unrelated/manual/legacy text in code", () => {
  const before =
    "# Todo\n\n## [x] Ручная запись\n<!-- todo:manual -->\nОбращений: 4 · Приоритет: 4\n\nСтарая цель.\n\n## Legacy\n  custom layout, unchanged\n";
  const draft = {
    id: "new-note",
    title: "Проверить Kitty",
    summary: "Проверить настройку A < B & C.",
    goal: "Выяснить причину.",
    returnWhen: "При настройке.",
    notes: "Контекст:\n```nix\nmodules = [\n  ./home/modules/kitty\n```",
  };
  const added = applyNoteChanges(before, { add: [draft] });
  assert.ok(added.startsWith(before));
  assert.match(
    added,
    /## \[ \] 3\. Проверить Kitty\n\n<details>\n<summary>Проверить настройку A &lt; B &amp; C\.<\/summary>/,
  );
  assert.match(
    added,
    /  ```nix\n  modules = \[\n    \.\/home\/modules\/kitty\n  ```/,
  );
  assert.equal((added.match(/<details>/g) ?? []).length, 1);
  assert.equal((added.match(/<\/details>/g) ?? []).length, 1);
  assert.equal(applyNoteChanges(before, {}), before);
  assert.equal(
    applyNoteChanges(before, {
      replace: [{ id: "manual", before: "Старая цель.", after: "Новая цель." }],
    }),
    before.replace("Старая цель.", "Новая цель."),
  );
  assert.throws(
    () => applyNoteChanges(added, { add: [draft] }),
    /already exists/,
  );
  assert.throws(
    () =>
      applyNoteChanges(before, {
        add: [{ ...draft, summary: "bad\nsummary" }],
      }),
    /plain text/,
  );
  assert.throws(
    () =>
      applyNoteChanges(before, { add: [{ ...draft, notes: "</details>" }] }),
    /plain text/,
  );
  for (const edit of [
    { id: "missing", before: "Старая цель.", after: "new" },
    { id: "manual", before: "not found", after: "new" },
    { id: "manual", before: "Старая цель.", after: "\n## bad\n" },
    { id: "manual", before: "Обращений: 4", after: "Обращений: 5" },
  ])
    assert.throws(() => applyNoteChanges(before, { replace: [edit] }));
  for (const invalid of ["\0", "\x1b", "\r", "\x7f", "\uFFFD"]) {
    assert.throws(
      () =>
        applyNoteChanges(before, {
          replace: [{ id: "manual", before: "Старая цель.", after: invalid }],
        }),
      /plain UTF-8 text/,
    );
  }
  assert.throws(
    () =>
      applyNoteChanges(before.replace("Старая цель.", "same same"), {
        replace: [{ id: "manual", before: "same", after: "new" }],
      }),
    /exactly once/,
  );
});

test("new note numbers start at one, continue after manual gaps and preserve existing marks/layout", () => {
  const draft = (id) => ({
    id,
    title: id,
    summary: "Summary.",
    goal: "Goal.",
    returnWhen: "Later.",
  });
  const first = applyNoteChanges("", { add: [draft("one"), draft("two")] });
  assert.deepEqual(
    [...first.matchAll(/^## (.+)$/gm)].map((match) => match[1]),
    ["[ ] 1. one", "[ ] 2. two"],
  );
  const manual =
    "# Todo\n\n## [x] 9. Finished\n<!-- todo:old -->\nManual text.\n\n## Legacy\n";
  const added = applyNoteChanges(manual, {
    add: [draft("ten"), draft("eleven")],
  });
  assert.ok(added.startsWith(manual));
  assert.match(added, /^## \[ \] 10\. ten$/m);
  assert.match(added, /^## \[ \] 11\. eleven$/m);
  assert.equal(applyNoteChanges(added, {}), added);
  assert.throws(
    () =>
      applyNoteChanges("## [ ] 9007199254740991. Max\n", {
        add: [draft("overflow")],
      }),
    /safe integer/,
  );
});

test("structured proposals are merged, compared, counted and committed without a model copying the file", async (t) => {
  const f = await fixture(t);
  const before =
    "# Todo\n\n## [x] Existing\n<!-- todo:existing -->\nОбращений: 4 · Приоритет: 4\n\nManual layout.\n\n## Legacy\n<!-- todo:legacy -->\nNo counter, keep this layout.\n";
  await writeFile(f.file, before);
  f.git("add", "todo.md");
  f.git("commit", "-qm", "add manual note");
  const p = await plugin(f);
  const changes = {
    add: [
      {
        id: "structured",
        title: "Проверить настройку",
        summary: "Выяснить, как работает настройка.",
        goal: "Проверить поведение.",
        returnWhen: "При настройке.",
      },
    ],
  };
  assert.equal(
    (await p.propose({ content: undefined, changes })).status,
    "saved",
  );
  const saved = await readFile(f.file, "utf8");
  assert.ok(saved.startsWith(before));
  assert.match(saved, /Обращений: 1 · Приоритет: 1/);
  assert.doesNotMatch(
    p.forms
      .flatMap((form) => form.questions.map((question) => question.question))
      .join("\n"),
    /Manual layout/,
  );
  assert.equal(
    (await p.propose({ content: undefined, revisited: ["existing"] })).status,
    "saved",
  );
  assert.match(
    await readFile(f.file, "utf8"),
    /## \[x\] Existing\n<!-- todo:existing;last:[a-f0-9]+ -->\nОбращений: 5 · Приоритет: 5/,
  );
  assert.equal(
    (await p.propose({ content: undefined, changes })).status,
    "invalid",
  );
  assert.equal((await p.propose({ changes })).status, "invalid"); // Ambiguous full file + structured delta.
  assert.equal(f.git("rev-list", "--count", "HEAD"), "3");
});

test("one native multi-question form requires explicit final consent and respects page feedback", async (t) => {
  for (const mode of ["missing-final", "feedback", "malformed", "decline"]) {
    const f = await fixture(t, false);
    const p = await plugin(f, (input) => {
      const answers = input.questions.map(() => []);
      if (mode === "malformed") return [[YES]];
      if (mode !== "missing-final")
        answers[answers.length - 1] = [mode === "decline" ? NO : YES];
      if (mode === "feedback") answers[0] = ["Перепиши эту заметку"];
      return answers;
    });
    assert.equal(
      (await p.propose()).status,
      mode === "decline" ? "declined" : "revise",
    );
    assert.equal(p.forms.length, 1);
    assert.equal(p.forms[0].questions.length, 2);
    await assert.rejects(access(f.root));
  }
  const f = await fixture(t);
  const p = await plugin(f, (input) =>
    input.questions.map((question) =>
      question.header === "Todo decision" ? [consent(input)] : [],
    ),
  );
  // Native Tab/arrow navigation does not have to answer every review page.
  assert.equal((await p.propose()).status, "saved");
});

test("approval presents readable changes with English controls and commits only approved content", async (t) => {
  const f = await fixture(t);
  const p = await plugin(f);
  const result = await p.propose();
  assert.equal(result.status, "saved", JSON.stringify(result));
  assert.equal(f.git("show", "HEAD:todo.md"), "# Todo\n\n- Test device");
  assert.equal(f.git("status", "--porcelain"), "");
  assert.equal(f.git("log", "-1", "--format=%s"), "add device test note");
  const form = p.forms.at(-1).questions.at(-1);
  assert.equal(form.header, "Todo decision");
  assert.deepEqual(
    form.options.map((option) => option.label),
    [NO],
  );
  const review = p.forms
    .flatMap((input) => input.questions.map((question) => question.question))
    .join("\n");
  assert.match(review, /Add\n# Todo\n\n- Test device/);
  assert.match(review, /Сохранить идею проверки устройства/);
  assert.doesNotMatch(review, /@@|--- todo|\+\+\+|Manual changes/);
  assert.ok(
    p.permissions.some((p) => p.action === "edit" && p.agent === "build"),
  );
});

test("confirmation shows only affected notes and lines, hides internal hashes, and never truncates", async (t) => {
  const f = await fixture(t);
  const p = await plugin(f, NO);
  const block = (id, title, goal) =>
    `## ${title}\n<!-- todo:${id} -->\nОбращений: 1 · Приоритет: 1\n\n- Цель:\n  ${goal}\n- Заметки:\n  Не менять.\n`;
  const unchanged = block(
    "untouched",
    "Не трогать",
    "Секретная неизменённая цель.",
  );
  const before =
    "# Todo\n\n" + block("idea", "Идея", "Старая цель.") + unchanged;
  await writeFile(f.file, before);
  f.git("add", "todo.md");
  f.git("commit", "-qm", "add fixture");
  const after = "# Todo\n\n" + block("idea", "Идея", "Новая цель.") + unchanged;
  await p.propose({ content: after });
  const question = p.forms
    .flatMap((input) => input.questions.map((question) => question.question))
    .join("\n");
  assert.match(question, /Update\nИдея/);
  assert.match(question, /Before:\nСтарая цель\./);
  assert.match(question, /After:\nНовая цель\./);
  assert.doesNotMatch(
    question,
    /Секретная|todo:|last:|@@|Manual changes|^# Todo$/m,
  );
  const manyLines = Array.from({ length: 50 }, (_, i) => `  Строка ${i}`).join(
    "\n",
  );
  const added = await noteReview(
    "# Todo\n",
    "# Todo\n\n" + block("new", "Новая", manyLines),
    f.store.preview,
  );
  assert.match(added.notes[0].text, /Строка 49/);
  const removed = await noteReview(
    before,
    "# Todo\n\n" + unchanged,
    f.store.preview,
  );
  assert.equal(removed.notes.length, 1);
  assert.match(removed.notes[0].text, /Remove\nИдея/);
  assert.doesNotMatch(removed.notes[0].text, /Не трогать|Секретная/);
  const renamed = await noteReview(
    before,
    before.replace("## Идея", "## Другая"),
    f.store.preview,
  );
  assert.match(renamed.notes[0].text, /Before:\nИдея/);
  assert.match(renamed.notes[0].text, /After:\nДругая/);
  const reordered = await noteReview(
    before,
    "# Todo\n\n" + unchanged + block("idea", "Идея", "Старая цель."),
    f.store.preview,
  );
  assert.equal(reordered.notes.length, 0);
  assert.match(reordered.order, /Reorder:/);
  assert.match(reordered.order, /Не трогать → Идея/);
  assert.doesNotMatch(reordered.order, /Секретная/);
});

test("change presentation preserves diff-looking note lines", () => {
  const rendered = describeChanges(
    "--- before\n+++ after\n@@ -1 +1 @@\n--- note text\n+++ note text\n",
  );
  assert.equal(rendered, "Before:\n-- note text\n\nAfter:\n++ note text");
});

test("one complete record per note, without wrappers or text loss, including Unicode and code", async () => {
  const text =
    "Русская строка 界 👩🏽‍💻 ".repeat(80) + "/" + "x".repeat(200) + "\nLAST LINE";
  const source =
    "# Todo\n\n" +
    Array.from(
      { length: 8 },
      (_, i) =>
        `## [ ] Note ${i}\n<details>\n<summary>Useful summary ${i}.</summary>\n\n<!-- todo:note-${i} -->\n${i === 3 ? text : `Goal ${i}.`}\n</details>\n`,
    ).join("\n");
  const review = await noteReview("# Todo\n", source, async () => "");
  assert.equal(review.notes.length, 8);
  assert.deepEqual(
    review.notes.map((note) => note.id),
    Array.from({ length: 8 }, (_, i) => `note-${i}`),
  );
  assert.ok(review.notes[3].text.includes(text));
  assert.ok(
    review.notes.every(
      (note) => !/<\/?details>|<\/?summary>|todo:/.test(note.text),
    ),
  );
  const code =
    "```html\n<details>\n<summary>Literal example</summary>\n<!-- todo:literal -->\n</details>\n```";
  assert.equal(
    cleanNote(
      `<details>\n<summary>Readable summary.</summary>\n${code}\n</details>`,
    ),
    `Readable summary.\n${code}`,
  );
});

test("review transport validates field identity, scopes every answer, and rejects old or missing consent", () => {
  const notes = [
    { id: "first", title: "First", text: "Full first note" },
    { id: "second", title: "Second", text: "Full second note" },
  ];
  const token = "a".repeat(64);
  const questions = reviewQuestions(notes, "One final review", token);
  const form = {
    metadata: { kind: "question" },
    fields: questions.map((q, i) => ({
      key: `q${i}`,
      type: "string",
      description: q.question,
    })),
  };
  assert.equal(readReview(form).notes[1].id, "second");
  assert.equal(
    readReview({ ...form, metadata: { kind: "unrelated" } }),
    undefined,
  );
  assert.equal(
    readReview({ ...form, fields: [...form.fields].reverse() }),
    undefined,
  );
  assert.equal(
    readReview({ ...form, fields: form.fields.slice(1) }),
    undefined,
  );
  for (const final of ["Submit", "Save all", "", SUBMIT + "b".repeat(64)])
    assert.equal(
      reviewAnswer(notes, token, [[], [], [final]]).status,
      "revise",
    );
  const result = reviewAnswer(notes, token, [
    [],
    ["Rewrite just this note"],
    [SUBMIT + token],
  ]);
  assert.equal(result.status, "revise");
  assert.deepEqual(result.feedback, [
    { id: "second", title: "Second", feedback: "Rewrite just this note" },
  ]);
  assert.equal(result.batchFeedback, "");
  assert.equal(
    reviewAnswer(notes, token, [[], [], [SUBMIT + token]]).status,
    "approved",
  );
  assert.equal(
    reviewAnswer(notes, token, [[], [], ["Reject"]]).status,
    "declined",
  );
  assert.equal(
    reviewAnswer(notes, token, [[], [], ["Global comment"]]).batchFeedback,
    "Global comment",
  );
  for (const answers of [
    [],
    [[SUBMIT + token]],
    [[], [], [SUBMIT + token, "extra"]],
    [[], "bad", [SUBMIT + token]],
  ])
    assert.equal(reviewAnswer(notes, token, answers).status, "revise");
});

test("scoped revisions preserve other drafts, need fresh approval, and never save feedback as note text", async (t) => {
  const f = await fixture(t);
  const changes = {
    add: ["first", "second"].map((id) => ({
      id,
      title: id,
      summary: `Summary for ${id}.`,
      goal: `Goal for ${id}`,
      returnWhen: "Review",
    })),
  };
  const p = await plugin(f, (input) => [
    ["Shorten first only"],
    [],
    [consent(input)],
  ]);
  const result = await p.propose({ content: undefined, changes });
  assert.equal(result.status, "revise");
  assert.deepEqual(result.feedback, [
    { id: "first", title: "[ ] 1. first", feedback: "Shorten first only" },
  ]);
  assert.deepEqual(result.draft.changes, changes);
  await assert.rejects(access(f.file));
  const revised = structuredClone(result.draft);
  revised.changes.add[0].goal = "Short goal";
  const q = await plugin(f, NO);
  assert.equal(
    (await q.propose({ ...revised, content: undefined })).status,
    "declined",
  );
  await assert.rejects(access(f.file));
  const r = await plugin(f);
  assert.equal(
    (await r.propose({ ...revised, content: undefined })).status,
    "saved",
  );
  const saved = await readFile(f.file, "utf8");
  assert.match(saved, /Goal for second/);
  assert.match(saved, /Short goal/);
  assert.doesNotMatch(saved, /Shorten first only|Goal for first/);
  assert.equal(f.git("rev-list", "--count", "HEAD"), "1");
});

test("batch review is one native form with one tab per note; final Submit commits every note exactly once", async (t) => {
  const f = await fixture(t);
  const original =
    "# Todo\n\n## Existing\n<!-- todo:existing -->\nОбращений: 4 · Приоритет: 4\n\nUntouched.\n";
  await writeFile(f.file, original);
  f.git("add", "todo.md");
  f.git("commit", "-qm", "add existing note");
  const head = f.git("rev-parse", "HEAD");
  const content =
    original +
    Array.from(
      { length: 8 },
      (_, i) =>
        `\n## [ ] Note ${i}\n<details>\n<summary>Review task ${i}.</summary>\n\n<!-- todo:note-${i} -->\n\n${i === 3 ? "Long Unicode note 👩🏽‍💻 Русский текст. ".repeat(50) : `Goal ${i}.`}\n</details>\n`,
    ).join("");
  const p = await plugin(f, YES, async () => {
    assert.equal(await readFile(f.file, "utf8"), original);
    assert.equal(f.git("rev-parse", "HEAD"), head);
    assert.equal(f.git("status", "--porcelain"), "");
  });
  assert.equal((await p.propose({ content })).status, "saved");
  assert.equal(f.git("rev-list", "--count", "HEAD"), "2");
  const saved = await readFile(f.file, "utf8");
  assert.ok(saved.startsWith(original));
  assert.equal((saved.match(/Обращений: 1 · Приоритет: 1/g) ?? []).length, 8);
  const review = p.forms
    .flatMap((input) => input.questions.map((question) => question.question))
    .join("\n");
  for (let i = 0; i < 8; i++) assert.match(review, new RegExp(`Note ${i}`));
  assert.equal(p.forms.length, 1);
  assert.equal(p.forms[0].questions.length, 9);
  assert.equal(p.forms[0].questions.at(-1).header, "Todo decision");
  assert.ok(
    p.forms[0].questions
      .slice(0, -1)
      .every((question) => question.options.length === 0),
  );
});

test("cancel, Escape, custom feedback and session abort during review cancel the entire batch", async (t) => {
  const content =
    "# Todo\n\n## [ ] Long\n<!-- todo:long -->\n\n" +
    "Page content.\n".repeat(40);
  for (const action of [
    "Cancel",
    "feedback",
    "Save all",
    "escape",
    "abort",
    "error",
  ]) {
    const f = await fixture(t, false);
    const abort = new AbortController();
    const failure = new Error("not a dismissal");
    const p = await plugin(f, (input) => {
      if (action === "escape") throw { _tag: "QuestionTool.CancelledError" };
      if (action === "abort") {
        abort.abort();
        return "Continue";
      }
      if (action === "error") throw failure;
      return input.questions.map((question, index) => [
        index === 0
          ? action
          : question.header === "Todo decision"
            ? consent(input)
            : "",
      ]);
    });
    p.context.signal = abort.signal;
    if (action === "error")
      await assert.rejects(
        p.propose({ content }),
        (error) => error === failure,
      );
    else {
      const result = await p.propose({ content });
      assert.equal(
        result.status,
        action === "escape"
          ? "declined"
          : action === "abort"
            ? "cancelled"
            : "revise",
      );
    }
    assert.equal(p.forms.length, 1);
    await assert.rejects(access(f.root));
  }
});

test("manual edits between review pages invalidate the whole proposal before final approval", async (t) => {
  const f = await fixture(t);
  const p = await plugin(f, YES, async () =>
    writeFile(f.file, "manual edit\n"),
  );
  const content =
    "# Todo\n\n## Long\n<!-- todo:long -->\n\n" + "Review line.\n".repeat(30);
  assert.equal((await p.propose({ content })).status, "stale");
  assert.equal(p.forms.length, 1);
  assert.equal(await readFile(f.file, "utf8"), "manual edit\n");
  assert.equal((await f.store.snapshot()).head, "");
});

test("native Escape is a completed decline; other failures and permission denials propagate", async (t) => {
  const f = await fixture(t, false);
  const dismissed = Object.assign(
    new Error("The user dismissed this question"),
    { _tag: "QuestionTool.CancelledError" },
  );
  const p = await plugin(f, YES, () => {
    throw dismissed;
  });
  assert.deepEqual(await p.propose(), {
    status: "declined",
    dismissed: true,
    message: "Nothing saved. Do not reopen confirmation unless the user asks.",
  });
  await assert.rejects(access(f.root));
  for (const error of [
    new Error("The user dismissed this question"),
    { _tag: "Permission.DeclinedError" },
    { name: "AbortError" },
  ]) {
    const q = await plugin(f, YES, () => {
      throw error;
    });
    await assert.rejects(q.propose(), (caught) => caught === error);
    await assert.rejects(access(f.root));
  }
  const next = await plugin(f, NO);
  assert.equal((await next.propose()).status, "declined");
});

test("no and free-form revision never write or initialize Git", async (t) => {
  for (const [answer, status] of [
    [NO, "declined"],
    ["Переформулируй короче", "revise"],
  ]) {
    const f = await fixture(t, false);
    const p = await plugin(f, answer);
    const result = await p.propose();
    assert.equal(result.status, status);
    if (status === "revise") assert.equal(result.batchFeedback, answer);
    await assert.rejects(access(f.root));
  }
});

test("stale before form or changes during form need new approval", async (t) => {
  const f = await fixture(t);
  await writeFile(f.file, "manual\n");
  const p = await plugin(f);
  const old = await p.read();
  await writeFile(f.file, "new manual\n");
  assert.equal((await p.propose({ base: old.fingerprint })).status, "stale");
  assert.equal(p.forms.length, 0);
  const q = await plugin(f, YES, () => writeFile(f.file, "edited in Neovim\n"));
  assert.equal((await q.propose()).status, "stale");
  assert.equal(await readFile(f.file, "utf8"), "edited in Neovim\n");
  assert.equal((await f.store.snapshot()).head, "");
});

test("manual staged and unstaged changes are shown and preserved by proposed merge", async (t) => {
  const f = await fixture(t);
  const p = await plugin(f);
  assert.equal((await p.propose({ content: "base\n" })).status, "saved");
  const reviewed = p.forms.length;
  await writeFile(f.file, "base\nstaged manual\n");
  f.git("add", "todo.md");
  await writeFile(f.file, "base\nstaged manual\nunstaged manual\n");
  const content = "base\nstaged manual\nunstaged manual\nnew idea\n";
  assert.equal((await p.propose({ content })).status, "saved");
  const question = p.forms
    .slice(reviewed)
    .flatMap((input) => input.questions.map((question) => question.question))
    .join("\n");
  assert.match(question, /Manual changes included/);
  assert.match(
    JSON.parse(p.forms.at(-1).questions.at(-1).question.slice(REVIEW.length))
      .summary,
    /After:\nstaged manual/,
  );
  assert.match(question, /After:\nunstaged manual/);
  assert.doesNotMatch(question, /@@|--- a\/|\+\+\+ b\//);
  assert.equal(await readFile(f.file, "utf8"), content);
  assert.equal(f.git("status", "--porcelain"), "");
  assert.equal((await p.propose({ content })).status, "unchanged");
  assert.equal(
    p.forms.filter((input) => input.questions.at(-1).header === "Todo decision")
      .length,
    2,
  );
});

test("Plan edit denial occurs before form or write", async (t) => {
  const f = await fixture(t);
  const p = await plugin(f, YES, undefined, true);
  p.context.agent = "plan";
  await assert.rejects(p.propose(), /Plan denied/);
  assert.equal(p.forms.length, 0);
  await assert.rejects(access(f.file));
});

test("cancelled signal after approval does not write", async (t) => {
  const f = await fixture(t);
  const abort = new AbortController();
  const p = await plugin(f, YES, async () => abort.abort());
  p.context.signal = abort.signal;
  assert.equal((await p.propose()).status, "cancelled");
  await assert.rejects(access(f.file));
});

test("missing Git identity fails before replacing manual content", async (t) => {
  const f = await fixture(t);
  await writeFile(f.file, "manual idea\n");
  f.git("config", "user.name", "");
  f.git("config", "user.email", "");
  const p = await plugin(f);
  const result = await p.propose();
  assert.equal(result.status, "error");
  assert.equal(result.written, false);
  assert.equal(await readFile(f.file, "utf8"), "manual idea\n");
  assert.equal((await f.store.snapshot()).head, "");
  await assert.rejects(access(join(f.root, ".git/index.lock")));
  await assert.rejects(access(join(f.root, ".git/agent-todo.lock")));
});

test("concurrent saves serialize without overwriting another proposal", async (t) => {
  const f = await fixture(t);
  const { fingerprint } = await f.store.snapshot();
  const results = await Promise.all([
    f.store.save(fingerprint, "first\n", "add first idea", signal()),
    f.store.save(fingerprint, "second\n", "add second idea", signal()),
  ]);
  assert.equal(
    results.filter((r) => r.status === "saved").length,
    1,
    JSON.stringify(results),
  );
  assert.ok(
    results.every((r) => ["saved", "stale", "busy"].includes(r.status)),
    JSON.stringify(results),
  );
  assert.equal(f.git("rev-list", "--count", "HEAD"), "1");
  assert.equal(f.git("status", "--porcelain"), "");
});

test("native index lock and unrelated files are never overwritten", async (t) => {
  const f = await fixture(t);
  const p = await plugin(f);
  await writeFile(join(f.root, ".git/index.lock"), "foreign lock");
  assert.equal((await p.propose()).status, "error");
  assert.equal(
    await readFile(join(f.root, ".git/index.lock"), "utf8"),
    "foreign lock",
  );
  await assert.rejects(access(f.file));
  await rm(join(f.root, ".git/index.lock"));
  await writeFile(join(f.root, "other.txt"), "unrelated");
  await assert.rejects(p.read(), /other changed files/);
  assert.equal(await readFile(join(f.root, "other.txt"), "utf8"), "unrelated");
});

test("restart/reload creates no durable proposals or implicit approval", async (t) => {
  const f = await fixture(t);
  const p = await plugin(f, NO);
  await p.propose();
  await p.cleanup();
  const next = await plugin(f, YES);
  assert.equal((await next.propose()).status, "saved");
  assert.equal(
    next.forms.filter(
      (input) => input.questions.at(-1).header === "Todo decision",
    ).length,
    1,
  );
});

test("symlinks, oversize text, conflicts and malformed proposals fail closed", async (t) => {
  const f = await fixture(t);
  const target = join(f.root, "../private");
  await writeFile(target, "secret");
  await symlink(target, f.file);
  await assert.rejects(f.store.snapshot(), /regular/);
  await rm(f.file);
  await writeFile(f.file, "x".repeat(32769));
  await assert.rejects(f.store.snapshot(), /32 KiB/);
  await rm(f.file);
  const p = await plugin(f);
  assert.equal(
    (await p.propose({ content: "x".repeat(32769) })).status,
    "invalid",
  );
  assert.equal(
    (await p.propose({ message: "bad\nsubject" })).status,
    "invalid",
  );
  await writeFile(join(f.root, ".git/MERGE_HEAD"), "fixture");
  await assert.rejects(f.store.snapshot(), /existing Git operation/);
  assert.equal(p.forms.length, 0);
});

test("heading blocks start at one; priority grows on returns, deduplicated per user turn", async (t) => {
  const f = await fixture(t);
  const p = await plugin(f);
  const content =
    "# Todo\n\n## Проверить сон\n<!-- todo:suspend -->\n\n- Цель:\n  Проверить прошивку.\n";
  assert.equal((await p.propose({ content })).status, "saved");
  assert.match(await readFile(f.file, "utf8"), /Обращений: 1 · Приоритет: 1/);
  // Same request is not another return, even after another tool call or reload.
  assert.equal(
    (await p.propose({ content, revisited: ["suspend"] })).status,
    "unchanged",
  );
  p.ctx.session.context = async () => [
    { type: "user", id: "request-2" },
    { type: "assistant", id: "message" },
  ];
  assert.equal(
    (await p.propose({ content, revisited: ["suspend"] })).status,
    "saved",
  );
  assert.match(await readFile(f.file, "utf8"), /Обращений: 2 · Приоритет: 2/);
  assert.equal(
    (await p.propose({ content, revisited: ["suspend"] })).status,
    "unchanged",
  );
  p.ctx.session.context = async () => [
    { type: "user", id: "request-3" },
    { type: "assistant", id: "message" },
  ];
  assert.equal(
    (await p.propose({ content, revisited: ["suspend"] })).status,
    "saved",
  );
  assert.match(await readFile(f.file, "utf8"), /Обращений: 3 · Приоритет: 3/);
});

test("checkbox headings and closed spoilers preserve marks, counters and legacy notes", async (t) => {
  const f = await fixture(t);
  const p = await plugin(f);
  const legacy =
    "## Старая заметка\n<!-- todo:legacy -->\nОбращений: 3 · Приоритет: 3\n\n- Заметки:\n  Не менять формат.\n";
  const content =
    "# Todo\n\n## [ ] Проверить сон\n\n<details>\n<summary>Проверить suspend/resume на текущей прошивке.</summary>\n\n<!-- todo:suspend -->\n\n- Цель:\n  Проверить прошивку.\n\n</details>\n\n" +
    legacy;
  assert.equal((await p.propose({ content })).status, "saved");
  const saved = await readFile(f.file, "utf8");
  assert.match(saved, /^## \[ \] Проверить сон$/m);
  assert.match(
    saved,
    /<summary>Проверить suspend\/resume на текущей прошивке\.<\/summary>/,
  );
  const spoiler = saved.slice(
    saved.indexOf("<details>"),
    saved.indexOf("</details>"),
  );
  assert.match(
    spoiler,
    /<!-- todo:suspend;last:[a-f0-9]{64} -->\nОбращений: 1 · Приоритет: 1/,
  );
  assert.match(spoiler, /- Цель:\n  Проверить прошивку\./);
  assert.doesNotMatch(saved, /<details\s+open/);
  // A manually checked heading survives another confirmed visit, with a mixed
  // legacy layout untouched and exactly one counter still inside the spoiler.
  const checked = saved.replace("## [ ]", "## [x]");
  await writeFile(f.file, checked);
  p.ctx.session.context = async () => [
    { type: "user", id: "request-2" },
    { type: "assistant", id: "message" },
  ];
  assert.equal(
    (await p.propose({ content: checked, revisited: ["suspend"] })).status,
    "saved",
  );
  const updated = await readFile(f.file, "utf8");
  assert.match(updated, /^## \[x\] Проверить сон$/m);
  assert.match(
    updated,
    /<summary>Проверить suspend\/resume на текущей прошивке\.<\/summary>/,
  );
  assert.match(
    updated.slice(updated.indexOf("<details>"), updated.indexOf("</details>")),
    /Обращений: 2 · Приоритет: 2/,
  );
  assert.equal(
    updated.slice(updated.indexOf("## Старая заметка")),
    saved.slice(saved.indexOf("## Старая заметка")),
  );
  assert.equal((updated.match(/Обращений: 2 · Приоритет: 2/g) ?? []).length, 1);
  assert.match(
    p.forms
      .flatMap((input) => input.questions.map((question) => question.question))
      .join("\n"),
    /Update\n\[x\] Проверить сон/,
  );
  const rules = await readFile(
    new URL("../config/decision-support.md", import.meta.url),
    "utf8",
  );
  assert.match(rules, /## \[ \] N\. Русский заголовок/);
  assert.match(rules, /<summary>Краткое резюме задачи<\/summary>/);
  assert.match(rules, /not a generic label or a repetition of the title/);
  assert.match(
    p.tools.get("agent_todo_propose").input.properties.changes.properties.add
      .items.properties.title.description,
    /Short descriptive Russian title/,
  );
  assert.match(
    p.tools.get("agent_todo_propose").input.properties.changes.properties.add
      .items.properties.summary.description,
    /One concise meaningful Russian sentence/,
  );
});

test("counter cannot be changed by model; missing context does not invent a return", () => {
  const a = "a".repeat(64),
    b = "b".repeat(64);
  const before = `## Идея\n<!-- todo:idea;last:${a} -->\nОбращений: 4 · Приоритет: 4\n\n- Заметки:\n  Текст.\n`;
  const proposed = before.replace(
    "Обращений: 4 · Приоритет: 4",
    "Обращений: 999 · Приоритет: 999",
  );
  assert.equal(countRevisits(before, proposed, [], b), before);
  assert.match(
    countRevisits(before, proposed, ["idea"], b),
    /Обращений: 5 · Приоритет: 5/,
  );
  assert.throws(
    () => countRevisits(before, proposed, ["idea"], ""),
    /Cannot attribute/,
  );
  assert.throws(
    () => countRevisits(before, proposed, ["unknown"], b),
    /Unknown/,
  );
  assert.throws(() => countRevisits("", before + before, [], b), /unique/);
});

test("personal reminder remains exact Russian text with only the extra comma removed", async () => {
  const skill = await readFile(
    new URL("../skills/decision-check/SKILL.md", import.meta.url),
    "utf8",
  );
  const quote = [
    "Решение существует, оно достаточно хорошее, но сознание не разрешает прекратить поиск, потому что ещё не доказано, что лучшего не существует.",
    "А вот это доказательство зачастую получить невозможно.",
    "Мне кажется, именно здесь ты можешь снять с себя больше всего когнитивной нагрузки. Не понижая требований к качеству решений — а перестав требовать доказательства их абсолютной оптимальности.",
  ].join("\n");
  assert.equal(skill.slice(skill.indexOf("Решение существует")).trim(), quote);
  const rules = await readFile(
    new URL("../config/decision-support.md", import.meta.url),
    "utf8",
  );
  assert.ok(
    !rules.includes("Решение существует"),
    "quote is on-demand, not ambient",
  );
});
