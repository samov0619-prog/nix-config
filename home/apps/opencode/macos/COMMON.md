# Общая конфигурация OpenCode

Глобальные правила (`AGENTS.md`), скиллы, плагины и инструменты. Общая конфигурация работает самостоятельно; личные дополнения подключаются отдельно.

## Переход на V2

Перед переходом с V1 закройте клиенты, остановите сервис и сохраните config, data, state и старый бинарник в приватную резервную копию. Не запускайте V1 на уже мигрированной БД.

Получите ветку `v2` общей конфигурации и переключитесь на неё, предварительно сохранив локальные изменения:

```sh
cd "$HOME/.config/opencode"
git fetch origin v2
git switch v2
git pull --ff-only origin v2
```

Обновите бинарник OpenCode (если он установлен через `curl`):

```sh
opencode upgrade --major --method curl
```

Текущая конфигурация подготовлена для OpenCode **2.4.0**. Если V2 уже установлен, повторять миграцию не нужно.

## Установка

1. Если `"$HOME/.config/opencode"` уже существует, сохраните его перед установкой (включая личные настройки):

   ```sh
   mv "$HOME/.config/opencode" "$HOME/.config/opencode-backup"
   ```

   Если каталога нет, этот шаг пропустите. Используйте свободное имя backup; резервную копию не коммитьте.

2. Клонируйте репозиторий сразу в стандартный каталог OpenCode:

   ```sh
   git clone git@scm.x5.ru:feedbacktc5/ai/team-agent-configs.git "$HOME/.config/opencode"
   ```

   Личные настройки из резервной копии можно подключить отдельно — см. «Совмещение с личной конфигурацией».

3. Задайте переменные окружения MCP-серверов. Значения живут в системе, а не в репозитории. OpenCode читает `{env:ИМЯ_ПЕРЕМЕННОЙ}` из окружения серверного процесса.

   Для Zsh добавьте в `~/.zshrc` (подставьте свои значения вместо плейсхолдеров):

   ```zsh
   export MCP_WIKI_URL="<wiki-mcp-url>"
   export MCP_WIKI_AUTHORIZATION="Bearer <wiki-token>"
   export MCP_KAITEN_URL="<kaiten-mcp-url>"
   export MCP_KAITEN_AUTHORIZATION="Bearer <kaiten-token>"
   export MCP_XTRACKER_URL="<xtracker-mcp-url>"
   export MCP_XTRACKER_AUTHORIZATION="Bearer <xtracker-token>"
   export MCP_GITLAB_URL="<gitlab-mcp-url>"
   export MCP_GITLAB_AUTHORIZATION="Bearer <gitlab-token>"
   ```

   Примените изменения: `source ~/.zshrc`.

   Для Fish выполните в fish (значения хранятся в `~/.config/fish/fish_variables`, повторный запуск перебивает значение):

   ```fish
   set -Ux MCP_WIKI_URL "<wiki-mcp-url>"
   set -Ux MCP_WIKI_AUTHORIZATION "Bearer <wiki-token>"
   set -Ux MCP_KAITEN_URL "<kaiten-mcp-url>"
   set -Ux MCP_KAITEN_AUTHORIZATION "Bearer <kaiten-token>"
   set -Ux MCP_XTRACKER_URL "<xtracker-mcp-url>"
   set -Ux MCP_XTRACKER_AUTHORIZATION "Bearer <xtracker-token>"
   set -Ux MCP_GITLAB_URL "<gitlab-mcp-url>"
   set -Ux MCP_GITLAB_AUTHORIZATION "Bearer <gitlab-token>"
   ```

   `set -Ux` действует сразу в текущей сессии и во всех новых.

   Переменные MCP-HUB (`MCP_HUB_URL`, `MCP_HUB_AUTHORIZATION`) прописывает однострочник из карточки на дашборде стенда (`https://feedbacktc5-test.fb-dc.x5.ru/ai/`): URL `<домен стенда>/mcp` и ваш `user-token` для авторизации.

   Дополнительно: `FIGMA_API_KEY` — для Figma-Framelink; `COPILOT_API_KEY` — для провайдера Copilot. Локальный `openai` использует ваш `ai-proxy` на `127.0.0.1:8080`. Задавайте секреты тем же способом, не записывайте их в Git.

4. Запустите OpenCode и проверьте подключение MCP-серверов.

### Перезапуск сервиса OpenCode

OpenCode 2 использует фоновый сервис. Если вы изменили окружение оболочки, из которой он запускается, после завершения активных задач выполните:

```sh
opencode service restart
opencode service status
```

Проверьте также сохранённые overrides через `opencode service get env`: они могут перекрывать окружение оболочки. Вывод может содержать секреты — не публикуйте его.

Обычные изменения конфигурационных файлов подхватываются автоматически, без перезапуска.

### Совмещение с личной конфигурацией

Общий репозиторий занимает `~/.config/opencode`. Личные настройки храните отдельно, например в `~/.config/opencode-local/opencode.jsonc`, и подключите через `OPENCODE_CONFIG`:

Для Zsh (`~/.zshrc`):

```zsh
export OPENCODE_CONFIG="$HOME/.config/opencode-local/opencode.jsonc"
```

Для Fish (`~/.config/fish/config.fish`):

```fish
set -gx OPENCODE_CONFIG "$HOME/.config/opencode-local/opencode.jsonc"
```

Перенесите только нужные личные настройки из резервной копии. Работу переопределений проверьте через `opencode debug config`. `OPENCODE_CONFIG_DIR` для обычной установки не нужен; `cli.json` остаётся в `~/.config/opencode/`.

Регистрацию личных ролей и команд см. в [README личного слоя](../opencode-local/README.md). Общая конфигурация от него не зависит.

#### Как объединяются конфиги и правила

При совпадении ключей более высокий уровень переопределяет нижний:

```text
          ↑ Приоритет выше
Системная управляемая конфигурация (если есть)
Проект: .opencode/opencode.json(c)
Проект: opencode.json(c)
Личный файл: OPENCODE_CONFIG
Глобальный каталог: ~/.config/opencode/
          ↓ Приоритет ниже
```

Проектные конфиги ищутся в рабочем каталоге и его родителях до корня файловой системы; внутри каждой группы более близкие имеют больший приоритет. Policies имеют отдельный порядок применения, см. [документацию](https://opencode.ai/docs/policies).

`AGENTS.md` и `instructions` **не переопределяют**, а дополняют друг друга:

- Глобальный `AGENTS.md` берётся из `~/.config/opencode/`. Проектные инструкции ищутся от рабочего каталога до домашнего (для проектов внутри него) либо до корня проекта (для остальных).
- Вложенные `AGENTS.md` подключаются при обращении к соответствующим подпапкам. В 2.4.0 при отсутствии `AGENTS.md` используется `CLAUDE.md`; глобальный fallback — `~/.claude/CLAUDE.md`.
- Личные правила можно добавить через `instructions`, например: `"instructions": ["~/.config/opencode-local/AGENTS-personal.md"]`. Приоритет противоречащих правил нужно сформулировать текстом: конфликты разрешает модель.
- Проектные скиллы и настройки располагаются в `.opencode/`.

#### Проверка resolve

Выполните из нужного проекта:

```sh
opencode debug config
```

Проверьте наличие общего `opencode.jsonc`, личного файла из `OPENCODE_CONFIG` (если подключён) и ожидаемых проектных источников. В 2.4.0 команда показывает загруженные записи конфигурации, а не единый итоговый объект. Не публикуйте полный вывод без проверки на секреты.

Назначение переменных:

- `OPENCODE_CONFIG` — путь к дополнительному JSON/JSONC-файлу.
- `OPENCODE_CLI_CONFIG_CONTENT` — JSON с временными настройками терминального клиента поверх `~/.config/opencode/cli.json`.

## Структура

Пути указаны относительно каталога `~/.config/opencode/`.

| Путь                     | Назначение                                                                                                                                                           |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AGENTS.md`              | Глобальные правила: исследование исходников, проверка изменений, источники требований для ревью и Git.                                                               |
| `opencode.jsonc`         | Модели, провайдеры (`copilot`, `openai`), разрешения и семь MCP: `MCP-WIKI`, `MCP-KAITEN`, `MCP-XTRACKER`, `MCP-GITLAB`, `Chrome MCP`, `MCP-HUB`, `Figma-Framelink`. |
| `cli.json`               | Локальные настройки терминального интерфейса; файл не хранится в репозитории и не заменяется патчами.                                                                |
| `plugins/`               | Локальные плагины OpenCode 2.                                                                                                                                        |
| `skills/`                | Общие скиллы агента.                                                                                                                                                 |
| `scripts/task-report.py` | Скрипт отчёта по задаче.                                                                                                                                             |

### Разрешения и политики

`opencode.jsonc` задаёт ограничения на двух уровнях:

- `policies` — разрешены только провайдеры `copilot` и `openai`, остальные запрещены. Shell-командам запрещены все формы сетевых операций Git: `push`, `pull`, `fetch`, `clone`, `ls-remote`, `remote update`, `remote show`, `remote set-head --auto` и `remote add -f/--fetch`, включая варианты с опциями внутри команды. Исключение — `git remote show ... -n`, читающий локальные данные без сети.
- `permissions` — команды, меняющие историю или локальное состояние репозитория, требуют ручного подтверждения (`ask`): `commit`, `merge`, `cherry-pick`, `revert`, `am`, `rebase`, `reset`, `checkout`, `switch`, `clean`, `restore`, мутирующие `branch`, `tag`, `stash` и `worktree`; отдельно `git commit`. Чтение истории и статуса разрешено без подтверждения.

Сохранённые гранты «Always» просматриваются и удаляются плагином `permissions/`. Эти ограничения относятся к агенту; команды установки пользователь выполняет сам.

### Источники требований при ревью

Секция «Requirements Sources» в `AGENTS.md` требует найти внешние требования до оценки соответствия задаче: явную задачу или документ, иначе — источник из описания, заголовка и ветки MR или локального диапазона. Агент использует доступные read-only MCP XTracker/Wiki/GitLab, проверяет связь задачи с ревизией и читает критерии приёмки. Неоднозначность требует уточнения; недоступность источника фиксируется как пробел покрытия, а не ошибка кода. Техническое ревью без внешнего ТЗ возможно по явной договорённости.

### Плагины

- `git-offline/` — дополнительная защита от сетевых Git-операций агента.
- `permission-stats/index.ts` — записывает запросы и ответы системы разрешений в `$XDG_STATE_HOME/opencode/permission-history.jsonl` (по умолчанию `~/.local/state/opencode/permission-history.jsonl`).
- `permissions/` — TUI-плагин: `/allowed-permissions` («Allowed permissions» в палитре) показывает гранты «Always» текущего проекта и позволяет удалять их с подтверждением. Политики из `opencode.jsonc` не показывает.
- `@safwan-o/opencode-voice` — необязательный внешний TUI-плагин голосового ввода. В эту поставку не входит; устанавливать его для работы конфигурации не нужно. Если он нужен отдельно, используйте `opencode plugin add @safwan-o/opencode-voice`; подключение хранится в локальном `cli.json`, не в серверном `opencode.jsonc`.

## Чеклист по добавлению скиллов (проверка человеком)

Перед созданием или публикацией скилла проверьте его вручную по [чеклисту ревью агентского скилла](agent-skills-review-checklist.md): назначение и границы, инструкции, инструменты, надёжность и проверка на модели.

### Скиллы

- `task-summary-log` — по явной команде («создай лог», «обнови лог») создаёт или обновляет английский лог в `./promptLogs/` целевого проекта. Один файл на задачу: `FBDC-123456_<short-name>.md`, без ключа — `<YYYY-MM-DD>_<short-name>.md`. Ключ XTracker необязателен; существующий лог, в том числе со старым именем, обновляется без дублирования.
- `git-regression-rollback` — временно откатывает недавние коммиты с сохранением изменений в stash, только после явного разрешения пользователя.
- `code-patterns-skill-generator` — исследует соглашения проекта, показывает черновик для подтверждения и создаёт или обновляет `.opencode/skills/<name>/SKILL.md`. Вызов: «Загрузи скил code-patterns-skill-generator и создай скил: <тема>».

`discussion-map` перенесён в личный слой и вызывается вручную через `@discussion-map`.

## Документация

- [Конфигурация OpenCode 2](https://opencode.ai/docs/config)
- [Личный слой и команды](../opencode-local/README.md)
