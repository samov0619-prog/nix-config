# OpenCode 2.1.4

Домашний Home Manager module для laptop/desktop. OpenCode закреплён отдельным
flake input `github:anomalyco/opencode/v2.1.4` (rev `68bc26b7da1990ce10ffecfbc1e09eb13aa5d824`),
без обновления всего nixpkgs-unstable. Официальный LTS-канал не обнаружен.
`package.nix` сохраняет upstream build и добавляет
`patches/session-routing.patch`, `patches/manual-model-routing.patch`, `patches/model-variants.patch`, `patches/session-attention.patch`,
`patches/question-location.patch`, `patches/theme-mode-cache.patch`; Linux wrapper сохраняет runtime libraries для watcher
и native audio. V1-модуль и прежние исследования — в [archive/v1](archive/v1/README.md).

## Структура

```text
opencode/
├── default.nix              # Home Manager: подключение и установка файлов
├── package.nix              # pinned binary, patches и Linux runtime libraries
├── config/                  # native V2 settings и устанавливаемые глобальные AGENTS.md
├── commands/                # переносимые Markdown-команды, без README внутри
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

## Автоматическая светлая/тёмная тема

В mutable `~/.config/opencode/cli.json` `theme.name = "flexoki"` выбирает палитру,
а `theme.mode = "system"` следует **терминалу**, не GTK. Имя `system` — другая,
терминальная палитра; менять Flexoki ради переключения не нужно.

`theme-mode-cache.patch` исправляет upstream 2.1.4: сохранённая палитра
`system-theme` могла перекрыть свежий режим терминала даже у Flexoki. Приоритет:
явный light/dark → свежий режим терминала → кеш → исходный fallback. Кеш и личный
`cli.json` не удаляются и не переписываются; F11/Kitty не требуют новых helper-ов.
Исправление входит в домашний binary, не переносится само в независимый Mac archive.

Четыре policy-теста проходят на настоящем patched startup block. На установленном
**старом** binary изолированный PTY воспроизвёл `rendererMode=light` при
`themeMode=dark` со старым кешем; без кеша light/dark работает. Пользователь затем
собрал HM output; после исправления относительного пути в тесте обе PTY-проверки
прошли на его `./result/home-path/bin/opencode`. Дальнейшая живая проверка обнаружила
независимый баг Kitty 0.47.0: применение auto-theme падало до отправки уведомления.
Он исправлен upstream в Kitty 0.47.1. Временная проверка backport в одном Kitty
подтверждена пользователем в обе стороны, но по его решению локальный backport,
overlay и специальные тесты удалены без применения пакета. Ограничение Acer
принято до обновления; [проверка после переезда](../../../docs/laptop-audit/lenovo-checklist.md)
добавлена в существующий Lenovo-чеклист. Фикс кеша OpenCode 2.1.4 остаётся нужен
независимо от версии Kitty и сохраняется.
Правка Python-теста сама по себе не требует пересборки OpenCode. После review:

1. Собрать свой HM output: `nix build .#homeConfigurations.samov-laptop-old.activationPackage`.
2. Проверить binary из собранного профиля:
   `python3 -B home/apps/opencode/tests/test_theme_mode_tui.py ./result/home-path/bin/opencode`.
3. Применить `home-manager switch --flake .#samov-laptop-old`, затем завершить работу
   в текущем TUI и переоткрыть его. Для desktop использовать свой профиль;
   Lenovo draft на Acer не применять. NixOS rebuild и restart service не нужны:
   этот patch меняет только TUI. Одного `/reload` для замены binary недостаточно.
4. В светлой системе новый TUI должен сразу стать светлым. На Kitty ≥ 0.47.1
   проверить также F11 в обе стороны; на 0.47.0 ограничение живого переключения
   пока принято. Личные preferences и кеш остаются на месте.

## Модели и сессионные команды

### Сохранённые Always: `/permissions`

TUI-only `plugins/permissions/` открывает сохранённые Always **текущего проекта**,
сразу с фильтром по native project ID. Они хранятся на сервере между сессиями и
перезапусками. Команда не показывает и не редактирует `allow/ask/deny` из конфига,
не переключает auto-accept, не вызывает модель и не обращается напрямую к БД.

Список и подтверждение — штатные `api.ui.dialog.select()` и `confirm()`,
без собственной отрисовки, JSX или нового патча OpenCode.

- **↑/↓**, поиск — выбрать шаблон; действия сгруппированы по категориям.
- **Ctrl+D или Enter** — открыть штатное подтверждение с действием и полным
  экранированным шаблоном. Только **Remove** разрешает удаление выбранного grant.
- **q / Esc** — закрыть список; **Cancel / Esc** — отменить подтверждение.
  Замена другим native-диалогом также отменяет выбор/подтверждение.
- После удаления — native toast, без автоматического открытия списка заново.
  Для обновления снова вызвать `/permissions`.

Область заморожена при открытии; при несовпадении каталога/проекта последующая
операция отклоняется, но уже открытый диалог нужно закрыть обычным способом.
При выгрузке плагин блокирует дальнейшее удаление, не вызывает общий `clear()`:
у promise-диалогов нет публичного ownership handle, и поверх могло открыться другое
окно. Уже отправленный DELETE отменить нельзя. Перед удалением перечитываются
ID, project ID, action и resource: изменённая/исчезнувшая запись не удаляется;
нужно открыть список заново. API принимает только ID, поэтому между
перепроверкой и DELETE остаётся короткая гонка с другим клиентом — атомарной
условной операции в 2.1.4 нет. После внешних изменений закрыть и открыть список
заново; фонового polling нет. Ошибка удаления может означать потерянный ответ —
перед повтором перечитать список. Это снятие Always, не запрет команды: дальше
действуют остальные правила, а **Permissions: auto-accept** автоматически отвечает
Allow once на новые запросы Ask. Для ручного контроля оставить **prompt**.

Проверки без сборки: `tests/test_permissions.mjs` исполняет настоящий controller;
`tests/test_permissions_tui.mjs` — HM declaration и fixture публичных native
promise-диалогов, без JSX/transpiler. 22 проверки проходят; это не настоящий
OpenTUI/PTY, установленная HM-генерация или удаление живой записи. Передача полного
шаблона проверена; реальное отображение очень длинного текста требует UI-проверки.

Применение только через HM, без NixOS:

1. Проверить diff; если новые исходники ещё untracked, добавить их для Git flake:
   `git add -- home/apps/opencode/plugins/permissions` (это не коммит).
   Применить `home-manager switch --flake .#samov-laptop`
   (на Acer/desktop — соответствующий профиль).
2. Для самого нового TUI-only плагина достаточно переоткрыть TUI. В общем пакете
   есть также server/limits изменения: для них соблюдать отдельное окно обслуживания,
   описанное ниже; сейчас сервис не перезапускать.
3. Открыть `/permissions`: сверить проект, проверить поиск/стрелки, Ctrl+D и Enter,
   отмену подтверждения и выход q/Esc **без удаления**. Проверить **Remove** только
   на явно выбранном ненужном saved grant; повторное открытие должно показать
   обновлённый список, а конфиг — остаться неизменным. Проверить длинный шаблон.

### Subscription limits и смысловые чекпоинты

Локальный `plugins/limits/` использует native V2 server hooks, RPC и TUI slots;
сторонний npm-плагин и новый binary patch не нужны. Индикатор показывается постоянно,
без команды и без LLM-запросов: остатки пятичасового/недельного окна, время до сброса,
число работающих сессий и `Checkpoint`. Проценты — из ChatGPT/Codex usage endpoint,
не оценка по токенам/ценам моделей. Получение процентов поддерживает только
`Codex browser (legacy)` / headless OAuth (`chatgpt-browser`, `chatgpt-headless`).
При ошибке этого источника выводится `unavailable`, а не выдуманные 100%.
Это служебный endpoint `wham/usage`, его контракт может измениться.

**Новый вход `Sign in with ChatGPT` (token sharing):** модель работает, но источник
процентов и времени сброса пока не подтверждён. Вместо общего `unavailable`:

```text
Limits: not exposed by token sharing | Active: 1 | Checkpoint +
```

`Active` и ручные `/checkpoint`, `/checkpoint-reset` работают; процентных
предупреждений нет. `/limits-reset` ничего не сбрасывает. Плагин не запрашивает
несовместимый `wham/usage`, не читает/пишет quota cache для этого подключения,
не принимает его `codex.rate_limits` и не подставляет сохранённые legacy-проценты.
Событие смены OpenAI credential обновляет статус без запроса к модели;
при возврате на legacy снова используется кэш выбранного аккаунта или HTTP fallback.
Другой credential не выбирается автоматически. Legacy — временный рабочий путь,
а не гарантированная долгосрочная зависимость.

Наблюдение 2026-11-07: действующий token-sharing токен получил HTTP 401 от
`wham/usage`; после ручного возврата на legacy проценты восстановились.
Ограничение отслеживается в [openai/codex#54219](https://github.com/openai/codex/issues/54219).
Проверять актуальные OpenAI [models/inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference.md),
[token reference](https://developers.openai.com/siwc/token-sharing-open-source/token-reference)
и [errors/recovery](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery.md).
До появления подходящего API смотреть квоту вручную в
[ChatGPT → Usage](https://chatgpt.com/settings/usage).
Обычные API request/token rate limits не равны пятичасовой/недельной квоте подписки.
`subscription_sharing_usage_limit_exceeded` может означать лимит конкретного
приложения: из него нельзя выводить общий остаток подписки или время сброса.

Чтобы не забыть перепроверить API при обновлении OpenCode, `default.nix` содержит
статический `OPENCODE QUOTA API` warning: штатный HM `warnings` при evaluation/build
и `warnEcho` перед активацией (в том числе готовой generation).
Цвет evaluation-warning задаёт Home Manager; activation-warning жёлтый в
поддерживающем цвета терминале, с учётом `NO_COLOR`. Это **локальное напоминание**,
не автоматическая проверка GitHub/API или текущей авторизации; оно появляется
независимо от выбранного входа и не блокирует build/switch. Сети, polling и LLM нет.
Напоминание и временный fallback удалять только после проверки настоящего
token-sharing источника: проценты, длительность и reset time нужных окон,
переключение аккаунтов без старых данных и независимые предупреждения обоих окон.
Закрытие issue само по себе недостаточно; browser cookies и другие credentials
для обхода ограничения не использовать. Follow-up также сохранён в личном todo.

Для legacy — один кэш на аккаунт в общем server process и один in-flight HTTP-запрос. Данные
запрашиваются при подключении TUI и на границах работы, не чаще раза в минуту;
в простое сетевого polling нет. Поддерживаемые `codex.rate_limits` WS frames
обновляют кэш без дополнительного запроса. Полнота этих событий на настоящем
провайдере не подтверждена, поэтому HTTP fallback сохраняется. Местный минутный
таймер обновляет только countdown/давность в UI. Устаревший снимок явно помечается.
Нет фонового LLM, анализа истории, отдельного процесса, auto-pause/resume и Git polling.

Между location-экземплярами разделяется одна lifecycle-подписка с передачей
владения при выгрузке. События фильтруются явно: Promise adapter pinned V2 2.1.4
не применяет `subscribe({ types })`. Текстовые deltas, metadata и собственные RPC
не меняют workers и не вызывают обновления UI; повторные wait/start/end уведомляют
только при изменении учитываемого числа workers. RPC invalidations объединяются
в microtask и отправляются один раз на весь server, не каждым экземпляром.
Запись кэша использует одну drain promise и dirty flag: снимок сериализуется
перед записью, промежуточные состояния не накапливаются в очереди. TUI объединяет
параллельные status-запросы с одним повтором, если во время запроса были изменения.

Сигналы видны только пользователю в строке статуса: `⚠` рядом с процентом
конкретного окна (`5h`, `week`). На раннем пороге знак серый, на основном — жёлтый.
Если сработали оба окна, у каждого свой знак и цвет; у здорового или явно
отключённого через `/limits-reset` окна знака нет. Отдельного поля с текстом
предупреждения или подсказкой команды нет. Плагин не добавляет бюджетных
инструкций в запросы к модели, не просит её предупреждать и не останавливает работу.
Подготовку handoff пользователь запускает явно через `/checkpoint`.

Пятичасовой резерв: 15/20/25% для 1/2/3 одновременно работающих сессий;
ранний сигнал на 10 п.п. раньше. Далее резерв растёт по той же формуле до 50%.
Недельные пороги — соответствующие пятичасовые × `3/22`, каждый округляется
до целого процента. Основание: один замер за ~39 минут, пятичасовой расход
22 п.п., недельный 3 п.п.; это эвристика для наблюдавшейся нагрузки, не гарантия.

| Работающих сессий | 5h: ранний / checkpoint | Week: ранний / checkpoint |
| ----------------- | ----------------------- | ------------------------- |
| 1                 | 25% / 15%               | 3% / 2%                   |
| 2                 | 30% / 20%               | 4% / 3%                   |
| 3                 | 35% / 25%               | 5% / 3%                   |

Сигнал включается при остатке ≤ порога. Округление может дать одинаковый
недельный порог для соседних чисел сессий; зависимость от workers сохраняется.
Счётчик обновляется событиями выполнения и model hooks для этой подписки,
а не количеством открытых вкладок. Ожидание native form/permission и родитель,
ожидающий blocking `subagent`, исключаются. Долгий обычный инструмент остаётся
частью работы. Другие компьютеры не учитываются; это личный контроль пользователя.
После загрузки плагина уже работающая сессия учитывается на следующем context hook.

Оба лимитных окна независимы. Усиленный сигнал фиксируется до подтверждённого
восстановления сработавшего окна: новый снимок после прежнего `reset_at` с новым
временем сброса либо остаток >95%. Коммит, готовый чекпоинт и уменьшение числа
сессий не снимают сигнал. Обновление порогов также не сбрасывает старый latch:
ранее сработавший недельный сигнал может оставаться выше нового порога до
восстановления окна или явного `/limits-reset`. Старые записи `notices` больше
не читаются и исчезнут при следующем сохранении кэша; файл вручную менять не нужно.
Пороги не гарантируют достаточного остатка для запроса или всех циклов review.

`Checkpoint +` (приглушённый синий) — смысловой handoff ещё не готов;
`Checkpoint ✓` (спокойный зелёный) — агент явно сообщил готовность через
`checkpoint_ready`. Это **не автоматическая независимая проверка** и не Git status.
Новый пользовательский запрос, продолжение работы инструментами или ручной reset
снимают готовность. Поле остаётся и без Git. Перед `✓` обязателен цикл
review → fix → repeat review до отсутствия известных handoff blockers. Нужно указать
проверки, непроверенное, ограничения и точку продолжения. С Git изменения текущей
задачи сохраняются локальным коммитом только по отдельному прямому запросу
пользователя на коммит. Без такого запроса reviewed изменения остаются
незакоммиченными и явно перечисляются в handoff; это не блокирует `✓`.
Без Git код/текст доводится
до связной границы с кратким планом продолжения. В Plan mode — только reviewed
handoff плана, без edits/commit. Нехватка бюджета или блокер оставляет `+`.
Ни статусный сигнал, ни ручная команда не разрешают сборки,
дополнительных агентов, deployment или Git network operations.

Локальные TUI-команды:

- `/checkpoint` — явный запрос агенту подготовить reviewed checkpoint; это обычный
  пользовательский запрос к модели. Не разрешает коммит и не обходит
  Plan/project permissions.
- `/checkpoint-reset` — вернуть индикатор в pending, без модели.
- `/limits-reset` — после native confirmation скрыть сигналы для текущих
  ограничивающих окон, без модели. Не восстанавливает реальную квоту, не меняет
  готовность чекпоинта и не отключает сигналы здоровых/следующих окон.

Готовность/описание handoff живут в `local.checkpoint` metadata сессии.
`Session.Info.metadata` необязательно: отсутствие означает pending, а не ошибку.
Первый rollout выявил HTTP 500 при отправке prompt из-за прямого чтения этого
поля; все server hooks теперь читают его безопасно. Регрессия проверяет сессию
без metadata, отсутствие бюджетных инструкций, создание чекпоинта и сброс при продолжении работы.
`checkpoint_ready` явно использует `codemode: false`, чтобы инструкция могла
вызывать его напрямую, а не только через Code Mode.

`git commit` отдельно требует native shell permission `ask`, включая формы с
`git -C` / `git -c`; остальные Git-команды сохраняют прежнюю политику. Коммит
выполняется только по отдельному прямому запросу пользователя, не вследствие
review, завершения задачи или `/checkpoint`. Не выдавать ему `Always`: сохранённый
project approval может перекрыть `ask`. Это не универсальная изоляция Git от
произвольных shell-обёрток; подтверждение Todo Submit остаётся отдельной явной
операцией записи заметок.

Подготовлено исправление зависших лимитов после разрыва соединения: вместо
одноразовой `rpc.events.on` плагин использует восстанавливаемый поток TUI
`api.data.on`. На `server.connected` перечитываются лимиты и metadata текущего
checkpoint, поскольку события за время разрыва не воспроизводятся. Idle polling
не добавлен. На Lenovo серверный кэш/RPC оставались свежими при застывшем TUI;
журнал фиксирует обрыв и восстановление основного потока 2026-11-13 00:55 UTC.
На точных pinned исходниках воспроизведена невосстанавливаемая RPC-подписка с
mock transport; это не живой UI-тест исправления. `/reload` неизменившегося
плагина не перезапускает его setup. Изменение store-каталога server-плагина также
подпадает под известный Bun-cache риск после HM: одного `/reload` недостаточно.
Сейчас сервис не перезапускать. Для будущего применения:

1. После review применить `home-manager switch --flake .#samov-laptop`.
2. Завершить активные задачи; в отдельно выбранное пользователем окно выполнить
   `opencode service restart`, затем `opencode service status`, переоткрыть TUI.
3. Во время обычной работы проверить обновления процентов и Active без `/reload`;
   при следующем естественном переподключении убедиться, что они продолжаются.
   Проверить `/checkpoint` без запроса на коммит: handoff не должен его создавать.

Агент ничего из этого не применял. Живые reconnect/UI/permission acceptance
и установленная генерация с исправлением пока не проверены.
Кэш и latch — private `0600` JSON под `$XDG_STATE_HOME/opencode/limits/`, имя файла
является hash аккаунта; токены авторизации, email, raw responses и prompts туда
не записываются. Удаление кэша не является пользовательским способом override:
использовать `/limits-reset`.

Минимальные unit/mock проверки (без сборки):

```sh
node --test home/apps/opencode/tests/test_limits.mjs
node --test home/apps/opencode/tests/test_git_commit.mjs
```

`tests/test_limits_tui.mjs` проверяет JSX/команды на fixtures с настоящим TypeScript
transpiler, если `OPENCODE_TEST_TYPESCRIPT` указывает на установленный
`typescript/lib/typescript.js`; сам тест ничего не устанавливает.

Они проверяют реальную логику и plugin setup с public-API-shaped fixtures, не живой
провайдер, TUI/PTY или installed HM symlinks. Для этих интеграций нужна отдельная
проверка на целевой машине после review и применения Home Manager.
Регрессии включают нефильтрованный event storm, повторные события, передачу
подписки между экземплярами и burst-запись с медленным sink. Это проверка
ограниченности работы/очередей, не профилирование heap или throughput benchmark.

Узкая opt-in проверка настоящего runtime с существующим binary (без сборки):

```fish
python3 home/apps/opencode/tests/test_v2_runtime.py (command -v opencode) --limits
```

Отдельный временный HOME/XDG, приватный localhost server и Responses mock;
не использует личные credentials, БД или общий сервис. Проверяет отправку prompt
без metadata, настоящий tool hook и создание/сброс чекпоинта. Не проверяет живой
OAuth/quota endpoint, сигналы на реальной подписке или TUI. Ресурсоёмкие runtime
проверки запускать только по отдельному согласованию; режим с
`OPENCODE_TEST_HM_GENERATION` требует generation, уже содержащую limits-плагин.

### Model routing

`/switch-free` и `/switch-paid` — локальные TUI-команды, без LLM-запроса.
Они записывают `local.model-routing` в metadata **корневой сессии**, сохраняя
остальные keys. Новые обычные сессии используют paid defaults. Отдельного
«ручного» режима нет: ручной выбор Sol/Luna включает Paid для вспомогательных
ролей, Big Pickle — Free, без дополнительного подтверждения. Для неизвестной
модели открывается `Choose helper models` с Free/Paid; Escape отменяет выбор
модели без изменения metadata. Известность определяется настроенными model IDs,
а не названием провайдера или каталожной ценой.

Ручная модель и effort относятся только к текущей сессии и агенту; выбранная
модель не становится моделью всех ролей. Переопределения сохраняются в metadata
корня семьи, остальные роли используют таблицу helper stack. Смена effort не
меняет stack, других агентов или глобальные preferences; старые глобальные
variant preferences больше не перекрывают defaults агентов. Смена модели
сохраняет остальные ручные переопределения. Явная `/switch-free` или
`/switch-paid` удаляет все переопределения семьи и возвращает таблицу режима.
Простая смена агента ничего не сбрасывает.

Выбор на домашнем экране переносится в metadata при создании сессии.
Picker ждёт записи политики до применения модели/открытия списка variants;
ошибки обновления показываются, а не маскируются фиктивным локальным выбором.

| Роль                            | Paid              |
| ------------------------------- | ----------------- |
| Build/general/research/review   | GPT-6.1 Sol High  |
| Plan                            | GPT-6.1 Sol XHigh |
| Explore                         | GPT-6 Luna Max    |
| Compaction/служебная generation | Sol High          |
| Title                           | Luna Low          |

В каталоге нет отдельных `(plan)`, `(summary)` или `(explore)` моделей:
роли выбирают настоящую модель и её variant. Sol предлагает High/XHigh,
Luna — Low/Max; строка ввода показывает агент, модель и выбранный effort отдельно.
`model-variants.patch` читает старые ссылки на aliases в сохранённых сессиях и
metadata как настоящие модели с прежним effort, без переписывания DB/history.
Старый session variant `default` тоже получает прежний effort alias: V2 подставляет
этот sentinel даже при отсутствии variant в сохранённой записи. Явный non-default
variant сохраняется.
Старые записи Recent/Favorites больше не доступны как отдельные модели.

Free направляет все эти роли на `opencode/big-pickle`. Политика действует на
**последующие** запросы существующих детей и сохраняется в DB при reopen.
Уже начатый запрос не отменяется. Другие корневые сессии не переключаются.
Перед записью команда проверяет доступность всех моделей/variants; при ошибке
режим не меняется, автоматического перехода с free на paid нет.
После изменения metadata обязательно `session.invalidate(id)` перед `session.sync(id)`:
в V2 sync — кешированная загрузка, а не принудительное обновление. Без invalidate
сервер уже переходил в paid, но TUI продолжал показывать free; тот же кеш мешал
применить ручной выбор после изменения политики. Проверка одной DB этого не замечает.
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

`patches/session-attention.patch` and the shared `patches/session-attention.ts`
route native sound/notifications/error toasts and quiet Kitty urgency to one
responsible TUI per root-session family. Selecting a session (including a child)
or focusing its terminal claims that family for this TUI. Switching to another
internal tab, home/plugin route or compositor workspace does not release open
background tabs. A more recent selection in another TUI transfers responsibility.
Merely receiving a shared/global tab list cannot claim a session.

Closing a tab releases that client's claim. With tabs disabled, only the current
session family remains eligible. If the owner closes/exits, the most recent
surviving client that previously selected the still-open session becomes eligible.
If no such live client exists, selection in a new TUI is required; restoring the
shared tab strip alone deliberately does not adopt every old session.
Unknown ancestry and forms without a session remain silent. A delayed metadata
hydration retains the original selection timestamp, rather than stealing ownership.

Linux-only coordination uses private atomic client records and per-event receipts
under `$XDG_RUNTIME_DIR/opencode-attention-v2`, not permanent preferences or session
transcripts. PID/start-time checks exclude stale records after crashes/PID reuse.
Selection changes and incoming events drive the policy; there is no idle polling,
new service or player. Event ownership is frozen across both output channels;
each channel consumes its own receipt, so route races/replayed event IDs cannot
produce duplicate output. Receipts remain until the runtime directory is cleared
when the user runtime directory is cleared; they contain only client identities,
not prompts/audio. A crash
after receipt consumption can lose output: this is at-most-once routing, not an
exactly-once delivery guarantee. IPC failure suppresses output and warns once.
Native mute/volume/sound files remain authoritative; quiet urgency ignores mute.
No BEL is sent, avoiding a second audio bell through Kitty/onionbell.

The user subsequently reports that the changed behavior works live. This is
user acceptance of the reported scenario, not independent observation of every
multi-window/focus/crash/mute case or an installed-derivation comparison. Lightweight policy,
actual patched notification-handler fixtures and real two-process IPC tests pass;
these do not test native Solid reactivity, actual audio, Kitty or compositor urgency.
The updated opt-in PTY harness adds inactive-tab/home/ownership-transfer scenarios
but has not been run on a newly built binary. See [BENCHMARK.md](BENCHMARK.md).

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

|               | Домашний laptop/desktop                         | Корпоративный Mac                                                    |
| ------------- | ----------------------------------------------- | -------------------------------------------------------------------- |
| Звуки         | Личные anime done/error, freedesktop permission | Только стандартные встроенные OpenCode                               |
| Обработчик    | Native plugin с `session-attention.patch`       | Штатный `opencode.notifications`, без нашего `session-notifications` |
| Kitty urgency | Домашний `quiet-urgency.ts`                     | Домашний plugin не переносится                                       |

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

HM собирает `tui.ts`, `session-attention.ts` и `silent-attention.py` в один
store-каталог. Импорты и путь Kitty kitten относительны к реальному entrypoint:
они не ссылаются на временный flake source snapshot, который GC может удалить.
Старый `replaceVars` оставлял такие абсолютные пути без зарегистрированных
Nix references. Для todo эта причина не установлена: при диагностике плагин
был загружен. Известный отдельный сбой кеша после смены store-ссылок описан ниже;
сам по себе факт GC не доказывает, что он затронул todo.

`plugins/workspace-context.ts` публикует полное Unicode-название **просматриваемой**
сессии и её directory в `$XDG_RUNTIME_DIR/hypr-spaces/apps/`, включая rename и
route changes без prompt. PID/starttime/Kitty pane и cleanup сохранены.
Модельных запросов и чтения message history нет.

## Независимое /delegated-review

HM устанавливает `commands/delegated-review.md`; `agents.review` читает общий
`config/review-system.md`, сохраняя прежние model routing и permissions.
Команда передаёт минимальный хэндофф отдельному ревьюеру, фиксирует scope/fingerprint
и сначала продолжает того же ребёнка при terminal provider failure. До шести
дополнительных вызовов делят один бюджет: паузы 20/40/60/90/120/120 с, предел
10 минут без подтверждённого прогресса. Работающему ребёнку не отправляется
дубликат; при недоказанном завершении или исчерпании бюджета — incomplete без
выдуманного вердикта. Это инструкции для модели, не программный retry scheduler.
Report repair тоже тратит дополнительный слот: INCOMPLETE + continuation = 2/7
вызовов, 1/6 дополнительных использован, осталось 5, provider retries 0. Отдельный
provider retry counter выбирает backoff, не увеличивая общий бюджет. Fingerprint
имеет точный canonical JSON формат `dr-scope-v1` и Python-рецепт в самой команде;
handoff передаёт JSON целиком, без угадывания shell/NUL-кодировки.

`review` по-прежнему подходит для других независимых проверок changes/claims.
Встроенная `/review` не заменяется, корпоративный конфиг не меняется. Лёгкие тесты
вычисляют реальные Nix settings, исполняют hash-рецепт и статически проверяют
command/wiring. Пользовательский тест подтвердил same-child INCOMPLETE → COMPLETE
на Big Pickle, не provider recovery. Отдельный согласованный opt-in native mock
успешно проверил HTTP 429/native retry и terminal failure → пауза 20 с → same-child
recovery с сохранённым read result без повторного чтения. Скриптовые решения mock
не проверяют реальную модельную политику или полный recovery budget. Применение — только HM,
без binary patch или restart сервиса. Полный контракт, API evidence и порядок
проверки — [DELEGATED-REVIEW.md](DELEGATED-REVIEW.md).

Второй пользовательский Big Pickle smoke подтвердил ожидание команды, точный
двухфайловый scope/hash, один вызов и правильные counters, без потери отчёта.
Он занял 6 мин 40 с и создал временный helper вне проекта. Последующие правки
запрещают такие artifacts у обоих агентов, уточняют однократную инициализацию
ledger и явно запрещают APPROVE/REQUEST_CHANGES/BLOCKER при incomplete.
Новые формулировки покрыты static guards, не новым real-model/Mac smoke.

После пользовательского сравнения R1/R2 редакция 13.11.2026 ставит анализ поведения
и контрпримеров перед оформлением отчёта. Существенное невыполненное требование
или решающий контрактный вопрос несовместимы с `APPROVE`; вопрос не объявляется
подтверждённым дефектом, непроведённый runtime check сам по себе не блокирует
source review. Восемь static/settings/hash checks и семь synthetic-oracle tests
проходят, **не доказывая** улучшение реальной модели. Слепая приёмка пока не запущена.
Новый четырёхфайловый Mac-кандидат:
`~/Downloads/delegated-review-mac-2026-11-13-scenario1/`; предыдущий пакет и
`opc-loc.zip` сохранены. Chrome-MCP вариант из архива пока не дорабатывался.

Пользовательский прогон первой аналитической редакции уже вернул REQUEST_CHANGES
и нашёл каретку, но необоснованно распространил принятую замену текста на потерю
selection. Handoff также обобщал частичный skip до игнорирования события и failed
typecheck до «clean apart from…». Последующее уточнение ограничивает выводы
конкретными эффектами и сохраняет failure qualifiers, не повышая severity автоматически.
Текущий кандидат — `~/Downloads/delegated-review-mac-2026-11-13-scenario1-r2/`,
маркер команды и роли `Review policy: behavior-v2.`. Десять static/settings/hash
и девять oracle tests проходят. Позднее пользовательский behavior-v2 прогон на
том же diff сохранил email REQUEST_CHANGES/caret finding без прежних blanket
exceptions: ограниченно положительный результат на одном кейсе, не общая приёмка.
Typecheck при TS2688 и условность history restore всё ещё переданы недостаточно точно.

После согласования второго сценария добавлена отдельная `/delegated-review-chrome`,
маркер `Audit policy: chrome-evidence-v1.`. Она пассивно сопоставляет claims с
записанными действиями/результатами, различает разрешённый mock и подмену, недостаток
доказательств и противоположное наблюдение. При необходимых недоступных evidence —
incomplete без verdict; browser actions не разрешены. Шесть static/hash/fixture
checks проходят, не проверяя модель. Mac-пакет отдельно:
`~/Downloads/delegated-review-mac-2026-11-13-chrome/`; reviewer/routing и старые
пакеты не меняются. См. [DELEGATED-REVIEW-CHROME.md](DELEGATED-REVIEW-CHROME.md).

## /problem-brief

Ручная команда без аргументов превращает непосредственно предыдущий ответ агента
в понятные открытые вопросы и действия. Аргумент задаёт источник/область и цель:
вся сессия, тема, локальные файлы или Git; возможна сводка завершённой работы.
Локальное чтение разрешено по запросу, внешние исследования/тесты/запись запрещены.
Её можно вызвать после `/delegated-review` или
`/delegated-review-chrome`, но не вместо полного отчёта/evidence и не как handoff
reviewer. Автозапуска, отдельного агента, модели или effort override нет.

Первоначальные prompt и [README](problem-brief.README.md) были перенесены побайтно.
По отдельному запросу домашняя версия получила только Scope и разрешение локального
чтения; остальные правила prompt сохранены. README согласован с новой областью.
Исходники Downloads/Mac не менялись. Пользовательские восемь GLM-5.3-Flash прогонов
относятся к исходному варианту, не новой семантике Scope; агент их не повторял.
Локальные проверки фиксируют границы разрешённых правок, metadata и выбранные
реальные HM file declarations, не качество генерации. Дальнейшие правки — только
по отдельному согласованию.

HM устанавливает команду в `~/.config/opencode/commands/problem-brief.md`, guide —
в `~/.config/opencode/problem-brief.README.md` (с учётом `XDG_CONFIG_HOME`). Для Mac
достаточно тех же двух файлов в соответствующем активном слое; corporate config
и существующие симлинки не заменять вслепую. После применения достаточно `/reload`.
Домашнее применение: добавить новые source-файлы в Git flake и выполнить
`home-manager switch --flake .#samov-laptop` либо свой desktop/laptop-old профиль.
NixOS не меняется; сборка/активация и модельный прогон агентом не выполнялись.

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

## Форматирование: правила проекта

Глобальное автоформатирование и зависимости форматтеров не устанавливаются.
Короткое правило в `config/AGENTS.md`: применять объявленный проектом formatter
через CLI только к изменённым файлам; без него сохранять существующее оформление,
не выбирать глобальный fallback и не заменять инструмент переформатированием моделью.
Lint fixes — отдельная операция. Проектные настройки V2 могут явно включить native
formatter; домашний модуль его не включает. Правила самого `nix-config` — в корневом
`AGENTS.md`, `.prettierrc.json`, `pyproject.toml`, `.editorconfig` и flake formatter.

## LSP

LSP в pinned V2 отсутствует, не просто выключен. Возвращение в новой архитектуре
отслеживается в [upstream #38528](https://github.com/anomalyco/opencode/issues/38528),
что [подтвердил maintainer](https://github.com/anomalyco/opencode/issues/50916#issuecomment-6287891675).
Это незавершённый port; отдельного публичного обоснования окончательного отказа нет.
Специализированного native LSP API в этой версии нет; расширять можно общим plugin
API/MCP. Есть [сторонний V2 plugin](https://github.com/christensenjairus/opencode-v2-lsp-support)
с lazy stdio servers и diagnostics через tool hooks, но он здесь не устанавливается
и совместимость с pinned 2.1.4 не проверена. Неиспользуемые language-server packages
в closure не добавлены. CLI lint/typecheck не заменяет navigation/rename/hover LSP.

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
файл через `agent_todo_read`, предлагает изменения через `agent_todo_propose`.
Обычный путь — `changes.add`: модель формулирует `title`, `summary`, `goal`,
`returnWhen`, необязательный `notes` и stable `id`; код создаёт checkbox heading,
закрытый spoiler и добавляет запись, сохраняя остальной файл побайтно. Для правок
есть `changes.replace` с ID и точными `before`/`after` фрагментами: совпадение должно
быть единственным внутри заметки; метаданные менять так нельзя. Для одного возврата
достаточно `revisited`, без копирования заметки. Полный `content` сохранён только как
совместимый путь для явно запрошенной перестройки всего файла, не для обычного импорта.

Это также убирает огромную серую строку аргументов на фоне: штатный generic-tool
summary печатает строковые поля, но не вложенный объект `changes`. Полезный текст
всё равно целиком показывается на страницах согласования и доступен при ручном
раскрытии tool details. Старые вызовы с `content` в истории не переписываются.
Сравнение, сборка Markdown, сохранение неизменённых блоков, счётчики, fingerprint,
навигация и Git выполняются кодом; модель нужна для смысла и формулировок, а не для
механического merge/diff. Между страницами дополнительных модельных запросов нет.
Служебные надписи и кнопки формы — английские (финальные `Submit` / `Reject` и
`Type your own answer`); пояснение модели — на языке беседы. Содержимое заметок
остаётся русским. Вместо полного unified diff форма показывает только затронутые
заметки: новые/удаляемые блоки, полный результат правки и изменённые строки (`Before`/`After`).
Неизменённые блоки, Git-заголовки, stable ID и hash `last` не дублируются; счётчики
показаны как `Visits`/`Priority`.

Длинный текст штатного Question в 2.1.4 не прокручивается. Поэтому TUI-часть
todo-плагина показывает собственный диалог поверх **одной native consent form**.
На время просмотра непрозрачная подложка скрывает штатный `Questions`, чтобы не
показывать два интерфейса одновременно. Она остаётся до удаления формы после
ответа/отмены; host tree и form cache не изменяются. Это визуальное скрытие,
не второе подтверждение и не отключение native consent.
**Одна заметка = одна вкладка**, начиная с первой задачи. Длинный текст прокручивается
внутри вкладки, без разбиения или обрезания. HTML-обёртки spoiler скрыты только при
просмотре; в файле сохраняются. Нет отдельных Proposal/Review/Change и счётчиков частей.
**← / →, Tab и Shift+Tab** циклически переключают заметки и единственную финальную
вкладку. ↑/↓ прокручивают заметку; Home/End — начало/конец, колесо мыши также работает.
PgUp/PgDown не используются для навигации. Подсказка повторяет привычный стиль
`tab / scroll или select / confirm / dismiss`; это plugin keymap, не изменение binary.
На финальной вкладке ↑/↓ выбирают `Submit`, `Reject` или `Type your own answer`.
Пояснение, путь, commit subject, перестановки и ручные правки находятся там же,
в прокручиваемом тексте. Для его прокрутки есть Ctrl+↑/↓ и Home/End.
Проверено в реальном TUI 80×24.

Отдельное предупреждение с изменёнными строками появляется только при имеющихся
ручных/staged правках; для существующего файла без HEAD показаны включаемые в первый
коммит заметки. Это не merge conflict: настоящий Git conflict/операция блокирует запись,
а изменение fingerprint требует перечитать файл и согласовать заново.

Только финальный `Submit` без комментариев применяет и локально коммитит **весь согласованный
итоговый todo.md** одним коммитом, включая показанные ручные изменения. До этого
просмотр не создаёт todo.md или Git repository и не сохраняет частично одобренные
задачи. `Reject`, Esc, закрытие диалога или уход с сессии отменяют весь пакет; для todo
Esc возвращает обычный `declined`, завершает tool и не прерывает шаг как native Question.
Плагин распознаёт только `QuestionTool.CancelledError`, остальные ошибки и session abort
не маскирует. `a` или клик по `Type your own answer` открывает комментарий к текущей
заметке; Enter сохраняет его в черновике формы, Tab сохраняет и переключает вкладку.
Ответы разных заметок не смешиваются. Финальный собственный ответ относится ко всему
пакету. При любом комментарии `Submit` **ничего не пишет**, а возвращает агенту
`feedback: [{id, title, feedback}]`, отдельный `batchFeedback` и исходный `draft`.
Агент меняет только соответствующие формулировки, сохраняя остальные черновики;
исправленный пакет снова требует согласия. После Esc открывать форму заново можно
только по просьбе пользователя. Reload/замена диалога не дают согласия автоматически.
Навигация локальна внутри TUI; она не отправляет ответы серверу до финального решения.
Fingerprint проверяется перед формой и снова при сохранении: ручная правка
во время просмотра блокирует запись и требует нового чтения и полного повторного согласования.
Native form остаётся транспортом consent/cancel. Submit-ответ привязан к fingerprint
и тексту конкретного предложения; если TUI-часть не загрузилась, clipped stock form
не может сохранить заметки обычной кнопкой. Это не повод обходить подтверждение.
Plan явно отклоняется самим todo-инструментом, даже при session-level `edit: allow`.

При включённом decision-support чтение `~/agent-todo/*` явно разрешено без
permission prompt. Это не даёт разрешения на запись: native `edit` permission,
Plan guard и отдельная форма подтверждения сохраняются. Ограничения самого todo-инструмента
(обычный UTF-8 файл до 128 KiB, проверки Git) также остаются.

`question-location.patch` сохраняет `Location` при вызове native question из
Promise-плагина. Без него сервер создаёт форму, но её событие не имеет каталога,
и TUI не показывает подтверждение — tool выглядит зависшим. Проверка включает
настоящие PTY-клиенты, а не только ответ форме через API. Это **server-side** patch:
после первой установки исправленного binary завершить активные задачи, выполнить
`opencode service restart` и `opencode service status`, затем переоткрыть TUI.
Обычный `/reload` обновляет конфигурацию, но не код запущенного service.

После обновлений Home Manager, меняющих store-каталоги плагинов, также перезапускать
service. HM корректно переключает directory symlink на новую версию, но Bun в уже
работающем процессе может помнить старый entrypoint. Проверка границ каталога
тогда молча исключает плагин; `/reload` этот кеш не очищает. Используется штатный
resolver без дополнительного патча; restart загружает актуальные ссылки заново.
Обычные изменения конфигурации не требуют restart.
Закрывать все клиенты заранее не обязательно, но активные задачи нужно завершить:
restart прерывает серверную работу. После замены binary переоткрыть TUI.

Формат (числа вычисляет инструмент; в примере второе обращение):

```text
# Todo

<!-- todo-stats -->
Total: 1 · Done: 0 · In progress: 0

## [ ] 1. Check laptop resume

<details>
<summary>Check suspend/resume on the current laptop firmware.</summary>

<!-- todo:laptop-suspend -->

Visits: 2 · Priority: Normal
Status: Todo
Created: 2026-11-04T10:00:00.000Z

- Goal:
  Check suspend/resume on this firmware.
- Return when:
  The device is available for a reproducible test.
- Notes:
  Comparing specifications cannot establish this.

</details>
```

Новые `changes.add` получают следующий номер в заголовке (после максимального
номера или количества существующих записей). Старые заголовки и ручные номера
не переписываются автоматически; номер не заменяет stable ID и не связан с
числом обращений/приоритетом. Перенумерация старых записей требует подтверждения.

Снаружи остаётся только заголовок с `[ ]`; для выполненного пункта вручную заменить
на `[x]`. Заголовок — короткое говорящее название, `<summary>` — краткое резюме сути
задачи в одном предложении, не общее «Подробности» и не дубль названия.
Все подробности и счётчик находятся в закрытом по умолчанию `<details>`.
Это HTML-спойлер в поддерживающем его Markdown-просмотре; в обычном буфере Neovim
теги остаются текстом и сами по себе folds не включают. Старые блоки совместимы:
плагин не переписывает их оформление и не меняет отметку выполнения автоматически.

Новый блок получает `Visits: 1`; `revisited: ["laptop-suspend"]` при осознанном возвращении
увеличивает только счётчик до `2`, `3` и далее — только после согласия.
Большее число означает больше возвращений, не срочность/обязанность выполнить.
ID стабилен при переименовании заголовка. В том же HTML-комментарии инструмент хранит
`last:<sha256>` от session/user-message IDs для дедупликации. Это непрозрачный локальный
идентификатор, не текст разговора. Повторы инструмента в одном user turn, чтение и
переформулирование счётчик не повышают. При неизвестной границе user message (например,
после compaction) инкремент отклоняется, а не угадывается. Распознавание «вернулись к
той же идее» остаётся суждением модели; плагин сам семантически темы не сопоставляет.
Не удалять ID/last, если нужна эта дедупликация. Произвольные ручные заметки допустимы,
но для учёта возвращений нужен блок с ID. Автоматической сортировки/опроса файла нет.

Интерфейс, reason и служебные поля английские. Новый контент по умолчанию английский,
даже при русском запросе; русский — только по явному указанию. Старый контент не
переводится. Артефакты (код, конфиги, команды, логи, ошибки, пути, IDs, URLs и текст
для дословного включения) сохраняются без перевода в обе стороны, независимо от
языка окружающего текста. Исключение — прямой запрос перевести конкретный артефакт.
Язык запроса сам по себе не делает весь запрос артефактом. Это инструкции для модели,
не автоматический определитель языка/артефактов; код сохраняет переданные значения.

Независимый `Priority`: `High / Normal / Low`, по умолчанию `Normal`.
`changes.update: [{id, priority?, status?}]` меняет явно указанные поля без
переписывания заметки. `Status`: `Todo / In progress / Done`; `In progress` никогда
не выставляется просто из-за обсуждения. `Done` совместим с `[x]`; повторное открытие
снимает `Completed`, новое закрытие записывает новую дату. Ручное закрытие датируется
при следующей операции как `(Observed)`, а не выдаётся за точное время отметки.

Только явный `sort: true` сортирует целые блоки: `In progress` → `Todo` → `Done`.
В первых двух группах: `Priority`, `Visits` по убыванию, `Created` от старых к новым.
В `Done`: `Completed` от свежих к старым. Неизвестные даты идут после известных,
равенства сохраняют порядок; номера/IDs и контент не меняются. Неизвестные разделы
без task heading/ID остаются на прежних местах. Сортировка мигрирует managed-поля
на английский; прежний числовой приоритет трактуется как `Normal`, не как отдельная
оценка. Старые даты восстанавливаются по последним 200 first-parent коммитам локального
Git с пометкой `(Git history)`; при нехватке данных остаётся `Unknown`.
Верхний `Total / Done / In progress` обновляется при подтверждённой записи, включая
ручные правки на диске. Чтение ничего не исправляет, polling нет. Перестановка и
новые totals показываются в финальной вкладке согласия; запись — один локальный коммит.

Защита записи: повторная проверка content/HEAD/index/status после ответа и перед
записью, короткий локальный lock и native Git index lock. Устаревшее предложение
требует нового чтения и согласия. Плагин отказывается работать с symlink/hardlink,
конфликтами, незавершёнными Git-операциями, другими файлами в репозитории и файлом
больше 128 KiB. Лимит не отправляет файл модели автоматически; явный
`agent_todo_read` возвращает фактическое содержимое, и его токенная стоимость растёт
с размером файла. Несохранённые буферы Neovim не видны; сохранения внешнего редактора
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
   nix build --no-link .#homeConfigurations.samov-laptop-old.activationPackage
   ```
   Для desktop — `samov-desktop`. Пока новые файлы не отслеживаются Git,
   использовать `path:.#…` вместо `.#…`.
2. Применить **только Home Manager** для нужного хоста:
   ```fish
   home-manager switch --flake .#samov-laptop-old
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
