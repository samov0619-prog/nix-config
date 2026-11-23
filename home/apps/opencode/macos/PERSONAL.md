# Личное дополнение Samov

`opencode-local/` добавляет личные правила, роли и команды к общей конфигурации из соседнего `opencode/`. Модели, MCP и Git-защита остаются в общей базе.

## Подключение

Для Fish добавьте в `~/.config/fish/config.fish`:

```fish
set -gx OPENCODE_CONFIG "$HOME/.config/opencode-local/opencode.jsonc"
```

Для Zsh (`~/.zshrc`):

```zsh
export OPENCODE_CONFIG="$HOME/.config/opencode-local/opencode.jsonc"
```

Переменную должен получить сервер. Если он уже запущен без неё, после завершения активных задач выполните `opencode service restart` и `opencode service status`. Последующие правки конфигов загружаются автоматически.

При нестандартном `XDG_CONFIG_HOME` укажите свой абсолютный путь; пакет должен быть экспортирован с соответствующим `personalDirectory`.

## Роли и команды

`OPENCODE_CONFIG` загружает JSONC, но не превращает соседние каталоги в discovery-каталоги. Поэтому роли и команды явно зарегистрированы в `opencode.jsonc`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "agents": {
    "review": {
      "mode": "subagent",
      "system": "{file:agents/review.md}",
    },
  },
  "commands": {
    "problem-brief": {
      "description": "Turn technical reports into clear, actionable issue briefs",
      "subagent": false,
      "template": "{file:commands/problem-brief.md}",
    },
  },
}
```

Это фрагмент для объяснения, не замена полного конфига с permissions. `{file:...}` считается от каталога JSONC. Здесь `.md` содержит только текст prompt, без YAML frontmatter; metadata задана в JSONC. Симлинки в Common не нужны. Личные правила подключены через `instructions`, скиллы — через `skills`.

Все пять команд запускаются в текущем разговоре, сохраняя его агента и модель. Только две команды делегированного ревью затем вызывают отдельного `review`.

| Команда                                                                        | Назначение                                                               |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| [`/task-analysis [задача]`](task-analysis.README.md)                           | Разобрать требования и составить план изменений и проверок.              |
| [`/browser-verification [сценарий]`](browser-verification.README.md)           | Проверить поведение в живом браузере через Chrome MCP.                   |
| [`/delegated-review [scope]`](delegated-review.README.md)                      | Провести независимое read-only ревью кода.                               |
| [`/delegated-review-chrome [run/evidence]`](delegated-review-chrome.README.md) | Проверить выводы по уже записанной Chrome-MCP истории, без нового теста. |
| [`/problem-brief [запрос]`](problem-brief.README.md)                           | Превратить технический ответ в понятную краткую сводку.                  |

## Структура

- `AGENTS-personal.md` — личные правила; новые ветки и коммиты используют подтверждённый ключ `FBDC-<number>`, остальной формат берётся из Git history.
- `agents/` — `review` и `research`, без закреплённой модели; наследуют модель родителя.
- `commands/` — тексты пяти команд.
- `review-analysis.md`, `review-system.md` — общая методика и read-only правила reviewer.
- `skills/discussion-map/` — ручной `@discussion-map`, без автоматического вызова.
- `update-2026-11-16/` — исторические материалы, не инструкция новой установки.

## Проверка resolve

Из рабочего проекта выполните `opencode debug config`: должен присутствовать личный JSONC, в нём — `agents`, пять `commands`, `instructions` и `skills`. Здесь же проверяются `subagent: false`, отсутствие command model/agent overrides и раскрытые `{file:...}`.

Фактическую регистрацию можно посмотреть через `opencode api command.list --param directory="$PWD"` и `opencode api agent.list --param directory="$PWD"`. `command.list` показывает имена и описания, не все настройки исполнения. Не публикуйте диагностический вывод без проверки на секреты.
