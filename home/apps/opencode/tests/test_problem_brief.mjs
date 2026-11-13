import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const source = (path) => readFileSync(new URL(path, import.meta.url));
const command = source("../commands/problem-brief.md");
const guide = source("../problem-brief.README.md");
const commandText = command.toString("utf8");
const guideText = guide.toString("utf8");
const localReading = `Do not conduct external research, run tests, or modify files.
Read-only inspection of relevant local sources is allowed when
required by the user's request.`;

// Reconstruct the initial artifacts by reversing only the authorized edits.
// This bounds textual changes; it does not test real-model scope selection.
test("prompt retains the original bytes outside Scope and the local-reading rule", () => {
  const scope = commandText.match(/^## Scope\n[\s\S]*?\n\n(?=## Priorities)/m)?.[0];
  assert.ok(scope);
  assert.ok(commandText.includes(localReading));
  const original = commandText
    .replace(scope, "Focus: $ARGUMENTS\nIf no focus is provided, use the latest relevant report or discussion\nin the current session.\n\n")
    .replace(localReading, "Do not perform new research, run tests, or modify files.");
  const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");
  assert.equal(
    hash(original),
    "d71219aec86b12a7f91447f6c3892996dc79d79c7edb499ed4241c0afbcc5ab3",
  );
});

test("scope covers the preceding response, explicit requests and read-only local sources", () => {
  const flat = commandText.replace(/\s+/g, " ");
  for (const marker of [
    "User request: $ARGUMENTS",
    "transform only the immediately preceding assistant response",
    "Use earlier context only to resolve references",
    "It takes precedence over the default",
    "entire session, a specific discussion, project files, repository state, or recent Git commits",
    "use read-only tools to inspect the relevant information",
    "status or summary of completed work, report it directly",
    "Do not conduct external research, run tests, or modify files",
    "required by the user's request",
  ]) assert.ok(flat.includes(marker), marker);
  assert.doesNotMatch(commandText, /Focus:|If no focus is provided/);
});

test("guide documents the new scope without changing the original example or quality rules", () => {
  for (const example of [
    "/problem-brief по всей текущей сессии",
    "/problem-brief перечисли последние 5 коммитов и кратко объясни изменения",
    "/problem-brief что осталось незавершённым в авторизации",
  ]) assert.ok(guideText.includes(example), example);
  const original = guideText
    .replace(/^### Область анализа и аргументы\n[\s\S]*?(?=### Пример)/m, "")
    .replace(
      "Без аргументов команда обрабатывает непосредственно предыдущий ответ агента; с аргументом использует указанную область и цель. Для открытых вопросов она выполняет редакционную обработку:",
      "Команда опирается на доступный контекст текущей сессии — прежде всего на последний релевантный отчёт или обсуждение — и выполняет редакционную обработку:",
    )
    .replace(
      "Обязательных аргументов нет.",
      "Обязательных аргументов нет. Команда использует релевантный контекст текущей сессии. Если в нём несколько разных тем или отчётов, важно, чтобы нужный материал был очевиден из последнего обсуждения.",
    )
    .replace(
      "- Не проводит внешние исследования, не запускает тесты и не проверяет систему заново; по запросу допускается чтение локальных источников.",
      "- Не проводит новые исследования, не запускает тесты и не проверяет систему заново.",
    );
  assert.equal(
    createHash("sha256").update(original).digest("hex"),
    "b7b7cdb0dc99379d5cc79908a2e3a3a834d6127cd3aec1bd48d38d59a55f7f09",
  );
});

test("command remains manual and in-session without model or agent overrides", () => {
  const [, header, body] = command.toString("utf8").split(/^---\n/m);
  assert.match(header, /^subagent: false$/m);
  assert.doesNotMatch(header, /^(agent|model|subtask):/m);
  assert.ok(body.includes("$ARGUMENTS"));
  assert.doesNotMatch(body, /!`/);
});

test("selected HM declarations install exact sources with guide outside commands", () => {
  // Evaluate only these real module attributes, with no package set or builds.
  // This is not full merged HM evaluation or installed-runtime verification.
  const installed = JSON.parse(
    execFileSync(
      "nix",
      [
        "eval", "--offline", "--json", "--file",
        fileURLToPath(new URL("../default.nix", import.meta.url)),
        "--apply",
        `f: let
          files = (f {
            pkgs.stdenv.isLinux = true;
            lib.optionalAttrs = condition: attrs: if condition then attrs else {};
            config = {};
            opencodePackage = null;
          }).xdg.configFile;
        in {
          command = builtins.readFile files."opencode/commands/problem-brief.md".source;
          guide = builtins.readFile files."opencode/problem-brief.README.md".source;
          commands = builtins.filter
            (name: builtins.match "opencode/commands/.*problem-brief.*" name != null)
            (builtins.attrNames files);
        }`,
      ],
      { timeout: 10000 },
    ),
  );
  assert.equal(installed.command, command.toString("utf8"));
  assert.equal(installed.guide, guide.toString("utf8"));
  assert.deepEqual(installed.commands, ["opencode/commands/problem-brief.md"]);
});
