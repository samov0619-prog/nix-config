# Личный слой Samov — декларативное подключение

`config/personal-layers.nix` описывает два набора файлов для `opencode-local/`:
`home` и `corporate`. Это сборка текстов и штатных settings на этапе Nix evaluation,
не runtime-загрузчик, installer или новый OpenCode plugin. JSONC получается через
`builtins.toJSON`. Домашний `default.nix` уже подключает этот результат декларативно;
Linux HM-сборка пользователя и isolated runtime/PTY 2.4.0 прошли; activation нет,
живые конфигурации не менялись. Последующий reporting-script fix требует пересборки.
Корпоративный
результат включён в отдельный полный staging-export `macos/export.nix`.

## Состав

- Личные инструкции, review policies и роли. Дома сохранены нынешние модели,
  ограничения и prompts; корпоративные review/research наследуют модель родителя.
- Четыре команды: `/delegated-review`, `/delegated-review-chrome`, `/task-analysis`,
  `/browser-verification`. Metadata — в JSONC, относительные `{file:...}` загружают
  только Markdown-тела. YAML-frontmatter проверяется и снимается при сборке текста.
- `/problem-brief` остаётся общей командой и здесь не дублируется.
- Личный `discussion-map` с `metadata.opencode/autoinvoke: false`; ручной вход —
  `@discussion-map`. Путь skills не зависит от проекта: `~/` в standalone-результате,
  абсолютный `config.xdg.configHome` в HM.
- Только дома: todo-plugin с сохранённым ID, всеми server/TUI-зависимостями и
  доступом к tools только Build/Plan. `todoEnabled = false` исключает весь этот
  набор. Decision Support не возвращается из архива.
- У каждой новой команды собственные русские пояснения:
  `task-analysis.README.md` и `browser-verification.README.md`.

Личный JSONC не определяет providers, MCP, общие safety policies или CLI-настройки.
Домашние routing/limits/audio и корпоративный внешний voice-plugin не заменяются.
Семь корпоративных MCP и `git-offline` остаются в базе. Общая конфигурация не должна
ссылаться на файлы этого дополнения; без него Common должен работать самостоятельно.

## Подключение

HM устанавливает нейтральные settings из `config/v2-base-settings.nix` и инструкции
`homeBase` в глобальный `opencode/AGENTS.md`. Providers, safety, compaction и домашние
TUI-only plugins сохранены. Личные модели/роли исключены только из базовых settings;
их исходник остаётся в `v2-settings.nix`, откуда генератор берёт прежние значения.

`opencode-local/` содержит личный JSONC, инструкции, policies, тела ролей/команд и
ручной skill. `home.sessionVariables.OPENCODE_CONFIG` указывает на этот JSONC с учётом
`config.xdg.configHome`; прежние глобальные review-команды/policy и discussion-map
больше не объявлены в установке. Todo устанавливается одной directory-ссылкой
`opencode-local/plugins/agent-todo`, чтобы относительные импорты Bun оставались
в одном store-каталоге. Его tool permissions находятся только в личном JSONC.

Для standalone Mac подключение остаётся штатным:

```fish
set -gx OPENCODE_CONFIG "$HOME/.config/opencode-local/opencode.jsonc"
```

Переменную должен получить server-процесс, не только новая вкладка терминала.
`OPENCODE_CONFIG_DIR` на личную папку не направляется. `cli.json` остаётся отдельным
пользовательским файлом: звук, UI и голосовой ввод этим JSONC не переопределяются.

Общие инженерные правила вынесены в `AGENTS.common.md`. Goals, Fish, collaboration
и личное routing — в `AGENTS.md`; домашний review-workflow — в `AGENTS.review.md`.
`instructions.nix` отдельно предоставляет `homeBase`, `homePersonal`, их объединённый
`home` для проверок, `corporate` и `corporatePersonal`. Корпоративные Git/requirements/
task-log contracts сохранены, автоматический discussion-map routing удалён.

Это пока **не принятая миграция корпоративной установки**: полный Common/export
и shared skills подготовлены, но живые file/symlink types и интеграции не проверены. Нельзя просто
добавить overlay к прежним discovery-копиям и объявить её законченной. Исторические
Mac acceptance-файлы, seed и R3 не заменяются новым набором.

## Проверено

`tests/test_personal_layers.mjs` проверяет оба результата Nix evaluation: реальные
тела команд/policies, сохранность домашних ролей/моделей/ограничений, отсутствие
домашних зависимостей на Mac и полное исключение todo при `todoEnabled = false`.
`tests/test_home_wiring.mjs` проверяет реальные выходы модулей Linux/Darwin, custom
XDG, оба состояния todo, отсутствие старых entrypoints и сохранность базовых
settings/моделей. Это ограниченная evaluation с lazy/stubbed package constructors,
не полное слияние pinned HM. Общий focused-прогон: **127 Node-проверок**.
Контроль прежних 68 домашних пунктов/hash сохраняется после точного обратного
преобразования согласованных path/delegation migrations; это не побайтное равенство
всего нового текста прежнему.

`tests/test_personal_layers_runtime.py` материализует именно `.files` генератора,
не переписывая его JSONC; повторный прогон на собранной **2.4.0+44aed4f** прошёл все пять
вариантов: Common-only, home, corporate, home без todo и `home-hm-layout`.
Последний использует custom XDG и directory-link к store-like todo bundle, не
realization Nix derivation. Приватный сервер запускается из постороннего CWD;
личные файлы доступны через `OPENCODE_CONFIG`, без discovery-симлинков.
Проверены регистрация четырёх команд, `{file:...}`-тела, системы/ограничения review/research,
домашние model references и путь личной инструкции. `./plugins/agent-todo`
разрешается относительно JSONC и активируется с прежним ID `local.agent-todo`;
общий `local.git-offline` остаётся активен во всех вариантах.

Локальный mock подтвердил загрузку реальных новых базовых/личных текстов, отсутствие рекламы ручного
`discussion-map` и видимость todo-tools/полных правил только у Build/Plan.
Common-only не подхватывает соседние личные роли, команды, skill и плагин.
Settings этого теста — **минимальный нейтральный Common-fixture**, не итоговый Common
и не полный корпоративный набор с семью MCP. Дополнение fixture проверяет 48 native
command API calls: четыре команды × Build/Plan/Review × точные/пустые аргументы ×
home/corporate. Агент/provider/model/low variant сохраняются в сессии и запросе,
непреднамеренных детей нет. Корпоративные review/research запущены native subagent
без model override; наследование модели/variant и фактическое чтение обеих review
policies проверены. Tool choices задаёт mock, не настоящая модель.

Пользователь подтвердил уже установленную Mac-версию **2.4.0**; домашняя 2.4.0
подключена отдельным upstream input и lock. Пользователь подтвердил успешную Linux
HM-сборку; isolated 2.4.0 runtime/PTY прошли, включая новое todo-размещение и native
consent/Plan guard, built plugin closures, тему и attention двух окон.
`test_personal_limits_tui.py` также проверил в обоих личных слоях native
autocomplete/выбор/отправку `@discussion-map`: настоящее тело skill сохранено во
вложении user message и передано модели без model tool call. Built limits отрисовал
pending/ready, Active:0 и muted/blue/absent compaction marks, включая другую сессию
и home footer. Проценты живой квоты и ненулевой Active здесь не проверялись.
Generated home command прошёл также native recovery-fixture на 2.4.0: один 429
обработан native retry, terminal error после 11 failures доставлен фоновым отчётом,
после 20-секундной паузы продолжен тот же ребёнок с сохранённым read evidence.
Не проверены реальный Mac, браузер, reviewer reasoning/полный recovery budget и выбор todo
настоящей моделью. Пересборка после accounting-fix подтверждена, новый wrapper
прошёл CLI fixture; покрытие — в [BENCHMARK.md](BENCHMARK.md#built-linux-240-isolated-acceptance-2026-11-23).
Ни activation, ни коммит не выполнялись; Darwin не собран.
Изменённые Nix-файлы отформатированы pinned `nix fmt --offline --no-write-lock-file`;
Последующий проход использует установленный Prettier 3.10.1; Ruff на PATH не найден.

Порядок дальнейшей проверки:

1. Проверить diff: сборка, пересборка accounting-fix и перечисленная isolated
   acceptance уже прошли. Последующие tests/docs runtime не меняют; общий unstable
   ради OpenCode не обновляется.
2. Отдельно согласовать проверки реальных моделей/reviewer workflow/MCP/browser;
   scripted mock не подтверждает принятие моделью решений по инструкциям.
3. Выполнить остановленный согласованный backup по [UPGRADE-240.md](UPGRADE-240.md).
   В согласованное окно применить HM пользователем, убедиться, что server получил
   `OPENCODE_CONFIG`, проверить отсутствие старых entrypoints, ручной skill и todo
   consent/Plan guard. Изменённые config-файлы перечитываются штатно; одна новая
   переменная в терминале ещё не доказывает её наличие у уже работающего server.
4. До применения Mac-пакета сверить live file/symlink types по `macos/INSTALL.md`
   и провести приёмку на подтверждённой
   2.4.0, сохранить семь MCP,
   voice/CLI, policies/`git-offline` и провести отдельную приёмку. Изменение командной
   Git-защиты требует согласования с командой. Этот исходник ничего не активирует.
