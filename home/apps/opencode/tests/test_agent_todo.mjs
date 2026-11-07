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
  organizeTodo,
} = await import("../plugins/agent-todo.ts");
const { reviewAnswer, reviewQuestions, readReview, SUBMIT, REVIEW } =
  await import("../plugins/agent-todo-review.ts");

const YES = "Submit";
const NO = "Reject";
const consent = (input) =>
  SUBMIT +
  JSON.parse(input.questions.at(-1).question.slice(REVIEW.length)).token;
const signal = () => new AbortController().signal;
const withoutStats = (text) =>
  text.replace(/\n<!-- todo-stats -->\nTotal:[^\n]*\n/, "");
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
            reason: "Save device test idea.",
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
  assert.ok(withoutStats(saved).startsWith(before));
  assert.match(saved, /Visits: 1 · Priority: Normal/);
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
    /## \[x\] Existing\n<!-- todo:existing;last:[a-f0-9]+ -->\nVisits: 5 · Priority: Normal/,
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
  assert.match(review, /Save device test idea/);
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
  assert.match(question, /Before:\n- Цель:\n  Старая цель\./);
  assert.match(question, /After:\n- Goal:\n  Новая цель\./);
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
  assert.ok(withoutStats(saved).startsWith(original));
  assert.equal((saved.match(/Visits: 1 · Priority: Normal/g) ?? []).length, 8);
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

test("128 KiB capacity accepts existing larger notes and structured additions without rewriting them", async (t) => {
  const f = await fixture(t);
  const limitText = "x".repeat(131072);
  await writeFile(f.file, limitText);
  assert.equal(
    (await f.store.snapshot()).content,
    limitText,
    "exact byte limit is readable",
  );
  const existing =
    "# Todo\n\n## Existing\n<!-- todo:existing -->\n" +
    "я".repeat(20000) +
    "\n";
  await writeFile(f.file, existing);
  const p = await plugin(f);
  assert.equal(
    (
      await p.propose({
        content: undefined,
        changes: {
          add: [
            {
              id: "larger-file",
              title: "Larger todo",
              summary: "Save a new note without rewriting the existing text.",
              goal: "Preserve manual content.",
              returnWhen: "Testing capacity.",
            },
          ],
        },
      })
    ).status,
    "saved",
  );
  const saved = await readFile(f.file, "utf8");
  assert.ok(Buffer.byteLength(saved) > 32768);
  assert.ok(
    withoutStats(saved).startsWith(existing),
    "unrelated note remains byte-identical",
  );
  assert.equal(p.forms.length, 1, "larger files still require native consent");
});

test("symlinks, oversize text, conflicts and malformed proposals fail closed", async (t) => {
  const f = await fixture(t);
  const target = join(f.root, "../private");
  await writeFile(target, "secret");
  await symlink(target, f.file);
  await assert.rejects(f.store.snapshot(), /regular/);
  await rm(f.file);
  await writeFile(f.file, "x".repeat(131073));
  await assert.rejects(f.store.snapshot(), /128 KiB/);
  await rm(f.file);
  const p = await plugin(f);
  assert.equal(
    (await p.propose({ content: "я".repeat(65537) })).status,
    "invalid",
  );
  const formatted = await p.propose({
    content:
      "# Todo\n\n## [ ] Capacity\n<!-- todo:capacity -->\n" +
      "x".repeat(130990),
  });
  assert.equal(
    formatted.status,
    "invalid",
    "generated metadata counts toward the byte limit",
  );
  assert.match(formatted.message, /128 KiB/);
  assert.equal(
    (await p.propose({ message: "bad\nsubject" })).status,
    "invalid",
  );
  await writeFile(join(f.root, ".git/MERGE_HEAD"), "fixture");
  await assert.rejects(f.store.snapshot(), /existing Git operation/);
  assert.equal(p.forms.length, 0);
});

test("heading blocks start at one; visits grow independently of priority, deduplicated per user turn", async (t) => {
  const f = await fixture(t);
  const p = await plugin(f);
  const content =
    "# Todo\n\n## Проверить сон\n<!-- todo:suspend -->\n\n- Цель:\n  Проверить прошивку.\n";
  assert.equal((await p.propose({ content })).status, "saved");
  assert.match(await readFile(f.file, "utf8"), /Visits: 1 · Priority: Normal/);
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
  assert.match(await readFile(f.file, "utf8"), /Visits: 2 · Priority: Normal/);
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
  assert.match(await readFile(f.file, "utf8"), /Visits: 3 · Priority: Normal/);
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
    /<!-- todo:suspend;last:[a-f0-9]{64} -->\nVisits: 1 · Priority: Normal/,
  );
  assert.match(spoiler, /- Goal:\n  Проверить прошивку\./);
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
    /Visits: 2 · Priority: Normal/,
  );
  assert.equal(
    updated.slice(updated.indexOf("## Старая заметка")),
    saved.slice(saved.indexOf("## Старая заметка")),
  );
  assert.equal(
    (updated.match(/Visits: 2 · Priority: Normal/g) ?? []).length,
    1,
  );
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
  assert.match(rules, /## \[ \] N\. Short title/);
  assert.match(rules, /<summary>One-sentence task summary<\/summary>/);
  assert.match(rules, /not a generic label or a repetition of the title/);
  assert.match(
    p.tools.get("agent_todo_propose").input.properties.changes.properties.add
      .items.properties.title.description,
    /Short descriptive title, English by default/,
  );
  assert.match(
    p.tools.get("agent_todo_propose").input.properties.changes.properties.add
      .items.properties.summary.description,
    /One concise meaningful sentence, English by default/,
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
  assert.equal(
    countRevisits(before, proposed, [], b),
    before.replace(
      "Обращений: 4 · Приоритет: 4",
      "Visits: 4 · Priority: Normal",
    ),
  );
  assert.match(
    countRevisits(before, proposed, ["idea"], b),
    /Visits: 5 · Priority: Normal/,
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

const record = (
  id,
  {
    status = "Todo",
    priority = "Normal",
    visits = 1,
    created = "Unknown",
    completed,
    body = "Unchanged content.",
  } = {},
) =>
  `## [${status === "Done" ? "x" : " "}] ${id}\n<!-- todo:${id} -->\nVisits: ${visits} · Priority: ${priority}\nStatus: ${status}\nCreated: ${created}\n${completed ? `Completed: ${completed}\n` : ""}\n${body}\n\n`;
const ids = (text) =>
  [...text.matchAll(/^<!-- todo:([a-z0-9-]+)(?:;last:[a-f0-9]+)? -->$/gm)].map(
    (match) => match[1],
  );

test("explicit stable sort follows status, independent priority, visits, age and completion date", () => {
  const source =
    "# Todo\n\n" +
    [
      record("done-old", {
        status: "Done",
        completed: "2026-01-01T00:00:00Z",
        priority: "High",
        visits: 100,
      }),
      record("todo-low", { priority: "Low", visits: 100 }),
      record("normal-unknown"),
      record("normal-new", { created: "2026-02-01T00:00:00Z" }),
      record("normal-old", { created: "2026-01-01T00:00:00Z" }),
      record("normal-visits", { visits: 2 }),
      record("high-tie-one", { priority: "High" }),
      record("active-low", { status: "In progress", priority: "Low" }),
      record("high-tie-two", { priority: "High" }),
      record("active-high", { status: "In progress", priority: "High" }),
      record("done-unknown", { status: "Done" }),
      record("done-new", { status: "Done", completed: "2026-02-01T00:00:00Z" }),
    ].join("");
  assert.deepEqual(
    ids(organizeTodo(source, source)),
    ids(source),
    "ordinary save must not sort",
  );
  const sorted = organizeTodo(source, source, {}, { sort: true });
  assert.deepEqual(ids(sorted), [
    "active-high",
    "active-low",
    "high-tie-one",
    "high-tie-two",
    "normal-visits",
    "normal-old",
    "normal-new",
    "normal-unknown",
    "todo-low",
    "done-new",
    "done-old",
    "done-unknown",
  ]);
  assert.match(sorted, /Total: 12 · Done: 3 · In progress: 2/);
  assert.equal(
    organizeTodo(sorted, sorted, {}, { sort: true }),
    sorted,
    "sort is idempotent",
  );
});

test("creation, explicit status/priority, reopening and later completion are code-owned", () => {
  const first = "2026-01-01T00:00:00.000Z",
    second = "2026-02-01T00:00:00.000Z";
  const draft = {
    id: "work",
    title: "Work",
    summary: "Do the work.",
    goal: "Finish.",
    returnWhen: "Ready.",
    priority: "High",
  };
  const changes = { add: [draft] };
  const initial = organizeTodo(
    "",
    countRevisits("", applyNoteChanges("", changes), [], "a".repeat(64)),
    changes,
    { now: first },
  );
  assert.match(
    initial,
    /Visits: 1 · Priority: High\nStatus: Todo\nCreated: 2026-01-01/,
  );
  const active = organizeTodo(initial, initial, {
    update: [{ id: "work", status: "In progress" }],
  });
  assert.match(active, /Total: 1 · Done: 0 · In progress: 1/);
  assert.match(active, /## \[ \] 1\. Work/);
  const returned = countRevisits(active, active, ["work"], "b".repeat(64));
  assert.match(returned, /Visits: 2 · Priority: High/);
  const done = organizeTodo(
    active,
    active,
    { update: [{ id: "work", status: "Done" }] },
    { now: first },
  );
  assert.match(done, /## \[x\] 1\. Work/);
  assert.match(done, /Total: 1 · Done: 1 · In progress: 0/);
  assert.ok(done.includes(`Completed: ${first}`));
  assert.equal(organizeTodo(done, done, {}, { now: second }), done);
  const reopened = organizeTodo(done, done, {
    update: [{ id: "work", status: "Todo", priority: "Low" }],
  });
  assert.doesNotMatch(reopened, /^Completed:/m);
  assert.match(reopened, /Priority: Low\nStatus: Todo/);
  const closedAgain = organizeTodo(
    reopened,
    reopened,
    { update: [{ id: "work", status: "Done" }] },
    { now: second },
  );
  assert.ok(closedAgain.includes(`Completed: ${second}`));
  assert.ok(closedAgain.includes(`Created: ${first}`));
  for (const update of [
    { id: "missing", status: "Done" },
    { id: "work" },
    { id: "work", priority: "Urgent" },
  ])
    assert.throws(() => organizeTodo(initial, initial, { update: [update] }));
});

test("manual checkbox completion is observed, never backdated; manual reopen clears Completed", () => {
  const now = "2026-03-01T00:00:00.000Z";
  const committed = "# Todo\n\n" + record("manual");
  const working = committed.replace("## [ ]", "## [x]");
  const observed = organizeTodo(working, working, {}, { committed, now });
  assert.ok(observed.includes(`Completed: ${now} (Observed)`));
  assert.match(observed, /Status: Done/);
  const reopened = observed.replace("## [x]", "## [ ]");
  assert.doesNotMatch(
    organizeTodo(reopened, reopened, {}, { committed: observed }),
    /^Completed:/m,
  );
});

test("legacy migration preserves Russian content, artifact languages, numbering and literal fenced metadata", () => {
  const artifact =
    "```text\n## [x] 999. Не задача\n<!-- todo:literal -->\n<!-- todo-stats -->\nTotal: literal artifact\nОбращений: 77 · Приоритет: 77\nStatus: Done\nCreated: keep this\n- Цель:\nОшибка: исходный текст /some/path\n```";
  const legacy =
    "# Todo\n\n## [ ] 17. Русская задача\n<!-- todo:legacy -->\nОбращений: 4 · Приоритет: 4\n\n- Цель:\n  Русский контент.\n\n" +
    artifact +
    "\n\n## Unmanaged section\nLeave this section alone.\n";
  const output = organizeTodo(legacy, legacy, {}, { sort: true });
  assert.ok(output.includes(artifact));
  assert.match(output, /## \[ \] 17\. Русская задача/);
  assert.match(
    output,
    /Visits: 4 · Priority: Normal\nStatus: Todo\nCreated: Unknown/,
  );
  assert.match(output, /- Goal:\n  Русский контент\./);
  assert.match(output, /Total: 1 · Done: 0 · In progress: 0/);
  assert.ok(
    output.endsWith("## Unmanaged section\nLeave this section alone.\n"),
  );
  assert.ok(cleanNote(output).includes(artifact));
  const added = applyNoteChanges(legacy, {
    add: [
      {
        id: "next",
        title: "Next",
        summary: "Next task.",
        goal: "Next.",
        returnWhen: "Later.",
      },
    ],
  });
  assert.match(added, /## \[ \] 18\. Next/);
  assert.ok(
    countRevisits(legacy, legacy, ["legacy"], "c".repeat(64)).includes(
      artifact,
    ),
  );
});

test("moving an EOF record preserves heading boundaries and unknown sections stay anchored", () => {
  const source =
    "# Todo\n\n" +
    record("low", { priority: "Low" }) +
    "## Other section\nKeep this here.\n\n" +
    record("high", { priority: "High" }).trimEnd();
  const sorted = organizeTodo(source, source, {}, { sort: true });
  assert.deepEqual(
    [...sorted.matchAll(/^## (.+)$/gm)].map((m) => m[1]),
    ["[ ] high", "Other section", "[ ] low"],
  );
  assert.equal(organizeTodo(sorted, sorted, {}, { sort: true }), sorted);
});

test("sorting an EOF spoiler before completed tasks leaves a blank line after details", () => {
  const done = record("done", {
    status: "Done",
    completed: "Unknown",
    body: "<details>\nCompleted.\n</details>",
  });
  for (const ending of ["", "\n", "\n\n", "\n\n\n"]) {
    const todo =
      record("todo", { body: "<details>\nPending.\n</details>" }).trimEnd() +
      ending;
    const source = "# Todo\n\n" + done + todo;
    const sorted = organizeTodo(source, source, {}, { sort: true });
    assert.deepEqual(ids(sorted), ["todo", "done"]);
    assert.ok(
      sorted.includes(
        todo.trimEnd() + (ending.length >= 2 ? ending : "\n\n") + done,
      ),
    );
    assert.equal(organizeTodo(sorted, sorted, {}, { sort: true }), sorted);
  }
});

test("ordinary saves repair missing spoiler separators without changing note contents or order", () => {
  const todo =
    record("todo", { body: "<details>\nPending.\n</details>" }).trimEnd() +
    "\n";
  const done = record("done", {
    status: "Done",
    body: "<details>\nCompleted.\n</details>",
  });
  const source = "# Todo\n\n" + todo + done;
  const output = organizeTodo(source, source);
  assert.equal(withoutStats(output), "# Todo\n\n" + todo + "\n" + done);
  assert.equal(organizeTodo(output, output), output);
});

test("local Git backfill records first appearance and latest closure, labelled as history", async (t) => {
  const f = await fixture(t);
  const commit = async (content, date) => {
    await writeFile(f.file, content);
    f.git("add", "todo.md");
    execFileSync("git", ["commit", "-qm", "fixture event"], {
      cwd: f.root,
      env: { ...process.env, GIT_AUTHOR_DATE: date, GIT_COMMITTER_DATE: date },
    });
  };
  const open =
    "# Todo\n\n## [ ] 7. Legacy\n<!-- todo:legacy -->\nОбращений: 2 · Приоритет: 2\n\nРусский контент.\n";
  const closed = open.replace("[ ]", "[x]");
  await commit(open, "2026-01-01T00:00:00Z");
  await commit(closed, "2026-02-01T00:00:00Z");
  await commit(open, "2026-03-01T00:00:00Z");
  await commit(closed, "2026-04-01T00:00:00Z");
  const history = await f.store.history(f.git("rev-parse", "HEAD"));
  assert.deepEqual(history.get("legacy"), {
    created: "2026-01-01T00:00:00.000Z",
    completed: "2026-04-01T00:00:00.000Z",
    done: true,
  });
  const output = organizeTodo(closed, closed, {}, { sort: true, history });
  assert.match(output, /Created: 2026-01-01T00:00:00.000Z \(Git history\)/);
  assert.match(output, /Completed: 2026-04-01T00:00:00.000Z \(Git history\)/);
  assert.ok(output.includes("Русский контент."));
});

test("sorting uses existing consent, preserves feedback drafts, and never writes on decline", async (t) => {
  const f = await fixture(t);
  const original =
    "# Todo\n\n" +
    record("low", { priority: "Low" }) +
    record("high", { priority: "High" });
  await writeFile(f.file, original);
  f.git("add", "todo.md");
  f.git("commit", "-qm", "fixture notes");
  const p = await plugin(f, NO);
  assert.equal(
    (await p.propose({ content: undefined, sort: true })).status,
    "declined",
  );
  assert.equal(await readFile(f.file, "utf8"), original);
  assert.match(p.forms[0].questions.at(-1).question, /Reorder:/);
  const q = await plugin(f, (input) =>
    input.questions.map((_, i) =>
      i === input.questions.length - 1 ? ["Reconsider order"] : [],
    ),
  );
  const feedback = await q.propose({ content: undefined, sort: true });
  assert.equal(feedback.status, "revise");
  assert.equal(feedback.draft.sort, true);
  const r = await plugin(f);
  assert.equal(
    (await r.propose({ content: undefined, sort: true })).status,
    "saved",
  );
  assert.deepEqual(ids(await readFile(f.file, "utf8")), ["high", "low"]);
  assert.equal(f.git("rev-list", "--count", "HEAD"), "2");
  assert.equal(
    (await r.propose({ content: undefined, sort: true })).status,
    "unchanged",
  );
});

test("language and artifact rules are explicit in instructions and tool contract", async (t) => {
  const rules = await readFile(
    new URL("../config/decision-support.md", import.meta.url),
    "utf8",
  );
  assert.match(rules, /English even when the creation request is in Russian/);
  assert.match(rules, /use Russian content only\n  when explicitly requested/);
  assert.match(rules, /must retain their original language and wording/);
  assert.match(rules, /explicitly requests translation of that artifact/);
  const f = await fixture(t, false),
    p = await plugin(f);
  const tool = p.tools.get("agent_todo_propose");
  assert.match(
    tool.description,
    /Default to English content even for non-English requests/,
  );
  assert.match(tool.description, /Preserve supplied artifacts/);
  assert.equal(tool.input.properties.sort.type, "boolean");
  assert.match(tool.input.properties.reason.description, /English/);
});

test("native proposal path applies structured status/priority without model-written metadata", async (t) => {
  const f = await fixture(t),
    p = await plugin(f);
  const add = {
    add: [
      {
        id: "task",
        title: "Task",
        summary: "Finish task.",
        goal: "Finish.",
        returnWhen: "Ready.",
        priority: "High",
      },
    ],
  };
  assert.equal(
    (await p.propose({ content: undefined, changes: add })).status,
    "saved",
  );
  const first = await readFile(f.file, "utf8");
  const created = first.match(/^Created: (.+)$/m)[1];
  assert.equal(
    (
      await p.propose({
        content: undefined,
        changes: { update: [{ id: "task", status: "Done", priority: "Low" }] },
      })
    ).status,
    "saved",
  );
  const done = await readFile(f.file, "utf8");
  assert.match(done, /Visits: 1 · Priority: Low\nStatus: Done/);
  assert.match(done, /^Completed: \d{4}-/m);
  assert.ok(done.includes(`Created: ${created}`));
  assert.equal(
    (
      await p.propose({
        content: undefined,
        changes: { update: [{ id: "task", status: "In progress" }] },
      })
    ).status,
    "saved",
  );
  const active = await readFile(f.file, "utf8");
  assert.doesNotMatch(active, /^Completed:/m);
  assert.match(active, /Total: 1 · Done: 0 · In progress: 1/);
  assert.match(active, /## \[ \] 1\. Task/);
  const tampered = active.replace(
    "Visits: 1 · Priority: Low",
    "Visits: 999 · Priority: High",
  );
  assert.match(
    countRevisits(active, tampered, [], "d".repeat(64)),
    /Visits: 1 · Priority: Low/,
  );
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
