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
const { todoStore, setupTodo, countRevisits } =
  await import("../plugins/agent-todo.ts");

const YES = "Да, сохранить";
const NO = "Нет, не сохранять";
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
      await onQuestion();
      return { output: { answers: [[answer]] }, content: "native answer" };
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

test("approval presents exact diff and commits only the approved content", async (t) => {
  const f = await fixture(t);
  const p = await plugin(f);
  const result = await p.propose();
  assert.equal(result.status, "saved", JSON.stringify(result));
  assert.equal(f.git("show", "HEAD:todo.md"), "# Todo\n\n- Test device");
  assert.equal(f.git("status", "--porcelain"), "");
  assert.equal(f.git("log", "-1", "--format=%s"), "add device test note");
  assert.match(p.forms[0].questions[0].question, /\+\- Test device/);
  assert.equal(p.forms[0].questions[0].options.length, 2);
  assert.ok(
    p.permissions.some((p) => p.action === "edit" && p.agent === "build"),
  );
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
    assert.deepEqual(result.answer, [answer]);
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
  await writeFile(f.file, "base\nstaged manual\n");
  f.git("add", "todo.md");
  await writeFile(f.file, "base\nstaged manual\nunstaged manual\n");
  const content = "base\nstaged manual\nunstaged manual\nnew idea\n";
  assert.equal((await p.propose({ content })).status, "saved");
  const question = p.forms[1].questions[0].question;
  assert.match(question, /\+staged manual/);
  assert.match(question, /\+unstaged manual/);
  assert.equal(await readFile(f.file, "utf8"), content);
  assert.equal(f.git("status", "--porcelain"), "");
  assert.equal((await p.propose({ content })).status, "unchanged");
  assert.equal(p.forms.length, 2);
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
  assert.equal(next.forms.length, 1);
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
