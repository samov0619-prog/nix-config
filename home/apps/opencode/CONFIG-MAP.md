# Карта разделения конфигураций OpenCode

Статус: **домашнее разделение/upstream 2.4.0 и полный корпоративный staging-export
реализованы в исходниках; сборка и целевая приёмка впереди**.
Составлена 2026-11-20; границы исправлены 2026-11-23.

Реализуем три сущности: домашнюю HM-конфигурацию, общую командную конфигурацию
и личное дополнение Samov на корпоративном Mac. Пакет Даши — **EXAMPLE ONLY**:
справочный пример совместимости и источник идей, не четвёртая поставка этой задачи.
Создание карты не разрешает перенос файлов, изменение permissions, установку,
сборку, применение конфигурации или коммит. Существующие правки не перезаписываются.

## 1. Что уже согласовано

- Нынешние permissions — исходная база, но личные дополнения должны позволять
  намеренные overrides. Common не становится неизменяемой личной policy Samov.
  Командная Git-защита — согласованное исключение: policies и Git-offline остаются
  как сейчас и не отменяются обычными permissions. Старым seed базу не заменяем.
- В разделе permissions итогового корпоративного README указать: добавление
  новых policies и изменения `git-offline` — только по согласованию с командой.
- `discussion-map` — личный skill Samov дома и в корпоративном дополнении,
  с ручным вызовом `@discussion-map`; в Common его и требования автозагрузки не будет.
- Ограничение MCP по провайдеру — отдельные будущие задачи, вне этого обновления
  и его приёмки. Нынешние MCP-подключения и их поведение сохраняются.
- Конфиг Даши не меняем: не навязываем ей FSD/SOLID или workflow Samov;
  переопределение обычных permissions допускается, но командная Git-защита остаётся.
  Личный слой сейчас делаем
  только Samov; совместимость обеспечиваем границами Common, не переделкой примера.
- Существующие имена агентов, skills, команд и MCP — отправная точка. Новые имена
  нужны только для новых сущностей или доказанного конфликта.
- Общая командная поставка работает без обоих личных дополнений. Она не требует
  `dev`, личного `review`, отдельных review-команд или личных policy-файлов.
- Локальное дополнение подключается штатным `OPENCODE_CONFIG`, без собственного
  runtime-загрузчика, системы профилей или обязательного редактирования Common.
- Способ работы — интерактивный либо оркестрация — не предписывается общей базой.
- Common оставляем с базовыми агентами; личные специалисты и routing Samov
  сохраняются лично. Расширение личного подхода полезными идеями из skills Даши
  рассматриваем отдельно. Продвижение специалистов в Common — только позже
  после соглашения. Базовые `build`, `plan`, `general`, `explore` остаются штатными,
  без новых личных prompts, role permissions или routing Samov в Common;
  существующие общие ограничения и настройка `title` сохраняются.
- Домашняя конфигурация не получает корпоративные MCP, обязательное внешнее ТЗ,
  трекер, frontend-архитектуру, workflow публикации MR или раскатку на стенд.
- Перенос полезных практик не означает копирование всех исходных предписаний.
  Пока это кандидаты для личного слоя Samov, не поручение переписать frontAgents.

Порядок решений и результаты исследования:
[CONFIG-CHECKLIST.md](CONFIG-CHECKLIST.md). Одобрение структуры не означает
одобрение всех рекомендаций, реализацию или снятие действующих ограничений агента.

## 2. Проверенные исходные точки

| Источник                                     | Что принимается за исходную точку                                                                      |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `/home/samov/Downloads/trf.zip`              | Актуальный предоставленный снимок корпоративного Common и личного Mac-дополнения: 37 файлов вне `.git` |
| `home/apps/opencode/`                        | Нынешние домашние исходники, включая уже существовавшие незакоммиченные изменения; не только `HEAD`    |
| `macos/trf-review/`                          | Историческая подготовка R3 из коммита `98aadcc`; источник для сравнения, не замена свежего снимка      |
| `/home/samov/Downloads/frontAgents.zip`      | Расширенный пакет Даши: 65 файлов, 16 агентов, 14 skills                                               |
| `/home/samov/Downloads/frontAgents-main.zip` | Второй вариант: 40 файлов, 9 агентов, 11 skills; сохраняется как отдельный исходник                    |

SHA256 архивов:

```text
trf.zip
c793a32ce23de032e2963e154e7ab8f2f4f88f3f51e00d4f8b514ed03a07ff05
frontAgents.zip
5657bca8d3699664f0d2dcd71c09d793de0b72c8cd7943c19f704469c8cc9ffd
frontAgents-main.zip
d8f0cb0d0b84c087e1188533776f7f2bc5cf2d73c5561c9461bac2277053cef8
```

Содержимое `.git` из ZIP не исследовалось и не исполнялось. Оно не входит в новую
поставку, но исходный архив не изменяется. Секреты, auth, история сессий и машинное
состояние не переносятся в карту или будущий публичный пакет.

### Что подтвердил свежий Mac-снимок

- Двенадцать пересекающихся с R3 файлов совпадают побайтно: оба AGENTS, reviewer
  в обеих папках, две delegated-review-команды в обеих папках, две личные README
  и две личные review-policy. Это не доказывает неизменность остальных файлов.
- Актуальный `opencode.jsonc` содержит семь MCP: `MCP-WIKI`, `MCP-KAITEN`,
  `MCP-XTRACKER`, `MCP-GITLAB`, `Chrome MCP`, `MCP-HUB`, `Figma-Framelink`.
  Их имена, env-подстановки, настройки и состояние сохраняются, без копирования
  секретных значений. Старый `macos/opencode/opencode.json` неполон для этой базы.
- Нынешние Git permissions/policies существенно полнее старого Mac-seed.
  Это baseline для сравнения. Будущие намеренные overrides и перенос личных
  настроек учитываются явно; командная Git-защита остаётся без изменения поведения.
- `cli.json` подключает `@safwan-o/opencode-voice`. Старый самописный Mac voice-port
  не является актуальной реализацией и не должен восстановиться при обновлении.
- Git-offline, оба файла permissions-плагина, permission-stats, `problem-brief`,
  `discussion-map` и `git-regression-rollback` совпадают с домашними исходниками.
  Сходство не означает разрешение автоматически объединить все поставки.
- `scripts/task-report.py` отличается: домашний вариант поддерживает журнал
  model-call attempts, Mac-вариант дополнительно явно отклоняет сессию без сообщений
  поддерживаемой схемы. Не заменять один другим целиком; сохранить обе возможности
  при возможном будущем объединении. Сейчас оставляем реализации на своих местах.
- Reviewer и три команды присутствуют в обеих папках с одинаковым содержимым.
  ZIP помечает все эти пути обычными файлами. История R3 описывает три симлинка,
  поэтому типы живых путей из этого ZIP установить нельзя. До будущего патча
  нужно отдельно сверить типы и цели, не повторяя ошибку поставки R1.

### Незакоммиченные домашние изменения

Уже существуют `config/AGENTS.home.md`, `AGENTS.corporate.md`,
`AGENTS.corporate-personal.md`, `instructions.nix`, layer-tests и связанные правки
README/default.nix/fixtures. Это самостоятельная работа после R3, а не содержимое
выпущенного Mac-патча. При реализации она становится входом миграции, а не мусором
для удаления. Прочие изменения рабочего дерева, в частности notifications,
вообще не относятся к этой задаче.

## 3. Три целевые сущности и внешний пример

| Поставка                   | Основа                                                                                                                                                   | Локальное дополнение                                                                                        | Что не попадает внутрь                                                                                                        |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Домашняя, NixOS/HM         | Домашний binary/package/patches, providers, safety, домашние среды и переносимые общие правила                                                           | Личный workflow Samov, роли и review-команды, todo, личная маршрутизация моделей; Decision Support в архиве | Корпоративные MCP, обязательные карточки/ТЗ, `.front`, FSD/React/MobX                                                         |
| Корпоративный Common       | Свежий `trf/opencode`, без личных точек входа; общие правила, integrations, базовые агенты, переопределяемые permissions и нынешняя командная Git-защита | Не требуется; база работает самостоятельно                                                                  | Личные workflow/default_agent, review-policy-пути и UI; Git policies/Git-offline остаются общими                              |
| Samov на корпоративном Mac | Корпоративный Common без копирования его содержимого                                                                                                     | `opencode-local/opencode.jsonc`, личные инструкции, reviewer, review-команды и policies                     | Домашние Nix/HM, todo и звуки; Дашина оркестрация                                                                             |
| Даша — EXAMPLE ONLY        | Внешний неизменяемый пример                                                                                                                              | Её нынешние агенты, skills, permissions и проектные соглашения принадлежат ей                               | Ничего из её набора не устанавливаем и не переписываем в этой задаче; Common не должен навязывать ей личные ограничения Samov |

Общее между домом и командой — **переносимые исходники правил/skills**, а не один
и тот же полный `opencode.jsonc`. Корпоративная специфика не наследуется домом.
Два личных workflow не требуется включать одновременно в одном процессе.

### Подключение без изменений Common

```text
~/.config/opencode/                 общая база или домашняя основа HM
  opencode.jsonc
  AGENTS.md
  skills/                          действительно общие skills
  plugins/                         общие для этой поставки plugins

~/.config/opencode-local/           выбранное локальное дополнение пользователя
  opencode.jsonc                    инструкции, определения ролей/команд, skills
  AGENTS-personal.md
  skills/discussion-map/SKILL.md    личный skill Samov, ручной вызов
  agents/                          тексты локальных ролей
  commands/                        локальные шаблоны команд
  review-analysis.md               у Samov
  review-system.md                 у Samov
```

Для Fish точка подключения остаётся прежней:

```fish
set -gx OPENCODE_CONFIG "$HOME/.config/opencode-local/opencode.jsonc"
```

Это схема назначения, не готовая инструкция установки. У Даши дополнительный
файл может находиться в её нынешнем каталоге; путь задаётся явно. Переносить весь
frontAgents в папку Samov или переименовывать роли не требуется.

Важные технические условия:

1. `OPENCODE_CONFIG` загружает JSONC, а не автоматически соседние `agents/` и
   `commands/`. Предложение: определять роли/команды в локальном JSONC и подключать
   Markdown-тексты через `{file:...}`. Frontmatter переносится в соответствующие
   поля JSONC; подставлять весь YAML-frontmatter как `system` нельзя. Имена ролей
   и команд сохраняются. Это изменение формы хранения, не их поведения.
2. Skills подключаются штатным `skills` с явным путём. Чтобы путь не зависел от
   рабочего проекта, для внешнего набора используется `~/...` или абсолютный путь.
3. Поддерживаемые server/combined plugins из локального каталога подключаются
   через `plugins`. TUI-only plugins относятся к `cli.json`, а не автоматически
   к личному JSONC. Проверка нужна для целевых версий каждой поставки: домашние
   исходники/lock подключены к upstream 2.4.0; пользователь подтвердил уже
   установленную корпоративную 2.4.0, но приёмки нового пакета на ней ещё нет.
4. `cli.json` — отдельный глобальный пользовательский файл. Его не заменяет
   `OPENCODE_CONFIG`; живые UI/voice/sound-настройки сохраняются отдельно от Common.
5. Общие и личные `instructions` накапливаются. Поздний текст не удаляет ранний.
   Поэтому противоречия устраняются разделением содержания, не фразой «я главнее».
6. Окружение с `OPENCODE_CONFIG` должно получить именно server-процесс. Изменение
   переменной в новом терминале не меняет окружение уже работающего сервиса.
7. Если база не ссылается на локальные files/agents/commands, отсутствие дополнения
   не вызывает ошибок. Старые discovery-копии/симлинки убираются только после
   проверки нового подключения и с сохранением их личных целей.

Изолированный runtime на установленной 2.1.4 подтвердил загрузку обоих JSONC,
относительные `{file:...}`, четыре личные команды и reviewer metadata/запреты
из постороннего CWD без симлинков. Common-only не загрузил личные команды/роль.
Первоначальные markers двух процедур заменены реальными телами и регистрация
повторно прошла; system reviewer пока fixture marker. Выполнение/аргументы,
модельное поведение, runtime 2.4.0 и живой Mac не проверены. Подробности — в чек-листе.

## 4. Куда распределяются инструкции

Имена ниже — существующие исходники в `home/apps/opencode/config/`, кроме явно
помеченных новых файлов. Сборка текстов остаётся по явным спискам `instructions.nix`.
Новый runtime-loader не нужен.

| Исходник / раздел                                                                              | Целевое назначение                                                | Что сохраняется или меняется                                                                                                                                                |
| ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Новый `AGENTS.common.md`                                                                       | Переносимое инженерное ядро для дома и Common                     | Точные источники, применимость версий, сохранность пользовательской работы, проектный formatter, честные проверки, понятные контракты и комментарии; без режима оркестрации |
| `AGENTS.md`: Goals and Approach                                                                | Личный слой Samov дома и на Mac                                   | Сохраняется полностью; не объявляется командной философией задним числом                                                                                                    |
| `AGENTS.md`: Engineering Choices                                                               | Кандидат в общее ядро                                             | Сохраняются supported/public API, простота и removal contracts; продвижение в Common — явная часть согласуемой карты                                                        |
| `AGENTS.md`: Meaning / Collaboration                                                           | Личный слой; универсальное требование точности — в ядро без дубля | Сохраняется помощь пониманию, участие пользователя и различение решения/разрешения/приёмки                                                                                  |
| `AGENTS.md`: Tools / Source Exploration / Working Files / Formatting / Verification / Comments | Универсальные части в ядро                                        | Привязки к среде остаются в соответствующих средах; вместо обязательных имён `research/review` — выбор разрешённого способа работы                                          |
| `AGENTS.md`: Shell                                                                             | Личный слой Samov                                                 | Fish не становится обязательной оболочкой всей команды                                                                                                                      |
| `AGENTS.md`: Git / User Actions                                                                | Общая Git-защита и личные особенности                             | Командную Git-защиту сохранить как есть; остальные личные особенности не переносить в Common автоматически                                                                  |
| `AGENTS.home.md`: Nix and Fish / Home Working Directories / Home Git Convention                | Домашняя среда                                                    | `nsh`, flake paths, `/tmp/opencode`, `~/.opencode/plan`, условный ticket сохраняются; в корпоративный порт не экспортируются                                                |
| `AGENTS.home.md`: Explicit Review Requests                                                     | Домашнее личное дополнение Samov                                  | Не относится к универсальной домашней среде; переносится вместе с обновлением policy-путей и tests                                                                          |
| `AGENTS.corporate.md`: Source Exploration / Output / Formatting / Verification / User Actions  | Common, с выделением совпадающего ядра                            | Все ограничения доказательности и ресурсов сохраняются, без повторного включения одних и тех же пунктов                                                                     |
| `AGENTS.corporate.md`: Requirements Sources                                                    | Только корпоративный Common                                       | Полностью сохраняется R3-контракт: источник именно выбранной задачи, ревизия, доступ, согласованные exceptions, отсутствие источника не равно багу                          |
| `AGENTS.corporate.md`: Git Workflow                                                            | Командный Common                                                  | Нынешняя Git-защита остаётся командной по решению пользователя; Дашины файлы не переписываем                                                                                |
| `AGENTS.corporate.md`: Discussion                                                              | Убрать требование автозагрузки discussion-map из Common           | Сам skill — в личных слоях Samov дома и на Mac, ручной вызов `@discussion-map`                                                                                              |
| `AGENTS.corporate.md`: Task Log                                                                | Корпоративный Common / существующий `task-summary-log`            | Только по явному запросу, английский, `promptLogs`, optional XTracker key, дата из команды; старые логи обновлять на месте, в HM не устанавливать                           |
| `AGENTS.corporate-personal.md`                                                                 | Личное Mac-дополнение Samov                                       | Ordinary/delegated/Chrome routing остаётся личным; убрать зависимость от общих discovery-ссылок после переноса регистрации                                                  |
| `AGENTS.corporate-personal.md`: Corporate Task Convention                                      | Личное Mac-дополнение Samov                                       | Подтверждённый `FBDC-<number>` для новых веток/коммитов; history — только для остального формата, без возврата `KT-…` или переписывания истории                             |
| Прежний `decision-support.md`                                                                  | Архив `archive/decision-support/config/decision-support.md`       | Не устанавливается; активные note-правила — в описании todo-tool только Build/Plan                                                                                          |

Предлагаемые результаты композиции: домашняя основа, домашнее личное дополнение,
корпоративный Common и корпоративное личное дополнение. Текущий результат `home`
содержит обе домашние части; при разделении его consumers/tests мигрируются вместе.
Нельзя просто убрать из него личные пункты и объявить их сохранёнными в исходнике:
они должны реально загрузиться через личное дополнение.

## 5. Полная карта 37 файлов свежего Mac-снимка

Новая поставка определена в `macos/export.nix`; exporter создаёт только новый
staging-каталог и hash manifest. Protected settings/plugins и пять исторических
acceptance artifacts сверяются побайтно с `macos/sources/baseline.json`.
Это отдельный пакет, не переписанный seed/R3; порядок live diff — `macos/INSTALL.md`.

Все пути в таблицах — относительно `trf/`. «Оставить» означает сохранить именно
актуальную версию, не заменить старым seed. Карта не содержит live-типов симлинков.

### Командная папка: 21 файл

| Текущий путь                                             | Цель                                                                                                                                                                                                |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `opencode/opencode.jsonc`                                | Baseline Common: providers, модели, permissions и семь MCP; нынешние командные Git policies сохранить как есть, без личного default_agent                                                           |
| `opencode/AGENTS.md`                                     | Common: разделение из раздела 4, без личного routing                                                                                                                                                |
| `opencode/README.md`                                     | Common: обновить описание состава и независимого подключения локального JSONC; сохранить integrations/safety; в permissions указать командное согласование новых policies и изменений `git-offline` |
| `opencode/agent-skills-review-checklist.md`              | Common: сохранить человеческий checklist публикации skills                                                                                                                                          |
| `opencode/.gitignore`                                    | Common: сохранить; отдельно проверить игнор личных файлов и чувствительного состояния                                                                                                               |
| `opencode/package.json`                                  | Common: сохранить текущую структуру пакета                                                                                                                                                          |
| `opencode/package-lock.json`                             | Common: сохранить, не перегенерировать без изменения dependencies                                                                                                                                   |
| `opencode/plugins/git-offline/index.ts`                  | Common: сохранить без изменения поведения; permissions не отменяют shell-hook                                                                                                                       |
| `opencode/plugins/permissions/state.ts`                  | Common: сохранить                                                                                                                                                                                   |
| `opencode/plugins/permissions/tui.ts`                    | Common: сохранить `/allowed-permissions` и подтверждение удаления grants                                                                                                                            |
| `opencode/plugins/permission-stats/index.ts`             | Common: сохранить журнал permission decisions                                                                                                                                                       |
| `opencode/scripts/task-report.py`                        | Common: сохранить текущий Mac-отчёт и guard пустой/неподдерживаемой сессии; не подменять домашним                                                                                                   |
| `opencode/skills/discussion-map/SKILL.md`                | Перенести в `opencode-local/skills/discussion-map/SKILL.md` Samov, подключить личным JSONC; `metadata.opencode/autoinvoke: false`, ручной вызов `@discussion-map`; из Common убрать                 |
| `opencode/skills/git-regression-rollback/SKILL.md`       | Common: сохранить explicit rollback contract; наличие skill не разрешает rollback само по себе                                                                                                      |
| `opencode/skills/task-summary-log/SKILL.md`              | Common: корпоративный opt-in task log; будущий source `skills/task-summary-log/SKILL.md` обновлён под XTracker, без изменения исторического snapshot                                                |
| `opencode/skills/code-patterns-skill-generator/SKILL.md` | Common: сохранить создание проектных skills после согласования; точечные исправления описаны ниже                                                                                                   |
| `opencode/cli.json`                                      | Живые пользовательские настройки Mac, не командный шаблон поверх чужого CLI; сохранить внешний voice-plugin, UI и стандартные звуки                                                                 |
| `opencode/agents/review.md`                              | После проверки регистрации в личном JSONC убрать только общую точку входа; сохранить личного `review`                                                                                               |
| `opencode/commands/delegated-review.md`                  | Аналогично: регистрация из локального JSONC, личный шаблон не удаляется                                                                                                                             |
| `opencode/commands/delegated-review-chrome.md`           | Аналогично; пассивный audit не заменяется live browser-test                                                                                                                                         |
| `opencode/commands/problem-brief.md`                     | Предложение: оставить единственную общую команду здесь; она не запускает личный workflow. Личная копия ниже избыточна                                                                               |

### Личная папка: 16 файлов

| Текущий путь                                                             | Цель                                                                                                                                 |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| `opencode-local/opencode.jsonc`                                          | Личное Mac-дополнение: дополнить явной регистрацией собственных ролей/команд, сохранив instructions                                  |
| `opencode-local/AGENTS-personal.md`                                      | Личное Mac-дополнение: сохранить Goals, review routing, Fish и прочие личные правила; универсальные продвижения учитывать без дублей |
| `opencode-local/agents/review.md`                                        | Личный `review`: сохранить read-only, отсутствие рекурсии, прямые личные policy-пути; metadata регистрируется в JSONC                |
| `opencode-local/review-analysis.md`                                      | Личное Mac-дополнение: сохранить `evidence-v5` / `sources-v1`, контрпримеры, полный causal path и ограничения verdict                |
| `opencode-local/review-system.md`                                        | Личное Mac-дополнение: сохранить delegated read-only, fingerprint и continuity                                                       |
| `opencode-local/commands/delegated-review.md`                            | Личная команда: сохранить scope defaults, fingerprint, handoff, bounded recovery и routing                                           |
| `opencode-local/commands/delegated-review-chrome.md`                     | Личная команда: сохранить historical evidence boundary, export/privacy, запрет browser/retest                                        |
| `opencode-local/commands/problem-brief.md`                               | Побайтный дубль общей команды; не регистрировать второй раз. Исходная копия остаётся в baseline до проверки миграции                 |
| `opencode-local/problem-brief.README.md`                                 | Сохранить документацию; при согласовании общей команды перенести её описание в Common, не теряя сценарии                             |
| `opencode-local/delegated-review.README.md`                              | Личная документация Samov                                                                                                            |
| `opencode-local/delegated-review-chrome.README.md`                       | Личная документация Samov                                                                                                            |
| `opencode-local/update-2026-11-16/INSTALL.md`                            | Историческая документация R3, не инструкция применения новой версии                                                                  |
| `opencode-local/update-2026-11-16/acceptance/goals-and-approach.md`      | Сохранить regression-сценарии личного поведения                                                                                      |
| `opencode-local/update-2026-11-16/acceptance/requirements/candidate.mjs` | Сохранить fixture требований                                                                                                         |
| `opencode-local/update-2026-11-16/acceptance/requirements/SPEC.md`       | Сохранить fixture-контракт                                                                                                           |
| `opencode-local/update-2026-11-16/acceptance/requirements/EVALUATION.md` | Сохранить source/model acceptance-сценарии; новые проверки дополняют, не заменяют старые                                             |

Точечные кандидаты на исправление `code-patterns-skill-generator`:
путь определяет skill ID, не frontmatter `name`; распространённость паттерна не
доказывает его корректность; `metadata` допустима в V2; shell fallback не должен
противоречить `rg`/`fd`; обычное обновление config не требует рестарта сервиса.
Это предлагаемые исправления совместимости/инструкций, не уже внесённые изменения.

## 6. Домашняя поставка: что сохраняется и где подключается

Пути — относительно `home/apps/opencode/`. Дом остаётся HM-managed, даже если
личные настройки физически устанавливаются в соседний `opencode-local`.

| Исходники                                                                                                                                   | Домашнее назначение / граница                                                                                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `default.nix`                                                                                                                               | Установка основы и личного дополнения, явная композиция; без копирования корпоративного JSONC                                                                                                              |
| `package.nix`, активные `patches/*.patch`, `patches/session-attention.ts`                                                                   | Домашний binary и принятые fixes, без переноса в официальный Mac binary; актуальный набор определяет package.nix                                                                                           |
| `config/v2-settings.nix`, `config/v2-base-settings.nix`                                                                                     | Первый сохраняет канонические домашние значения; второй исключает только model/agents для базы, сохраняя providers, limits, policies/permissions и compaction                                              |
| `config/personal-layers.nix`                                                                                                                | Реальные home/corporate settings и файлы; домашние роли/модели сохранены в личном JSONC, Mac review/research наследуют родителя                                                                            |
| `config/instructions.nix`, `config/AGENTS*.md`                                                                                              | Реализованы homeBase/homePersonal и corporate/corporatePersonal; общий regression-view home сохраняет прежние правила с явными path/delegation migrations; Mac export использует только corporate-варианты |
| `config/review-analysis.md`, `config/review-system.md`                                                                                      | Домашнее личное дополнение, с согласованными путями consumers; не корпоративный Common                                                                                                                     |
| `commands/delegated-review.md`, `commands/delegated-review-chrome.md`                                                                       | Домашнее личное дополнение; команды и routing сохраняются                                                                                                                                                  |
| `commands/problem-brief.md`, `problem-brief.README.md`                                                                                      | Переносимая общая команда, доступна дома и в Common                                                                                                                                                        |
| `DELEGATED-REVIEW.md`, `DELEGATED-REVIEW-CHROME.md`                                                                                         | Документация личного workflow, обновить только затронутые пути                                                                                                                                             |
| Прежние `decision-support.nix`, `config/decision-support.md`, `skills/decision-check/SKILL.md`                                              | Перенесены побайтно в `archive/decision-support/`, без активного подключения                                                                                                                               |
| `todo.nix`, `config/todo-settings.nix`, `plugins/agent-todo.ts`, `agent-todo-instructions.ts`, `agent-todo-review.ts`, `agent-todo-tui.tsx` | Todo только Build/Plan, без global instruction; сохранить native consent, весь batch, feedback, visits, dates, manual edits, Git-local commit; не переносить на корпоративный Mac                          |
| `plugins/model-routing/{tui.ts,model-routing.ts,routing-models.json}`                                                                       | Домашние `/switch-free` / `/switch-paid`, таблица моделей и ручной выбор сохраняются; не добавляются в корпоративный Common                                                                                |
| `plugins/limits/{index.ts,tui.tsx,policy.ts,rpc.ts,writer.ts}`                                                                              | Домашние limits/accounting, включая текущие ограничения token-sharing; не терять warning/removal contract                                                                                                  |
| `plugins/git-offline.ts`                                                                                                                    | Домашняя safety-основа, текущий plugin ID и поведение сохраняются                                                                                                                                          |
| `plugins/permissions/{state.ts,tui.ts}`, `plugins/permission-stats.ts`                                                                      | Домашние permissions UI/history сохраняются; общий исходник возможен без смены поведения                                                                                                                   |
| `plugins/model-calls.ts`, `scripts/task-report.py`                                                                                          | Домашняя диагностика, model-calls остаётся выключенным по умолчанию; старые журналы не удаляются                                                                                                           |
| `plugins/skill-stats.ts`, `scripts/skill-stats.py`                                                                                          | Домашний учёт skills, без автоматического экспорта на Mac                                                                                                                                                  |
| `plugins/workspace-context.ts`                                                                                                              | Домашняя Linux-функциональность, без переноса в корпоративный Common                                                                                                                                       |
| `plugins/quiet-urgency.ts`, `scripts/silent-attention.py`, `sounds/*`                                                                       | Только домашние notifications/audio; Mac не получает anime sounds или quiet-urgency                                                                                                                        |
| `skills/discussion-map/SKILL.md`                                                                                                            | Домашний личный skill Samov, HM-managed; `metadata.opencode/autoinvoke: false`, ручной вызов `@discussion-map`, без требований автозагрузки                                                                |
| `skills/git-regression-rollback/SKILL.md`                                                                                                   | Существующий переносимый skill, ограничения применения сохраняются                                                                                                                                         |
| `README.md`, `BENCHMARK.md`, `tests/**`                                                                                                     | Сохранить историю и guards; обновить tests совместно с реальным изменением подключения, не ослаблять ради зелёного результата                                                                              |
| `archive/**`                                                                                                                                | История, не устанавливается и не восстанавливается в активный runtime                                                                                                                                      |
| `macos/opencode/**`, `macos/opencode-local/**`, `macos/trf-review/**`                                                                       | Старый seed/R3 остаются историческими источниками; не использовать как полный актуальный Mac-export                                                                                                        |

В этой таблице `agent-todo-*` перечислены внутри `plugins/`, а `sounds/*` включает
запасной `completion-sound[wow].mp3`, который не становится установленным.
Первоначальная карта учитывала шесть patches: `session-routing.patch`, `manual-model-routing.patch`,
`model-variants.patch`, `session-attention.patch`, `question-location.patch`,
`theme-mode-cache.patch`. В текущей подготовке 2.4.0 package.nix применяет пять:
theme-cache fix уже upstream, исторический patch сохранён. Эта работа не меняет
набор patches или их removal contracts; routing адаптирован к общему select 2.4.0.

Домашние TUI-only plugins могут оставаться в штатной глобальной discovery-папке
как пользовательские функции этой установки. Это не делает их корпоративным
Common. Todo/combined plugin уже подключён явно из личного JSONC и устанавливается
в `opencode-local/plugins/agent-todo` одной directory derivation; приёмка на целевом binary впереди.
Выключение локального дополнения не должно случайно выключить Git-offline/safety.

Текущее состояние: HM wiring выполнен в исходниках, старые домашние global
discovery-определения personal commands/policy/skill убраны. 127 focused checks и
пять isolated generated-files runtime cases на 2.1.4 прошли. Это не full pinned-HM
merge/build, не runtime 2.4.0 и не живая migration. Корпоративный Common/export и
shared-skill adjustments готовы в `macos/export.nix`; Mac type/runtime acceptance впереди.
Подробное покрытие — [PERSONAL-LAYER.md](PERSONAL-LAYER.md).

## 7. Справочный инвентарь Даши — EXAMPLE ONLY

Пути ниже — относительно корня frontAgents. Оба исходных архива сохраняются.
**Все перечисленные файлы остаются без изменений и вне реализации этой задачи.**
Колонки описывают назначение примера, а не план адаптации или разрешения Samov.

### Агенты: 16 файлов

Все принадлежат её набору с прежними ID. Наличие в инвентаре не доказывает
совместимость с конкретной установленной версией V2; её набор мы не мигрируем.

| Путь                                 | Назначение примера                                           |
| ------------------------------------ | ------------------------------------------------------------ |
| `agents/dev.md`                      | Основной оркестратор Даши                                    |
| `agents/task-reader.md`              | Разбор задачи                                                |
| `agents/backend-contract.md`         | Извлечение backend-контракта                                 |
| `agents/xtracker-sync.md`            | Синхронизация карточки                                       |
| `agents/feature-dev.md`              | Реализация frontend-задачи                                   |
| `agents/mr-maintainer.md`            | Сопровождение MR                                             |
| `agents/gitlab-conflict-resolver.md` | Разрешение конфликтов                                        |
| `agents/review-responder.md`         | Обработка замечаний                                          |
| `agents/bug-fixer.md`                | Исправление дефектов                                         |
| `agents/browser-tester.md`           | Live browser-test, отличный от пассивного Chrome-audit Samov |
| `agents/code-reviewer.md`            | Её reviewer, не личный `review` Samov                        |
| `agents/bug-investigator.md`         | Диагностика                                                  |
| `agents/refactor.md`                 | Рефакторинг                                                  |
| `agents/contract-checker.md`         | Сверка frontend/API                                          |
| `agents/autotest-impact.md`          | Оценка влияния на тесты                                      |
| `agents/test-deployer.md`            | Раскатка на тестовый контур                                  |

Её permissions не заменяют настройки Samov, но и настройки Samov не должны
блокировать её собственные overrides. Цепочки делегирования не уплощаем.
Глубина subagent в V2 — отдельная настройка; это compatibility-фактор для Common,
а не поручение переделать её оркестрацию. Фактическую работоспособность всего
frontAgents на V2 не проверяли и не обещаем без соответствующей приёмки.

### Skills и references: 18 файлов

| Путь                                                           | Назначение примера                                                                         |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `skills/task-analysis/SKILL.md`                                | Анализ требований; кандидат для отдельного личного аналога Samov                           |
| `skills/browser-verification/SKILL.md`                         | Проверка в браузере; кандидат для отдельного личного аналога Samov                         |
| `skills/bug-localization/SKILL.md`                             | Диагностика; кандидат для отдельного личного аналога Samov                                 |
| `skills/delivery-workflow/SKILL.md`                            | Её workflow доставки без адаптации под Samov                                               |
| `skills/delivery-workflow/references/frontend-repositories.md` | Корпоративные проектные сведения, доступные её workflow; не домашние глобальные инструкции |
| `skills/delivery-workflow/references/backend-repositories.md`  | Аналогично; не публиковать внутренний реестр как переносимый общий skill                   |
| `skills/delivery-workflow/references/repositories.md`          | Правила выбора проекта, у Даши; общее доказательство применимости — в ядре                 |
| `skills/delivery-workflow/references/integrations.md`          | Её интеграционные контракты                                                                |
| `skills/frontend-conventions/SKILL.md`                         | Её frontend-соглашения                                                                     |
| `skills/component-anatomy/SKILL.md`                            | Её структура компонентов                                                                   |
| `skills/fsd/SKILL.md`                                          | FSD по её выбору; Common не запрещает                                                      |
| `skills/solid/SKILL.md`                                        | SOLID по её выбору; Common не запрещает                                                    |
| `skills/clean-code/SKILL.md`                                   | Её правила clean code                                                                      |
| `skills/mobx/SKILL.md`                                         | MobX                                                                                       |
| `skills/vuex/SKILL.md`                                         | Vuex                                                                                       |
| `skills/react-performance/SKILL.md`                            | React performance                                                                          |
| `skills/review-checklist/SKILL.md`                             | Её checklist, независимый от review-policy Samov                                           |
| `skills/test-deployment/SKILL.md`                              | Её deployment workflow                                                                     |

Не создаём в Common одноимённые skills на основе её исходников сейчас.
Если позже Samov выберет личные аналоги, их содержание/ID согласуем отдельно,
не меняя её skills, references или способ подключения.

### Tools, templates и поддержка: 31 файл

| Пути                                                                                                  | Цель                                                                                                                 |
| ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `tools/doctor/doctor.py`, `tools/doctor/test_doctor.py`, `tools/doctor/README.md`                     | Её preflight; не объединяет inherited configs, поэтому его missing не доказывает отсутствие настройки в OpenCode     |
| `tools/run-checks/run-checks.sh`, `tools/run-checks/test_run_checks.py`, `tools/run-checks/README.md` | Её project-check runner                                                                                              |
| `tools/swagger-diff/swagger_diff.py`, `tools/swagger-diff/README.md`                                  | У неё; помощь для конкретного snapshot API, не доказательство отсутствия будущего API                                |
| `tools/autotest-impact/autotest_impact.py`, `tools/autotest-impact/README.md`                         | У неё; источник тестов передаётся явно, никаких обязательных соседних клонов                                         |
| `tools/git-task/git_task.py`, `tools/git-task/test_git_task.py`, `tools/git-task/README.md`           | Её Git workflow с fetch/push; исходники не меняем, но под принятой командной Git-защитой сетевые операции не обещаем |
| `templates/task-plan.md`                                                                              | Её workflow; контракт, provenance и progress полезны, но не обязательный шаблон каждого разговора                    |
| `templates/browser-report.md`                                                                         | Её browser-report; идея структуры доказательств для личного аналога Samov                                            |
| `templates/bug-comment.md`                                                                            | Её комментарий о дефекте                                                                                             |
| `templates/mr-description.md`                                                                         | Её описание MR                                                                                                       |
| `templates/review-replies.md`                                                                         | Её шаблон ответов                                                                                                    |
| `templates/test-deployment.json`, `templates/test-deployment-report.md`                               | Только отдельная раскатка; шаблон не доказательство существования окружения/CI jobs                                  |
| `templates/lessons.md`, `templates/decisions.md`                                                      | Необязательные проектные записи; не создавать автоматически для всех и не заменять существующие                      |
| `templates/AGENTS.md`                                                                                 | Её проектные инструкции; не переписываем                                                                             |
| `templates/opencode.json`                                                                             | Её пример конфигурации; не заменяем новым overlay                                                                    |
| `install.sh`                                                                                          | Её установщик; не запускаем и не изменяем                                                                            |
| `plugin/notify.ts`, `plugin/README.md`                                                                | Её plugin/reference; совместимость его API с V2 не подтверждена                                                      |
| `AGENTS.md`, `ARCHITECTURE.md`, `README.md`, `.gitignore`                                             | Документация/правила самого frontAgents; не становятся глобальными инструкциями рабочих проектов                     |

Суммарно: 16 agents + 18 skill/reference files + 31 прочий файл = 65.
Tools не запускались; эта карта не является их correctness/security review.

### Второй пакет Даши не выбрасываем

У 40-файлового пакета нет уникальных путей относительно расширенного, но 24 файла
отличаются по содержимому. Это не просто два имени одного архива. Отличия затрагивают
Kaiten/XTracker, инструменты браузера, ветки/base/target, источник API, внешние тесты,
workflow публикации, шаблоны, permissions и коды неполного прогона checks.

Для проектирования используем расширенный вариант как более полный набор
возможностей, **не утверждая, что это хронологически последняя версия Даши**.
Ничего не объединяем, не восстанавливаем и не исправляем в обоих вариантах.
Сравнение помогает выбирать идеи для Samov, но не даёт поручений Даше.

## 8. Кандидаты для личных правил Samov, не для обязательного Common

Для Samov предложен обычный инженерный язык вместо обязательного FSD/SOLID.
Это не запрещает Даше включить FSD/SOLID в своём слое. Кандидаты:

- Соблюдать проверенные границы модулей и направление зависимостей проекта;
  не вводить новую организацию файлов ради текущего изменения.
- Использовать подходящий публичный контракт, а не внутренние детали соседа.
- Разделять ответственность, когда это облегчает понимание, независимые изменения
  или тестирование; не дробить код только по числу строк.
- Делать внешние зависимости и существенные побочные эффекты понятными.
- Вводить интерфейсы/обёртки только ради конкретной изоляции, замены или проверки,
  не оборачивать каждую библиотеку «на будущее».
- Проверять контракт и требуемую версию по источникам; будущая и развёрнутая
  версии различаются. Тестирование одной не подтверждает другую.
- При продолжении сверять сохранённые планы, IDs и результаты с текущим состоянием;
  после неизвестного результата внешней записи не повторять её вслепую.

Дома это применимо к Nix-модулям, scripts и plugins без корпоративной архитектуры.
Формулировки должны дополнить, а не продублировать нынешние Engineering Choices.
Подробности анализа задач и браузера — по task-specific commands,
без обязательной загрузки всего набора перед каждой правкой.

Сравнение P5 записано в [чек-листе](CONFIG-CHECKLIST.md): содержание компактных
личных `task-analysis` и `browser-verification` одобрено; новых агентов и отдельный
`bug-localization` не добавляем. Обе процедуры — команды `/task-analysis` и
`/browser-verification` текущей сессии, без skill-дублей и overrides агента/модели.
Общая процедура не зависит от Playwright; текущий доступный инструмент — Chrome MCP.
Возможный Playwright-вход — отдельное будущее решение, не новый MCP в этой работе.
Не переносить FSD/трекер/delivery workflow; живой тест не заменяет пассивный аудит.
Созданы английские `commands/task-analysis.md`, `commands/browser-verification.md`
и отдельные русские `task-analysis.README.md`, `browser-verification.README.md`.
Шесть source-checks и изолированная
регистрация реальных тел на 2.1.4 прошли. Личный overlay и домашний HM wiring теперь
готовы в исходниках; модельная приёмка и живая проверка браузера ещё впереди.
Дашины пакеты не менялись.

Отдельная scoped правка трекера подготовлена в corporate sources нового экспорта:
XTracker для требований/логов и личный `FBDC-…` для веток/коммитов Samov.
Это не удаление MCP-KAITEN и не обновление исторического seed/R3; staging Mac-export
проверен, но не является принятой живой миграцией;
домашняя реализация в исходниках отражена в разделе 6 и текущем итоге ниже.

## 9. Что ещё требует отдельного решения

### Общие роли — P4 согласован

Решение пользователя: сохранить встроенные `build`, `plan`, `general`, `explore`
без новых специальных настроек в Common. Это не добавление агентов, а сохранение
штатного поведения. Общие permissions/policies и нынешняя настройка `title`
сохраняются. Личные домашние настройки этим не отменяются. Исходные различия:

- Дома `explore/research/review` имеют личные prompts, permissions и model routing.
- На Mac `review` фактически личный; глобально настроен только maintenance `title`.
- У Даши есть отдельные `code-reviewer`, `backend-contract`, `browser-tester`.

Домашний `research` сохраняется. В целевом личном Mac-дополнении Samov также
используем существующий контракт `research`: отдельный анализ источников/гипотез,
без редактирования и дальнейшего делегирования. Определение подключается штатно
через личный JSONC; домашняя model routing не переносится. Это целевой план,
не утверждение о наличии `research` в нынешнем Mac-снимке и не выполненная установка.

На этапе карты ничего не унифицируем. Возможный общий анализ/skill не требует
общего агента. Перенос роли в Common допустим лишь после удаления личных
зависимостей и отдельного согласования её контракта. До этого общая инструкция
не обязана ссылаться на несуществующие общие `research/review`.

### Decision-support и контекст специалистов

Перенос подробных правил из global `instructions` в skill позволяет загружать
их по задаче, но не гарантирует постоянное прежнее conversational поведение.
Скрыть/запретить личные skills/tools специалистам можно role-scoped permissions;
это дополнительные ограничивающие правила, не пересмотр базовой безопасности.
Любое изменение scoping нужно согласовать, а не внести под видом простого
перемещения Markdown. Нынешние permissions — baseline, не запрет на overrides.

Без неё нельзя обещать, что specialist вообще не увидит доступный личный skill.
Фраза «не применяй» в глобальном тексте не означает отсутствия текста в контексте.
Недокументированного `agents.<id>.instructions` не вводим. Build/Plan `system`
ради этого не заменяем. Plan сохраняет запрет записи, todo — native confirmation.

Исходное состояние P6: прежний `decision-support.nix`
подключает все 65 строк через глобальный `settings.instructions`, а todo-плагин
регистрирует инструменты независимо от роли. Перенос этого массива в личный
JSONC сам по себе не отделяет его от личных research/review/explore/general.
Документированные `instructions` общие; непустой agent `system` заменяет штатный
provider prompt, поэтому не используем его как добавочный role-scoped текст.

Отклонённый вариант: оставить короткий домашний trigger с явным назначением
Build/Plan и вынести подробный note-workflow в подгружаемый личный skill.
Пользователь требует исключать ненужный специалистам контекст полностью, без
остаточного глобального trigger; полезное поведение todo сохранить. Затем явно
одобрено архивирование Decision Support/`decision-check`, но не отключение todo.

Реализовано в исходниках: отделить заметки от decision guidance. Полный
контракт заметок хранить в описаниях существующих todo-tools, разрешённых только
Build/Plan, без нового skill и глобального instruction. Возможность уместно
предлагать сохранение идеи сохранить в их описаниях; чтение/запись остаются только
после запроса/согласия, запись — native consent и действующие ограничения Plan.
Нативный tool
snapshot 2.1.4/2.3.0 исключает полностью denied actions из доступного набора;
у todo-tools не задан иной `options.permission`, поэтому используется имя tool.
Глобального trigger нет. Приватный runtime на установленной 2.1.4 с локальным mock
провайдером подтвердил note-tools/полный workflow только у Build/Plan, отсутствие
у general/explore/research/review, отсутствие Decision Support/skill. Реальные
LLM/MCP, запись заметок и живой сервис не использовались. Это не приёмка выбора
инструментов настоящей моделью, runtime 2.3.0 или новой полной структуры overlay.
Пользователь подтвердил обычный вход «добавь в todo»; спонтанное автосохранение
идей не требуется и не добавлено. Архив сохранён побайтно; HM activation не выполнена.

### Совместимость с внешними browser MCP

Существующий `Chrome MCP` сохраняется с прежним именем. Её Playwright предполагает
изолированный браузер, другие инструменты и профиль. Это не эквивалентные настройки.
Не подключаем оба Samov автоматически и не переименовываем общий сервер.
Common не должен запрещать Даше добавить собственный Playwright. Её browser flow
не адаптируем. Пассивный Chrome-audit Samov не затрагивается.

### Discussion-map и MCP по провайдеру

Факты, ограничения и варианты записаны в [чек-листе](CONFIG-CHECKLIST.md).
Для discussion-map согласованы личные слои Samov дома и на корпоративном Mac,
ручной вызов и исключение из Common. Регистрация в `config/personal-layers.nix`
подключена домашним HM и включена в полный корпоративный staging-export.
Ограничение MCP по провайдеру исключено пользователем из текущего обновления:
не выбирать гарантию, не разрабатывать guard и не менять подключение MCP в рамках
этой работы. Исследование в чек-листе сохранено только для отдельных будущих задач,
не как зависимость или критерий приёмки разделения конфигураций.

## 10. Как проверять, что ничего не потеряно

Это общий план приёмки, не утверждение о прохождении всех пунктов;
выполненные focused-проверки и ограничения перечислены отдельно:

1. Зафиксировать hash/type manifest актуальных входов, включая уже изменённые
   домашние файлы и живые типы Mac-entrypoints. Не использовать старый R2/R3
   snapshot как базу нового patch. Сохранить оба исходных архива Даши.
2. Для каждого существующего правила/публичного имени составить соответствие
   старый источник → новый реально загружаемый источник. Отдельно отмечать
   обобщение, дедупликацию, неактивируемую возможность и изменение поведения.
3. Сравнить permissions/policies и safety-plugin IDs/поведение по каждой среде,
   включая итоговые role permissions и wrappers. Различать одобренный override /
   перенос личных настроек и случайную потерю. Командную Git-защиту не менять.
4. Проверить независимые fixtures: Common без локального слоя; Common + Samov;
   домашняя основа + домашнее дополнение Samov. Отдельная синтетическая fixture
   чужого overlay проверяет overrides, skills и делегирование без правки/запуска
   Дашиного набора. Проверить отсутствие личных файлов и смену default agent.
5. Проверить наличие всех семи нынешних Mac MCP и отсутствие второго подключения
   с иными ID; auth не читать и не экспортировать. Model/MCP live-приёмка отдельно.
6. Сохранить R3 requirements/Goals и review-regression fixtures: ordinary против
   delegated, fingerprint/recovery, passive audit против live browser-test.
   Новые пути не являются основанием удалить старые поведенческие сценарии.
7. Проверить домашние routing/limits/todo/attention и CLI persistence точечно;
   Mac не получает домашние звуки, Nix и отключённые/устаревшие plugins.
8. Подготовить scoped diff только после согласования карты. Проверить forward/
   reverse на fixture с реальными типами путей, конфликт базы и повторное
   применение; не удалять личные файлы до проверки новой регистрации.
9. Передать человеку отдельные проверки поведения на Mac и дома. Не называть
   source-fixtures доказательством соблюдения инструкций моделью. Build/switch,
   remote Git и live deployment остаются за пользователем/отдельным разрешением.

### Что выполнено при составлении карты

Прочитаны актуальные инструкции и wiring HM, R3-документация, рабочие файлы
предоставленного Mac-снимка по затронутым темам, ключевые skills/workflow и
интеграционные контракты Даши. Механически проверены SHA256 архивов, состав
37/65/40 файлов, 12 R3-совпадений, четыре пары одинаковых entrypoints и отличия
Mac/home task-report. Использованы V2 guides по config, agents, skills, CLI и
plugin loading и migration; доступность всей композиции на целевых версиях ещё
не проверена. На момент первой карты база была 2.1.4; после согласованной реализации
домашние package/patches/lock используют upstream 2.4.0. Пользователь уточнил:
на живом Mac уже 2.4.0; это не runtime-приёмка нового слоя. Механическая проверка
первой карты подтвердила явное наличие в ней всех 37
Mac-путей и всех 65 путей расширенного пакета Даши. Это проверка учёта файлов,
не доказательство сохранения runtime-поведения. Изначально Prettier был недоступен;
финальные авторские файлы отформатированы установленным CLI 3.10.1 без установки зависимостей.

Не запускались конфиги/скрипты из архивов, агенты, MCP, браузер, pipeline, builds,
activation, formatter с установкой зависимостей или remote Git. Не менялись
живые конфиги, исходные архивы, история Git и ранее существовавшие правки.

## 11. Порядок согласования

1. Пользоваться [CONFIG-CHECKLIST.md](CONFIG-CHECKLIST.md): за один раз обсуждать
   только небольшой/средний пакет, не требовать одобрения всей карты сразу.
2. Git-защита остаётся командной как есть; discussion-map — личный, с ручным вызовом.
   P4 согласован: штатные агенты без новых специальных настроек Common.
   MCP по провайдеру вне этого обновления; далее — P5, личные агенты/skills Samov.
3. Конкретные реализации Common и личных слоёв Samov согласовывать отдельными
   пакетами. Идеи личных специалистов рассматривать позже; Даша вне реализации.

### Личный слой и HM wiring в исходниках; без установки

`config/personal-layers.nix` возвращает `home`/`corporate`, каждый с `.settings`
и `.files`. Личные команды явно зарегистрированы в JSONC, `{file:...}` содержит
только тела. Все домашние роли/модели и permissions сохранены; Mac получает только
review/research без model overrides. `/problem-brief` остаётся общим. `discussion-map`
личный с `autoinvoke: false`. Todo включён только дома, явно через относительный
`./plugins/agent-todo`; четыре исходных plugin-файла входят в набор. Интерфейсные
настройки, providers, MCP, team policies/`git-offline` не переносятся в личный JSONC.

127 focused Node checks прошли. Runtime на установленной 2.1.4 материализовал
реальные `.files` и проверил Common-only/home/corporate/home без todo/home-hm-layout
из постороннего CWD без discovery-симлинков; последний case — custom XDG и store-like
directory-link todo, без Nix realization. Полные команды и agent systems разрешились; todo активен под
прежним ID; mock-запросы подтвердили note-workflow только Build/Plan и отсутствие
авторекламы discussion-map. Common-only не обнаруживает соседние личные определения.
Settings — минимальный нейтральный fixture с настоящим `git-offline` и реальными
новыми instruction texts, не полный HM merge или корпоративная интеграция семи MCP. Политики reviewer проверены как
файлы/системы, не как исполненный review workflow. Подробности — [PERSONAL-LAYER.md](PERSONAL-LAYER.md).

Нейтральный instruction core, отдельные homeBase/homePersonal и домашний HM wiring
готовы; старые личные discovery-определения исключены из домашней установки.
Новые base-settings сохраняют providers/safety/compaction, personal JSONC сохраняет
модели/роли/команды и домашний opt-in todo. Full pinned-HM merging/build и целевая
runtime-приёмка ещё не выполнены. Выполнение команд,
передача аргументов, live agent/model inheritance, TUI и real-model/browser tests,
runtime 2.4.0 и живой Mac ещё не проверены. Ничего не установлено/активировано,
сборок и коммита нет; прежние сторонние изменения сохранены.
