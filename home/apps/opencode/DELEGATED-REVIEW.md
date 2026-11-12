# /delegated-review

Домашний HM-модуль устанавливает `commands/delegated-review.md` как
`~/.config/opencode/commands/delegated-review.md`. Профиль `agents.review` читает
`config/review-system.md`, сохраняя существующие model routing и permissions.
Это config-only изменение, без binary patch, плагина или нового сервиса.
Корпоративный personal-layer и исходные файлы в Downloads не меняются.
Родитель и reviewer не создают временные scripts/manifests/reports/directories,
даже вне проекта: механические вычисления выполняются inline, результаты остаются
в контексте сессии. Штатные runtime logs/session storage этим не запрещаются.

```text
/delegated-review current branch
/delegated-review last 2 commits
/delegated-review working tree
/delegated-review последние 3 коммита
/delegated-review src/auth.ts + tests
```

## Разделение ответственности

Команда остаётся в текущей сессии (`subagent: false`): родитель определяет scope,
составляет минимальный хэндофф, вызывает независимый `review` (или `general`, если
его нет), восстанавливает попытку и возвращает полный отчёт на русском. Модель
не задаётся командой: действует локальная политика выбора моделей. Диалог
разработки, self-review и полный transcript ребёнку не передаются; обычные
project/system instructions OpenCode продолжают действовать.

`review` остаётся общим read-only ревьюером changes **и claims**, а не только
исполнителем этой команды. Он проверяет унаследованные findings, различает
прочитанные файлы и проанализированные review units, проведённые и непроведённые
проверки. Новых checkpoint-файлов нет. Сам `edit=deny` не запрещает запись через
shell: prompt дополняет shell policy, но не является security sandbox. Fallback
`general` получает prompt-контракт, не permission rules агента `review`.

Команда `/delegated-review` не перекрывает встроенную `/review`; имя агента
`review` тоже не заменяет slash-команду. README намеренно находится вне `commands/`.

## Scope и восстановление

- Scope разрешается в точные Git endpoints/paths. Fingerprint — SHA256 точного
  canonical JSON manifest `dr-scope-v1`: `sort_keys=True`, separators `,`/`:`,
  `ensure_ascii=True`, `allow_nan=False`, ASCII bytes без завершающего newline.
  Поля/порядок массивов, diff argv и исполняемый Python-рецепт заданы в команде;
  родитель передаёт ребёнку сам JSON, а не описание «NUL-delimited manifest».
  Для mutable scope учитываются diff и содержимое/типы/modes всех scoped файлов,
  включая релевантные untracked файлы. Не угадывать варианты кодировки и не
  использовать склеенные shell escapes вроде `\0100644`. Mtimes/diffstat недостаточны; ignored secrets и
  посторонние артефакты не читаются ради хэша. Внешние зависимости не заморожены.
- Fingerprint проверяется перед запуском/восстановлением/отчётом и ревьюером
  при начале/завершении. Изменившийся scope означает incomplete, не смесь версий.
- Сначала продолжать того же ребёнка через `sessionID`. Потерянный ID искать по
  invocation metadata, parent-filtered списку и точному review ID/fingerprint;
  не угадывать по названию или времени. Пагинация обязательна. Сверка ограничена
  двумя минутами и общим recovery deadline; неизвестное состояние — incomplete.
- Работающему ребёнку не отправлять дубликат: native retry/backoff, ожидание
  permission/form и потеря ответа не доказывают terminal failure. Ожидать native
  completion, не polling/sleep для проверки прогресса.
- После terminal transient failure — до **шести дополнительных вызовов** с паузами
  **20 → 40 → 60 → 90 → 120 → 120 с**, учитывая более долгий provider retry hint.
  Continuation, replacement и восстановление неполного отчёта делят один бюджет;
  native внутренние retry не считаются новыми command-level вызовами.
  Ledger: `additional_used = invocations_used - 1`, остаток `6 - additional_used`.
  Например, INCOMPLETE + continuation = 2/7 вызовов, 1/6 дополнительных использован,
  осталось 5, provider retries 0. Отдельный счётчик provider retries выбирает
  backoff, но не добавляет попыток; первый provider retry после report repair
  ждёт 20 с и оставляет 4 дополнительных слота. Переименование review не сбрасывает
  ledger. Все счётчики показываются перед итоговым отчётом.
- До ожидания/повтора проверять **10 минут без подтверждённого прогресса**. Это не
  timeout здорового работающего ревью. Токены, чтение файла и новый ID не сбрасывают
  часы; новый подтверждённый анализ/check result может сбросить часы, но не бюджет.
- Не каждый 429 временный: quota/billing/auth/cancellation/denied access требуют
  действий, а не слепых повторов. Не менять модель/аккаунт и не переводить весь
  независимый план в serial execution ради обхода concurrency limit.
- Replacement допустим только при невозможности продолжить или доказанном
  отсутствии восстанавливаемого/работающего ребёнка. Ему передаётся исходный
  хэндофф плюс минимальный evidence-based appendix. Унаследованные findings —
  проверяемые leads, не готовый вердикт. Некоторое повторное чтение может понадобиться.
- По исчерпании бюджета/неизвестном состоянии — **«Ревью не завершено; итогового
  вердикта нет»**, provisional findings с provenance, gaps и план продолжения.
  Частичный ответ не превращается в APPROVE или кодовый BLOCKER.

Complete означает анализ согласованного scope, не прохождение всех возможных
integration/build checks. Честно указанные непроведённые проверки сами по себе
не делают source review incomplete; непроанализированные обязательные области —
делают. Ни родитель, ни ребёнок не правят код и не запускают сборки; фиксы —
отдельная задача. Это инструкции для модели, не гарантированный retry scheduler;
они не сохраняют недоставленные токены и не работают после остановки родителя.

## Основание и границы проверки

Сверены V2 [commands](https://opencode.ai/v2/docs/commands),
[agents](https://opencode.ai/v2/docs/agents), [API](https://opencode.ai/v2/docs/api)
и pinned 2.1.4 source `68bc26b7da1990ce10ffecfbc1e09eb13aa5d824`:

- `packages/core/src/tool/plugin/subagent.ts:153–167,200–216,245–264`: parent
  validation, ID в progress/error/metadata; prompt работающему ребёнку может стать
  steering input, а не пассивным ожиданием.
- `packages/core/src/session/subagent-job.ts:53–60`: completed/error-free assistant
  message из последних 20 сообщений не обязательно является полным отчётом текущей
  попытки. Поэтому нужны review ID/fingerprint, coverage и timeline provenance.
- `packages/core/src/session/subagent-completion.ts`: native completion связывает
  результат с ребёнком и родителем, но не подтверждает полноту анализа.
- `packages/schema/src/session.ts:71–106`,
  `packages/protocol/src/groups/session.ts:103–133,211–225`: parent filtering,
  pagination, active foreground drains данного процесса. Отсутствие в active не
  заменяет сверку terminal job/retry/ожидаемого ввода.
- `packages/protocol/src/groups/message.ts:23–41,68–86`: message pagination,
  limit 1–200, opaque cursor без `order` на последующих страницах.

Использовать `opencode api` в том же server/location/auth context, не читать БД.
Примеры 2.1.4 (заменить IDs; cursor URL-encode, сохранять фильтры):

```fish
opencode api get '/api/session?parentID=ses_PARENT&limit=50'
opencode api get /api/session/ses_CHILD
opencode api get /api/session/active
opencode api get '/api/session/ses_CHILD/message?limit=50&order=desc'
```

Текущие online docs могут опережать установленный API. При обновлении сверять
реальную схему, а не предполагать V1 endpoints. Например, в проверенном 2.1.4
`/api/agent/review` дал 404, тогда как `/api/agent` работал.

Лёгкая проверка (без сборки):

```fish
node --test home/apps/opencode/tests/test_delegated_review.mjs
python3 -B home/apps/opencode/tests/test_delegated_review_fixture.py
```

Node-тест действительно вычисляет Nix settings и проверяет prompt/model/permissions,
а command/recovery/wiring проверяет статически. Он также исполняет опубликованный
Python-рецепт fingerprint и сверяет независимое JSON-кодирование с кавычками,
backslash/newline/Unicode и изменёнными данными. Python unit-тест проверяет только
сценарий mock-провайдера, без запуска OpenCode. Это **не** native command
discovery, модельное следование инструкции, actual failure/recovery или UI-приёмка.

## Наблюдённый первый тест и native mock

В соседней пользовательской сессии `ses_e2eec9478ffe7dZYLjivJYJUzY` независимая
read-only сверка истории и transport-логов подтвердила Big Pickle у родителя/детей.
После ошибочного преждевременного запуска и пользовательского прерывания основное
ревью использовало ребёнка `ses_e2ee8930affeXoIdg31nKcD8jM`: INCOMPLETE → продолжение
того же ID → COMPLETE. Первый scope был отвергнут пользователем; это не разрешение
игнорировать отмену или обнулять бюджет повторной попытки того же scope.
Хэши всех подготовленных файлов совпали с началом теста; правок/коммитов/сборок/
активаций в журнале нет. Созданы два временных файла вне проекта. Реальных
provider failures не было: все записанные HTTP responses — 200.

Аудит нашёл неверное «бюджет не расходовался», неполный рецепт fingerprint и
неточный статус staged/untracked в handoff; текущая редакция уточняет эти правила,
но новое следование модели ещё не проверено. Nits того ревью не являются
автоматически принятыми дефектами: например, blanket-утверждение об отсутствии
policy-тестов неверно — Git-network policies покрыты `test_git_offline.mjs`.

Opt-in `tests/test_delegated_review_runtime.py` успешно выполнен 12.11.2026
после явного согласования. Два ранних прогона выявили ошибки самого harness:
обязательный доступ к отсутствующему MCP и чтение command list до асинхронной
активации плагинов. Теперь optional MCP обрабатывается без ошибки, discovery
ожидается не более 20 с, а setup failure закрывает mock socket без запуска потока.
Четыре дешёвых unit-теста включают проверку cleanup при setup failure.
Он использует установленный binary и настоящий native subagent tool, но решения
«модели» задаются скриптом локального mock Responses-провайдера:

1. Один HTTP 429 поглощается native retry; родитель не создаёт новый вызов ребёнка.
2. После реального read tool result идут 11 HTTP 429 (исходный запрос + десять
   native retries в pinned 2.1.4). Terminal error доходит до родителя с child ID.
   Скриптовый родитель выполняет настоящий `sleep 20`, продолжает того же ребёнка;
   проверяются один child, два subagent-вызова, сохранённый read result и отсутствие
   повторного чтения. Это доказательство сохранения прочитанного, не выполненного
   независимого анализа. Все запросы должны оставаться на Big Pickle.

Успешный прогон: `/tmp/opencode/delegated-review-runtime-yjqaiucn/`.
Native case: parent `ses_e2ed2b85dffe3S5yyREvgFA76g`,
child `ses_e2ed2b778ffeZHRxCFPUo9AEM0`, один completed subagent-вызов.
Terminal case: parent `ses_e2ed2ae86ffer8SU5dvP7991N1`,
child `ses_e2ed2ae1effeSesdW77jZGqIjX`, error → completed на том же ID,
пауза между завершением первого и созданием второго вызова 20,304 с.
В обоих случаях ровно один completed read; все 5/17 HTTP-запросов соответственно
использовали mock model ID `big-pickle`. Это не обращения к реальному Big Pickle.

Без новых plugins, builds или shared service: отдельные HOME/XDG/project,
loopback mock/server, фиктивные credentials, отключённые MCP/каталожные fetch,
только имеющийся model-calls logger. Приватные артефакты остаются под
`/tmp/opencode/delegated-review-runtime-*`. Native-фаза ограничена 240 с плюс
короткая подготовка/cleanup. 11 HTTP failures / 10 native retries — контракт
текущего pin, не повод молча
менять ожидание при обновлении. Сценарий не проверяет реальную модель, последующие
backoff-ступени, исчерпание семи вызовов или десятиминутного окна, missing-ID,
replacement и всю команду end-to-end. Scripted decisions не доказывают prompt
compliance. Запускать только после отдельного согласования этой команды и scope:

```fish
python3 -B home/apps/opencode/tests/test_delegated_review_runtime.py (command -v opencode)
```

## Второй пользовательский smoke и последующие правки

Read-only аудит сессии `ses_e2ecce9dbffeYUvXNihLTXgmdv` и её единственного
reviewer `ses_e2ecac52bffexPSz0g6i9k9QUd` подтвердил ожидание фактической команды,
scope из двух файлов, воспроизводимый fingerprint, корректные `1/7`, `0/6`,
остаток 6 и provider retries 0. Все transport attempts использовали Big Pickle;
все 8/7 parent/child HTTP responses — 200. Полный отчёт с двумя nits возвращён
без потери findings. Provider recovery здесь не понадобился.

Fingerprint проверенной версии:
`6321020148ded0f293c781e16dff89d7725a27623b2f5120324769d1f81b9160`.
Приватные evidence artifacts: `/tmp/opencode/delegated-review-live-audit-kq76wlnx/`.
Весь запуск занял 400,301 с, reviewer — 275,785 с; малый scope не гарантирует
короткого размышления. Родитель создал временный helper script вне репозитория,
поэтому этот прогон не доказывает строгое отсутствие записей. Проект не менялся.

После согласования исправлены двусмысленное `Before any invocation` (инициализация
теперь только перед первым вызовом), запрет временных review artifacts у обоих
агентов и явное перечисление APPROVE/REQUEST_CHANGES/BLOCKER для incomplete.
Шесть settings/static/hash-recipe тестов, два Git-offline и четыре fixture-unit
теста проходят. Новый запрет temp artifacts проверен текстовыми guards, не новым
прогоном реальной модели; native HTTP mock повторно не запускался, транспортный
код не менялся. Старый fingerprint не относится к этой новой редакции.

## Перенос на корпоративный Mac

Для этой функции достаточно отдельного минимального пакета: актуальная команда,
model-free reviewer profile из актуального `config/review-system.md` и README
по установке/проверке. Это не полный перенос домашней конфигурации и не требует
домашних plugins, Nix, Linux binary patches или `/switch-free`/`/switch-paid`.
Встроенная `/review` не заменяется. Старый `Downloads/delegated-review-v2/`
сохранён как предыдущий portable draft, не как актуальный пакет для установки.

В Mac-задаче сначала проверить фактический V2 config и overrides: существующему
`review` сохранить корпоративные model/permissions и более строгие правила;
если своего reviewer нет, добавить read-only subagent без model/provider override.
Не заменять весь `opencode.json`, personal-layer, proxy/MCP/auth/voice/CLI/sounds.
Для переноса нужен Git и Python 3 для приведённого hash recipe; native API/tools
должны поддерживать continuation с `sessionID` (проверенная база — OpenCode 2.1.4).
На Mac необходим отдельный маленький smoke: наличие команды, независимый reviewer,
корректные scope/hash/counters и отсутствие agent-created temp files. Linux-тесты
не являются Mac acceptance. По запросу подготовлен отдельный пакет вне Git:
`~/Downloads/delegated-review-mac-2026-11-12/` — актуальные `delegated-review.md`,
model-free `review.md`, установочный `README.md` и русское описание для человека
`delegated-review.README.md`. Команда и body reviewer побайтно сверены с исходниками.
Человеческое описание размещается в корне `~/.config/opencode`, не в `commands/`;
README пакета содержит таблицу всех путей. Старые Downloads-файлы сохранены.
Корпоративная конфигурация не менялась; пакет на Mac ещё не запускался.

## Применение и последующая проверка

1. Проверить diff и сделать новые source-файлы видимыми Git flake, не коммитя
   автоматически. До этого `.#...` не включает untracked файлы:

   ```fish
   git add -- home/apps/opencode/commands/delegated-review.md home/apps/opencode/config/review-system.md
   ```

   Пользователь применяет только нужный HM-профиль:
   `home-manager switch --flake .#samov-laptop` (либо `samov-laptop-old`/`samov-desktop`).
   NixOS не меняется; агент не выполняет сборку или activation.
2. Проверить наличие `/delegated-review` в TUI, при необходимости `/reload`.
   Для этого config-only изменения restart сервиса и переоткрытие binary не нужны.
3. В отдельной тестовой сессии запустить команду на небольшом согласованном scope;
   проверить точный диапазон, независимого ребёнка, coverage и итоговый отчёт.
4. Terminal failure → same-child continuation уже проверен native mock выше.
   Остальные эксперименты согласовывать отдельно: потерянный ID, running child
   без duplicate prompt, partial report, replacement, scope change и исчерпание
   бюджета. Реальный
   provider failure проверять при естественном возникновении, не создавая нагрузку
   для намеренного достижения concurrency limit. Эти оставшиеся проверки пока
   не выполнены.
