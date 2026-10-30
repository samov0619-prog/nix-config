# OpenCode 2.1.4

Домашний Home Manager module для laptop/desktop. OpenCode закреплён отдельным
flake input `github:anomalyco/opencode/v2.1.4` (rev `68bc26b7da1990ce10ffecfbc1e09eb13aa5d824`),
без обновления всего nixpkgs-unstable. Официальный LTS-канал не обнаружен.
`package.nix` сохраняет upstream build и добавляет небольшой
`patches/session-routing.patch` и `patches/session-attention.patch`; Linux wrapper сохраняет runtime libraries для watcher
и native audio. V1-модуль и прежние исследования — в [archive/v1](archive/v1/README.md).

## Структура

```text
opencode/
├── default.nix              # Home Manager: подключение и установка файлов
├── package.nix              # pinned binary, patches и Linux runtime libraries
├── config/                  # native V2 settings и устанавливаемые глобальные AGENTS.md
├── plugins/                 # server plugins и TUI plugins
│   └── model-routing/       # tui.ts, общая policy и единая таблица моделей
├── patches/                 # binary patches и общий session-attention.ts
├── scripts/                 # read-only отчёты и тихая Kitty urgency
├── skills/                  # <skill>/SKILL.md
├── sounds/                  # домашние аудиофайлы (wow — запасной вариант, не установлен)
├── tests/                   # unit, isolated runtime и PTY checks
├── macos/                   # независимый корпоративный source overlay
└── archive/                 # неиспользуемые V1 и RLM reference
```

`config/v2-settings.nix` читает таблицу из `plugins/model-routing/routing-models.json`.
`patches/session-attention.ts` используется и binary patch, и `plugins/quiet-urgency.ts`.
Это структура **исходников**: пути в `~/.config/opencode`, имена команд,
plugin IDs и storage не меняются. Пустой прежний `lib/` удалён; архив не устанавливается.
Проверки и ограничения покрытия — в [BENCHMARK.md](BENCHMARK.md).

## Модели и сессионные команды

`/switch-free` и `/switch-paid` — локальные TUI-команды, без LLM-запроса.
Они записывают `local.model-routing` в metadata **корневой сессии**, сохраняя
остальные keys. Новые обычные сессии используют paid defaults. Ручной model
picker не включает free mode. Сессионная политика после явной команды имеет
приоритет над отдельным ручным model selection до следующего переключения.

| Роль | Paid |
|---|---|
| Build/general/research/review | GPT-6.1 Sol High |
| Plan | GPT-6.1 Sol XHigh, alias `gpt-6.1-sol-plan` |
| Explore | GPT-6 Luna Max, alias `gpt-6-luna-max` |
| Compaction/служебная generation | Sol High, alias `gpt-6.1-sol-high` |
| Title | Luna Low |

Free направляет все эти роли на `opencode/big-pickle`. Политика действует на
**последующие** запросы существующих детей и сохраняется в DB при reopen.
Уже начатый запрос не отменяется. Другие корневые сессии не переключаются.
Перед записью команда проверяет доступность всех моделей/variants; при ошибке
режим не меняется, автоматического перехода с free на paid нет.
Настоящий V2 каталог без пользовательских credentials содержит активный Big
Pickle с public key и нулевой каталожной стоимостью; это не гарантия будущих
условий сервиса или успешности удалённого запроса.

Единый paid role table — `plugins/model-routing/routing-models.json`. Его используют Nix, TUI-команды
и core patch. Patch перечитывает live root перед каждым model resolve, включая
title/compaction/auxiliary generation, и согласует TUI selection с запросом.
Если ancestor ещё не загружен в TUI cache, он синхронизируется до выбора модели.
При обновлении upstream повторить сквозные проверки, а не только patch apply.
HM собирает model-routing одним store-каталогом с обычными файлами, затем
связывает их через `recursive = true`, сохраняя прежние managed paths.
Symlinks в разные изолированные store-файлы ломают относительные импорты Bun.

### Изоляция уведомлений между TUI

`patches/session-attention.patch` ограничивает native `opencode.notifications` текущей
сессией TUI и её потомками; тот же `patches/session-attention.ts` используется для тихой
Kitty urgency. Общий event stream, одинаковая директория и global tabs не дают
чужой сессии права включать звук/подсветку/ошибку-toast в этом окне. На home и
plugin routes session-уведомления молчат. Неизвестная ancestry и global forms
без привязки к сессии не вызывают attention. Дедупликация и native sound settings
сохраняются; второго аудиоплеера и BEL нет.

Правило — «открытая сессия и её подагенты», не single-owner election: если одна
сессия открыта сразу в двух TUI, она принадлежит обоим. При просмотре отдельного
подагента родитель/соседи не уведомляют его окно. Смена route применяется сразу.

Это исправление **домашнего pinned binary**, не официального Mac binary из
самостоятельного архива. После HM switch нужно заново открыть работающие TUI,
чтобы загрузить новый встроенный notification code; `/reload` обновляет только
конфигурацию/local plugins. Общий server ради этой TUI-правки перезапускать не
нужно. Рабочая директория/сами сессии и `session.new_location` не изменяются.

До явной команды обычная compaction наследует модель сессии — сохранённый
пользовательский выбор. `/switch-paid` устанавливает High и для compaction.
High для work / XHigh для plan — рабочая гипотеза, не доказанный optimum;
прежние измерения качества и их ограничения сохранены в V1-архиве.

Soft input `244000 − buffer 32000 = 212000`, output 128000, recent tail 15000.
Проверка порога между шагами допускает overshoot. V2 использует `buffer` и
`keep.tokens`; старого `prune=false` в native config нет.

## Native audio и тихая urgency

Звук воспроизводит только штатный `opencode.notifications` / OpenTUI Audio.
Mutable `~/.config/opencode/cli.json` задаёт `attention.sound`, `volume` и
`sounds.permission/done/error`. Home Manager **создаёт defaults лишь при
отсутствии файла**, чтобы native settings могли сохранять mute/volume.
Permission — freedesktop bell, преобразованный в WAV; done/error — локальные
anime sounds. В существующем `cli.json` пути к ним при необходимости задать в
native settings вручную: `~/.config/opencode/sounds/{permission.wav,completion.mp3,error.mp3}`.

V1 sound state machine, её фильтрация дочерних/остановленных задач и команды
`/mute`/`/unmute` не подключены. Используются native semantics, включая события
подагентов/остановки. Старые TS-файлы/tests — только V1 reference.

### Дом и корпоративный Mac — разные настройки

| | Домашний laptop/desktop | Корпоративный Mac |
|---|---|---|
| Звуки | Личные anime done/error, freedesktop permission | Только стандартные встроенные OpenCode |
| Обработчик | Native plugin с `session-attention.patch` | Штатный `opencode.notifications`, без нашего `session-notifications` |
| Kitty urgency | Домашний `quiet-urgency.ts` | Домашний plugin не переносится |

**Личные звуки — только для дома.** При ручном Mac-порте не копировать домашний
`cli.json`, `attention.sounds`, аудиофайлы и `quiet-urgency`. Mac сохраняет свои
личные CLI-настройки; его текущее штатное поведение уведомлений оставляем без
изменений. Изоляция и кастомизация независимы: патч фильтрует события, а пути
к звукам задаются штатным `attention.sounds`. Самостоятельный Mac-порт не
обновляется домашним Home Manager и не должен наследовать эти настройки.

`plugins/quiet-urgency.ts` дополняет native notifications **только** тихой Kitty
workspace/tab urgency через `scripts/silent-attention.py`; не отправляет BEL и не
проигрывает аудио. Его подписки не зависят от `attention.sound`, поэтому mute
не должен отключать подсветку. OSC99 desktop notification сам по себе не
доказывает Waybar urgency. Live-проверка mute/unmute и PipeWire всё ещё нужна.

`plugins/workspace-context.ts` публикует полное Unicode-название **просматриваемой**
сессии и её directory в `$XDG_RUNTIME_DIR/hypr-spaces/apps/`, включая rename и
route changes без prompt. PID/starttime/Kitty pane и cleanup сохранены.
Модельных запросов и чтения message history нет.

## Permissions и отчёты

Основные tools используют native V2 baseline. Plan запрещает edit;
research/review/explore — read-only, без дальнейшего делегирования/todos,
Explore также не вызывает skills. Подключены штатные discussion-map и
git-regression-rollback; RLM/governor не устанавливаются.

Skill selection follows native V2 discovery: the advertised `description` owns
the trigger; `config/AGENTS.md` does not force discussion-map for general planning.
Discussion-map requires established independent threads needing coordination or
an explicit map request, not a single task, routine status check or topic change.
Git-regression-rollback requires a user-authorized temporary commit rollback;
ordinary investigation and permanent reverts are outside its scope. Already-loaded
instructions are reused rather than loading the same skill on every follow-up.
Built-in `opencode`/`report` are not overridden. These rules remain model guidance,
not a deterministic classifier; use skill statistics to check false positives.

Нативные `tool.use` policies запрещают сетевые Git-команды даже поверх Always.
`plugins/git-offline.ts` через shell `create.before` задаёт `GIT_ALLOW_PROTOCOL=""`,
`GIT_NO_LAZY_FETCH=1`, `GIT_TERMINAL_PROMPT=0`, в том числе для составных команд
и `git -C`. Это дополнительная transport-защита, **не sandbox** для произвольного
shell/env override. Сеть Git выполняет пользователь.
`remote`, `remote -v`, `get-url`, `show -n` читают local config; `remote show`
без `-n`, `remote update`, `set-head --auto`, `add -f` способны ходить в сеть.
`remote add/rename/remove/set-url` изменяют local config: это не read-only операции.

`plugins/permission-stats.ts` читает native V2 permission events, дописывает прежний
XDG state `opencode/permission-history.jsonl`, теперь с session/request IDs.
Это учёт **запрошенных решений**, не всех auto-allowed вызовов. Старый history
и usage ledgers сохраняются. `opencode-permission-stats` агрегирует журнал.
Server plugins в HM развёрнуты как directory symlinks `*-v2` в store-каталоги
с обычным `index.ts`: native V2 проверяет, что real entrypoint находится внутри
real plugin root. Отдельный symlink `index.ts` за пределы root молча исключался
из discovery. Новые directory paths позволяют HM убрать старые managed leaves
без конфликтов при обновлении. IDs и данные plugins не меняются.

`opencode-task-report --session <id>` читает SQLite в read-only transaction и
поддерживает V1/V2 tables, детей, cache, saved retry/tool states и compaction.
При наличии сессии в V2 предпочитает её legacy-копии; `--recent N` объединяет
обе версии без дубликатов. Проверен на настоящей изолированной V2 DB, включая
точные token totals и compaction.

`plugins/model-calls.ts` дописывает приватный XDG state `opencode/model-calls/<session>.jsonl`.
В том же отчёте теперь есть **каждая наблюдаемая transport attempt**: время,
сессия/ребёнок, `primary`/`title`/`generate`/`compaction`, agent, resolved
provider/model/variant, API `model` и reasoning effort (если удалось извлечь).
HTTP retries — отдельные строки; HTTP status означает только получение headers,
не завершение stream. WebSocket Open Responses учитывается перед отправкой
`response.create`, без предположения об успехе; control frames не считаются.
Тела, URL, headers, ошибки провайдера, prompts и ключи не сохраняются.

История начинается после установки плагина; старый нейминг восстановить нельзя.
Вызовы вне native session hooks не покрываются; последующие hooks могут менять
запрос. Для HTTP JSON больше 8 MiB/неподдерживаемых протоколов wire model/effort
может быть неизвестен, resolved model остаётся. Token totals по-прежнему берутся
только из messages/legacy ledgers: журнал вызовов ничего к ним не добавляет.
V2 сохраняет title usage в отдельных events, но этот отчёт их не суммирует.
Это не invoice и не измеритель подписочной квоты.
См. [BENCHMARK.md](BENCHMARK.md).

### Вызовы скиллов

`plugins/skill-stats.ts` — один native V2 `tool.execute.after` hook, без LLM, polling
и изменения поведения скиллов. Каждый завершившийся вызов инструмента `skill`
сохраняет ID скилла, статус (`completed`/`error`), время, agent/model, session,
tool call/message IDs и **полный текст предшествующего запроса** с его ID.
Запрос выбирается перед вызывающим assistant message в той же сессии; более
поздние steering/queued prompts не подменяют его. Если граница/запрос отсутствуют
в текущем контексте (например, после compaction), запрос остаётся неизвестным.

Хранилище — штатный `ctx.storage` в локальной OpenCode DB, namespace
`local.skill-stats`; отдельной БД/журнала нет. Ключ session + message + tool call делает
повторную обработку идемпотентной; счётчики вычисляются по записям. Содержимое
скилла, tool output и ошибки не копируются. Ошибка записи/lookup не ломает вызов,
но учёт может быть неполным. История начинается после установки; явные `@skill`
без вызова инструмента, прерванные до after hook вызовы и причина решения модели
не покрываются. Записи не удаляются автоматически при удалении исходной сессии.

Просмотр без изменения DB:

```fish
opencode-skill-stats
opencode-skill-stats --skill discussion-map --examples 10
opencode-skill-stats --json
```

По умолчанию выводятся только счётчики, число сессий и неизвестных запросов.
**`--examples N` раскрывает приватные тексты запросов**, включая в JSON-выводе:
не отправлять такой отчёт/DB в Git или публичные логи. Тексты хранятся локально
с той же защитой, что и остальная OpenCode DB; дополнительного шифрования нет.
Домашний HM подключает сборщик на laptop/desktop; самостоятельный Mac-порт
не меняется. После HM switch V2 автоматически перечитывает plugins; при
необходимости выполнить `/reload`, перезапускать service не требуется.

## Decision support и локальные todo

Домашний модуль явно включает `programs.opencode.decisionSupport.enable`:
короткая дополнительная инструкция, узкий навык `decision-check` и инструментальный
плагин `local.agent-todo`. NixOS/server и самостоятельный Mac-порт не меняются.
Для отключения задать `programs.opencode.decisionSupport.enable = false;` и применить
Home Manager. F3 — независимый обычный Hyprland bind, он продолжит открывать заметки.
На одну беседу можно попросить не предлагать decision-check/todo; это указание модели,
не механический переключатель. Навык не загружается при каждом выборе. Цитата внутри
него сохранена по-русски с исправлением только лишней запятой; показывается редко.

**F3** открывает `~/agent-todo/todo.md` в отдельном Kitty/Neovim на laptop/desktop;
команда `agent-todo-open` делает то же самое. Каталог создаётся при открытии, файл —
при сохранении в редакторе или согласованной записи. Сам Markdown и `.git` — ручное
состояние вне Nix store и вне этого репозитория, не создаются при HM activation.

В OpenCode попросить, например: «Сохрани идею проверки прошивки в todo». Агент читает
файл через `agent_todo_read`, предлагает целый итоговый файл через `agent_todo_propose`.
Штатное меню показывает русский вопрос, точный diff к текущему файлу, уже имеющиеся
ручные/staged правки, путь и commit subject. «Да, сохранить» применяет и локально
коммитит **весь согласованный итоговый todo.md**, включая показанные ручные изменения.
«Нет, не сохранять» ничего не меняет. Свободный ответ возвращается агенту для уточнения;
повторный вопрос — только при оставшемся существенном выборе. Пункт свободного ввода
пока имеет штатное английское название `Type your own answer`. Закрытие формы не
является согласием; штатный Question может завершить текущий шаг до нового ввода.
Plan явно отклоняется самим todo-инструментом, даже при session-level `edit: allow`.

Формат (числа вычисляет инструмент; в примере второе обращение):

```markdown
# Todo

## Проверить пробуждение ноутбука

<!-- todo:laptop-suspend -->

Обращений: 2 · Приоритет: 2

- Цель:
  Проверить suspend/resume на конкретной прошивке.
- Вернуться, если:
  Устройство доступно для воспроизводимого теста.
- Заметки:
  Сравнение общих спецификаций этого не установит.
```

Новый блок получает `1`; `revisited: ["laptop-suspend"]` при осознанном возвращении
увеличивает счётчик и числовой приоритет до `2`, `3` и далее — только после согласия.
Большее число означает больше возвращений, не срочность/обязанность выполнить.
ID стабилен при переименовании заголовка. В том же HTML-комментарии инструмент хранит
`last:<sha256>` от session/user-message IDs для дедупликации. Это непрозрачный локальный
идентификатор, не текст разговора. Повторы инструмента в одном user turn, чтение и
переформулирование счётчик не повышают. При неизвестной границе user message (например,
после compaction) инкремент отклоняется, а не угадывается. Распознавание «вернулись к
той же идее» остаётся суждением модели; плагин сам семантически темы не сопоставляет.
Не удалять ID/last, если нужна эта дедупликация. Произвольные ручные заметки допустимы,
но для учёта возвращений нужен блок с ID. Автоматической сортировки/опроса файла нет.

Защита записи: повторная проверка content/HEAD/index/status после ответа и перед
записью, короткий локальный lock и native Git index lock. Устаревшее предложение
требует нового чтения и согласия. Плагин отказывается работать с symlink/hardlink,
конфликтами, незавершёнными Git-операциями, другими файлами в репозитории и файлом
больше 32 KiB. Несохранённые буферы Neovim не видны; сохранения внешнего редактора
не кооперируются с lock, поэтому абсолютной защиты от записи именно между последней
проверкой и rename нет. Не редактировать одновременно в момент подтверждения.

Git создаётся при первом согласии; нужны настроенные `user.name`/`user.email`.
Используются отдельный временный index, `commit-tree` и compare-and-swap `update-ref`,
без hooks/signing, сетевых операций и `git add -A`. Неудача не запускает rollback:
проверить `git -C ~/agent-todo status` и `git -C ~/agent-todo log -5 --oneline`.
После аварийного завершения могут остаться `.git/agent-todo.lock`/`.git/index.lock`;
удалять их вручную только убедившись, что записи больше нет. Notes/history приватны,
не публиковать без проверки. Plan может читать, но явный guard запрещает предложение
с записью до показа формы; для остальных агентов применяется native `edit` permission.

Нагрузка: нет отдельной LLM-оценки, polling, event subscriptions, фонового агента или
сервиса; только короткая постоянная инструкция и схемы двух tools в контексте.
Загрузка навыка/подтверждение могут добавить обычный шаг основного агента. При работе
с todo — ограниченное чтение, локальные Git subprocesses и чтение текущего session
context для attribution; временный preview удаляется, журнал предложений не создаётся.
Сам файл уже хранится локально, показанные tool results/diff — в обычной истории
OpenCode. Семантические false positives возможны: отрицательный ответ должен прекращать
повторные советы без новых фактов. Ни автообнаружения всех возвращений между чатами,
ни гарантированной памяти о прошлых советах после compaction здесь нет.

Проверка: `node --test home/apps/opencode/tests/test_agent_todo.mjs`, затем isolated
runtime/HM-generation smoke из BENCHMARK. Unit-тесты с fake question не доказывают
поведение живой модели; fixtures навыка — сценарии для ручной оценки точности, а не
автоматическое измерение полезности. Live F3/форма/редактор проверяются на целевом хосте.

## Kitty clipboard MIME 5522

Проверены OpenCode **2.1.4** и закреплённый OpenTUI **0.6.8**. Реализации
Kitty MIME paste / OSC5522 / private mode **5522** в проверенном parser нет.
Native clipboard-service PNG/text support не заменяет этот terminal protocol.
Ожидаем upstream-поддержку; затем повторяем text **и image** paste в Kitty.
Не включать отвергнутые global Kitty workaround mappings.
Спецификация: <https://sw.kovidgoyal.net/kitty/clipboard/>.

## Проверка и применение (Fish)

1. Проверить diff и собрать Home Manager без activation:
   ```fish
   nix build --no-link .#homeConfigurations.samov-laptop.activationPackage
   ```
   Для desktop — `samov-desktop`. Пока новые файлы не отслеживаются Git,
   использовать `path:.#…` вместо `.#…`.
2. Применить **только Home Manager** для нужного хоста:
   ```fish
   home-manager switch --flake .#samov-laptop
   ```
   Для этих изменений NixOS switch не требуется.
3. После изменений config/local plugins достаточно автоматической перезагрузки
   или `/reload`. После замены **бинарника** переоткрыть TUI; чтобы загрузить новый
   серверный код (например, при миграции V1→V2 или обновлении routing patch),
   отдельно перезапустить background service: `opencode service restart`.
   Только TUI attention patch перезапуска сервиса не требует.
   Для изолированного запуска — `opencode --standalone`.
   V2 использует новый ChatGPT token-sharing OAuth flow. Если прежний browser
   credential не содержит client ID для этого flow, потребуется повторный
   вход через `opencode auth login`; API-key route от этого не зависит.
4. Проверить `/switch-free`, `/switch-paid`, Plan↔Build, существующего ребёнка
   и reopen. Сопоставить model/variant в UI с фактическим запросом.
5. Проверить permission/done/error при включённом и выключенном native sound:
   один звук либо тишина, но подсветка Kitty/Waybar в обоих случаях. Для нового
   Kitty socket/OpenCode plugin открыть новый процесс, reload недостаточно.

Самостоятельный корпоративный Mac-порт: [macos/README.md](macos/README.md).
Он сохраняет командный/личный layers, X5/proxy/MCP и local voice; домашняя HM
activation его не устанавливает. Полный архив лежит вне Git.
