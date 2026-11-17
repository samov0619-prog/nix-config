# /delegated-review

Домашний HM-модуль устанавливает `commands/delegated-review.md` как
`~/.config/opencode/commands/delegated-review.md`. Профиль `agents.review` объединяет
`config/review-analysis.md` и `config/review-system.md`, сохраняя model routing и permissions.
Это config-only изменение, без binary patch, плагина или нового сервиса.
Исходные файлы в Downloads и живая корпоративная конфигурация не меняются.
Исходники переноса на новую корпоративную базу — в
[`macos/trf-review/`](macos/trf-review/README.md); единый переносимый Git-патч и
порядок установки описаны там. Это не обновление старого Mac seed.
Родитель и reviewer не создают временные scripts/manifests/reports/directories,
даже вне проекта: механические вычисления выполняются inline, результаты остаются
в контексте сессии. Штатные runtime logs/session storage этим не запрещаются.

```text
/delegated-review
/delegated-review current branch
/delegated-review last 2 commits
/delegated-review working tree
/delegated-review последние 3 коммита
/delegated-review src/auth.ts + tests
```

Без аргументов (или с одними пробелами) сначала проверяются **незакоммиченные
изменения**: staged/unstaged tracked и релевантные неигнорируемые untracked файлы.
Если они есть, проверяется только working tree относительно HEAD, без коммитов
ветки. Если их нет — **текущая ветка** от merge-base с локальной базой до HEAD.
Посторонние untracked артефакты и ignored файлы не включаются и не запускают выбор
working tree. Явный аргумент имеет приоритет; выбранный дефолт озвучивается.
Неоднозначная база/detached HEAD требуют уточнения, unborn HEAD — явного указания
ограничения; произвольные коммиты вместо них не выбираются. Если изменений для
ревью нет, агент сообщает об этом и не вызывает reviewer.

## Обычное и делегированное ревью (2026-11-16)

Обычное «поревьюй» выполняется **в текущем разговоре**, с его контекстом и без
смены агента/модели, fork или запуска ребёнка. Родитель сначала читает установленный
`review-analysis.md` из активного глобального config directory OpenCode; HM
устанавливает его рядом с `AGENTS.md`. Встроенная `/review` не заменяется и тоже
работает в текущем потоке. Сам запрос ревью не разрешает правки/сборки/коммиты и не
снимает Plan restrictions. Последующий запрос реализации возвращает обычную работу,
без необходимости переключать роль обратно.

`review` — один отдельный read-only subagent для **явно делегированных** проверок.
Его system prompt содержит те же правила анализа плюс ограничения/continuity
из `review-system.md`; это не второй агент. `/delegated-review` остаётся
оркестратором scope/fingerprint, выбранного handoff, recovery и полного отчёта.
Явная просьба отдать code review отдельному reviewer сначала читает применимый
установленный template этой команды, а не создаёт второй workflow. Model override
не передаётся: сохраняются reviewer route и Free/Paid family policy.

Маршрутизация — инструкция модели, **не программный перехват ключевых слов**.
Обсуждение правил, цитата, отрицание/будущий запрос, обычная разработка/debug и
самостоятельная проверка не запускают отдельный review workflow. Активная команда
сама владеет запуском: второй reviewer не добавляется. При недоступном `review`
делегированный workflow сообщает ограничение без `general` или self-review вместо
ребёнка. Обычному ревью в текущем потоке доступность subagent не требуется.
Явный запрос аудита записанных Chrome-MCP результатов остаётся специальным
делегированным workflow, а не обычным code review; см.
[Chrome-контракт](DELEGATED-REVIEW-CHROME.md#согласование-с-обычным-запросом-ревью-2026-11-16).

Текущая аналитическая policy — `evidence-v5`; критерии анализа/вердикта находятся
в **одном** `review-analysis.md`: обычное ревью читает его, Nix включает точные
байты в reviewer system prompt. В командах нет второй аналитической policy.
Перед блокирующим finding обязательна полная релевантная цепочка от события
до результата: типы/signatures, callers, wrappers/hosts, инжекция/defaults и порядок
spread. Частичный поиск не доказывает отсутствия; нужно искать опровержение своего
вывода. Предлагаемый фикс также проверяется на success/cancel/error paths и
изменении состояния во время `await`. Архитектурное предпочтение не становится
blocker без обязательного правила или конкретного существенного эффекта. После
снятия finding вердикт пересматривается, а не сохраняется через повышение nits.

Новая делегированная задача начинает нового ребёнка без `sessionID`; recovery относится только
к уже начатой текущей задаче. Отменённая задача не возобновляется из-за `/reload`
или сходства scope: нужен явный запрос продолжить её и сверка ledger/identity.
Диагностика recovery читает paginated metadata/messages в памяти, не создаёт
экспорты/probe-файлы. Решающее причинное звено нельзя заменять словами прежней
модели либо считать доказанным, одновременно отправляя его проверку в optional.

Компиляция не обязательна при каждом ревью: сначала определить, какую
неопределённость снимет штатная проверка, её стоимость и побочные записи
(`--noEmit` не исключает incremental metadata). Неизвестные/дорогие/изменяющие
проверки не запускаются без необходимого разрешения. Source review не подменяется
ни passing typecheck, ни обязательным запуском всей системы.

38 лёгких Node-проверок settings/static/hash, прежнего synthetic behavior oracle
и Chrome проходят, включая три исполняемых теста опубликованного exclusive-write
recipe. Guards проверяют текст/подключение инструкций, writer-тесты — сам рецепт,
не семантическую маршрутизацию, completeness/redaction или качество модели.
Дополнительно проходит HM evaluation test: проверяет установку общего файла и
включение тех же байтов в reviewer system prompt с обоими decision-support settings,
без сборки/активации. Итого 39 checks. Новых model/runtime/PTY runs,
сборок, activation, restart сервиса и корпоративных правок нет. Nixfmt выполнен;
Prettier недоступен;
layout сохранён без подмены formatter. Процедура новой модельной приёмки — в
[`EVALUATION.md`](tests/fixtures/delegated-review/EVALUATION.md); она пока не выполнена.

## Разделение ответственности

### Основа требований — `sources-v1`

До анализа code review общий `review-analysis.md` устанавливает основу требований.
Внешнее ТЗ обязательно только при явном правиле применимого `AGENTS.md`, а не по
наличию MR, GitMCP, hostname или названию ветки. Без такого правила достаточные
согласованные требования из разговора/документации не вызывают вопрос «где ТЗ?».
Неясное существенное поведение всё равно требует конкретного уточнения.

Явная ссылка пользователя имеет приоритет; иначе проверяются зацепки выбранного
MR/ветки и связанные задачи/документы. Нельзя подменять source branch чужого MR
текущим checkout, угадывать префикс по цифрам или считать первый поисковый результат
подходящим. Нужны содержание, связь с задачей, применимые контур/release и ревизия.
Недоступный обязательный источник — pending input/incomplete, не отсутствие ТЗ
и не дефект кода. Техническое ревью без ТЗ — явное согласование для этой задачи.

Оркестратор разрешает источники **до запуска ребёнка**, передаёт релевантные
разделы/выдержки с provenance, не весь development transcript. Reviewer сверяет
основу и проверяет материальные требования по реализации, даже если код выглядит
нормально. Источники не меняют схему `dr-scope-v1`; их версии и изменения отмечаются
отдельно. Пассивный Chrome-аудит сохраняет историческую evidence boundary без
нового поиска ТЗ. Сценарии приёмки и ограничения автоматических guards:
[`tests/fixtures/review-requirements/EVALUATION.md`](tests/fixtures/review-requirements/EVALUATION.md).

### Оркестратор и reviewer

Команда остаётся в текущей сессии (`subagent: false`): родитель определяет scope,
составляет минимальный хэндофф, вызывает независимый `review`, восстанавливает
попытку и возвращает полный отчёт на русском. Модель
не задаётся командой: действует локальная политика выбора моделей. Диалог
разработки, self-review и полный transcript ребёнку не передаются; обычные
project/system instructions OpenCode продолжают действовать.

Для нового native subagent без `sessionID` OpenCode 2.1.4 создаёт пустую историю
и передаёт строку `You are a subagent spawned by another session.` плюс выбранный
prompt. Контекст не требуется «очищать»: новая сессия не является fork. Handoff
нужно отбирать, чтобы родитель сам не скопировал лишнее. Это не security sandbox:
файлы/инструменты, location и унаследованные metadata/permissions остаются общими;
запрет получать постороннюю историю через инструменты — инструкция, не изоляция ОС.
В Chrome выбранная запись намеренно передаётся как evidence, а не как инструкции.

Проверены pinned исходники `68bc26b7da1990ce10ffecfbc1e09eb13aa5d824`:
`packages/core/src/tool/plugin/subagent.ts:153–213` (новая сессия/prompt),
`packages/core/src/session/history.ts:103–123` (история по ID сессии),
`packages/core/src/session/context.ts:126–184` (общие инструкции и сборка контекста).
В этой версии foreground — default, фон задаётся `background: true`; текущая
онлайн-документация про обязательный фон новее pinned реализации. Fork копирует
историю, но не получает `parentID` и не может продолжаться через обычный subagent
инструмент; для согласованного workflow он не нужен.

`review` остаётся общим read-only ревьюером changes **и claims**, а не только
исполнителем этой команды. Он проверяет унаследованные findings, различает
прочитанные файлы и проанализированные review units, проведённые и непроведённые
проверки. Новых checkpoint-файлов нет. Сам `edit=deny` не запрещает запись через
shell: prompt дополняет shell policy, но не является security sandbox. При
недоступном `review` команда останавливается без fallback на другой профиль.

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

## Аналитическая доработка после сравнения R1/R2 (2026-11-13)

Пользователь сравнил два ревью одного диапазона с одинаковой исходной точкой
диалога. Наша R1 пропустила проблему сохранения каретки и одобрила изменения
при незакрытом существенном вопросе по email. Блюр email нашли оба; последующее
уточнение подтвердило требование. Пропавшая подсветка подтверждена пользователем,
но конкретная watcher-причина и достаточность `$nextTick` в экспорте не доказаны.
Не все дополнительные находки R2 подтвердились: unknown-ID concern частично снят
контрактом, проверка темы осталась вопросом. Это конкретный проигрыш R1, не замер
систематического превосходства другой модели/инструкции.

Текущая доработка ставит анализ поведения перед отчётностью: ожидаемое поведение,
релевантные ветки, поздние события/пользовательский ввод, focus/selection и
контрпример к утверждениям о безопасности. Важна вся цепочка, включая callback,
который может исправить промежуточное состояние. Тесты/хэши/coverage не заменяют
такой анализ; непроверенная timing-гипотеза не становится диагнозом.

`APPROVE` допустим с optional improvements или явно принятым риском с источником,
но не с невыполненным существенным требованием или вопросом, меняющим решение
о принятии. Последний означает `REQUEST_CHANGES` до уточнения, **не** выдуманный
подтверждённый дефект/`BLOCKER`. Непроведённый runtime check сам по себе не запрещает
завершить source review. Родитель проверяет согласованность отчёта и при конфликте
просит ребёнка обосновать решение в том же бюджете, не переписывая verdict сам.
Полная команда/recovery ledger ребёнку не передаются. Scope/fingerprint, native
continuation, общий бюджет и model/permission policy сохранены.

Лёгкие проверки этой редакции:

```fish
node --test home/apps/opencode/tests/test_delegated_review.mjs home/apps/opencode/tests/test_delegated_review_analysis.mjs
```

Восемь settings/static/hash checks проходят; два новых text guard сначала падали
на прежних инструкциях. Семь дополнительных тестов исполняют **синтетическую**
задачу: A теряет caret/не скрывает mail, B исправляет оба пути. Контракт явно
разрешает перезапись и unknown-ID restore, исключает subject из проверки — это
отрицательные контроли против false positives. Это проверка корректности
упражнения, **не** реального reviewer, браузера, Vue или корпоративного кода.
Слепая модельная приёмка описана в
[`tests/fixtures/delegated-review/EVALUATION.md`](tests/fixtures/delegated-review/EVALUATION.md).
Она ещё не запускалась; нельзя объявлять аналитическую регрессию исправленной
по одним text guards и oracle-тестам. Агент не выполнял новых сборок, runtime/PTY,
активации или обращений к модели. Prettier недоступен, замена не установлена.

`opc-loc.zip` просмотрен без распаковки/изменения: его обычные command/reviewer
совпали с предыдущей редакцией. Отдельный `/delegated-review-chrome` предназначен
для аудита Chrome-MCP transcript; он и корпоративные personal/config files пока
не менялись. Второй сценарий не считается доработанным или проверенным этим этапом.

### Пользовательский прогон и уточнение behavior-v2

`dlg2.md`/`dlg2 (1).md` предоставлены пользователем вне Git. Expanded command
побайтно совпал с первой аналитической редакцией; исходный diff и пересчитанный
manifest совпали. У worktree изменился путь, не исторические endpoints/байты diff.
Ребёнок `review` выдал REQUEST_CHANGES по email и нашёл потерю каретки, но отнёс её
к UX-полировке на основании согласованного overwrite. Raw child report подтверждает,
что эта аргументация и расширение Wall-exception возникли до перевода родителем.
Полная effective system-инструкция ребёнка в экспорте не показана.

Handoff выявил и родительскую неточность: «ignore unknown temporaryId reject»
вместо «не добавлять bubble; restore всё равно выполняется». Результат tsc был
передан как «clean apart from webpack-env error», а ребёнок сократил его до clean.
Ошибка окружения не доказывает ни чистоту typecheck, ни новые ошибки диффа.

На этом этапе маркер обоих файлов — `Review policy: behavior-v2.`. Handoff теперь
разделяет требования/принятые исключения, наблюдения реализации и открытые вопросы;
сохраняет фактический status/limits проверок и точные side effects каждой ветки.
Reviewer ограничивает согласование конкретными эффектами, не выводит product
acceptance из симметрии кода и сохраняет квалификаторы failed/blocked. Это не приказ
повышать severity каретки. Идемпотентность повторного события без изменений между
вызовами не доказывает сохранность нового ввода; но и не означает сама по себе
дефект, если overwrite прямо разрешён контрактом.

Два новых static guard сначала падали на первой аналитической редакции; текущие
десять settings/static/hash и девять synthetic-oracle checks проходят. Два новых
oracle-сценария различают повтор без изменений и повтор после нового ввода; в
синтетическом контракте оба допускают restore. Это не модельная приёмка behavior-v2:
её живой прогон ещё не выполнен, прежний REQUEST_CHANGES не доказывает новые guards.
Сборок/активации и новых модельных запусков агентом нет. Chrome-сценарий по-прежнему
не дорабатывался.

### Ограниченная пользовательская приёмка behavior-v2

Позднее получены `dlgr2.md`/`dlgr2-sub.md`: expanded command побайтно соответствует
behavior-v2, handoff содержит её маркер, исходные endpoints/diff и пересчитанный
manifest совпадают. Email REQUEST_CHANGES и caret finding сохранены; необоснованные
Wall acceptance и общее обещание безопасной идемпотентности исчезли. Это положительный
результат на одном кейсе, не общее превосходство модели. Effective system prompt
по-прежнему не установлен. Остались переоценка filtered tsc при TS2688 и безусловный
email restore в рекомендации при открытом вопросе о history click. Повтор полного
прогона только ради этих формулировок не рекомендован.

### Chrome-сценарий

После согласования перехода ко второму сценарию добавлен самодостаточный
`commands/delegated-review-chrome.md` с маркером `Audit policy: chrome-evidence-v1.`.
Это отдельный пассивный аудит записанных claims, не запуск browser tests и не
неявное наследование обычной Markdown-команды. Общий reviewer/routing не менялись.
В отличие от первоначального Chrome-варианта различаются effect/role действий,
разрешённый fixture и подмена результата; отсутствие evidence не означает обман.
Изменяемые условия анализируются причинно для конкретного claim, а не по счётчику.
Полный контракт, ограничения export/privacy, coverage/status/verdict и отдельный
трёхфайловый Mac-пакет — [DELEGATED-REVIEW-CHROME.md](DELEGATED-REVIEW-CHROME.md).
Шесть Chrome static/hash/fixture-integrity checks проходят; восемь записей с human
oracle не являются проверкой модели. Живой Chrome/Mac приёмки пока нет.

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

Для аналитической редакции 13.11 подготовлен отдельный четырёхфайловый кандидат
`~/Downloads/delegated-review-mac-2026-11-13-scenario1/` с теми же путями установки.
Он не заменяет предыдущую папку или архив; команда и reviewer body были побайтно
сверены с исходниками первой аналитической редакции. При personal-layer `opencode-local` обновлять
соответствующие существующие пути в этом слое, сохраняя corporate model/permissions,
не создавать конкурирующие определения. Общий `review` влияет и на Chrome-команду,
поэтому для изолированной проверки допустим один project-local профиль после
проверки overrides. Chrome-команда не включена и не принята этим этапом.

Следующее уточнение behavior-v2 подготовлено отдельно в
`~/Downloads/delegated-review-mac-2026-11-13-scenario1-r2/` (те же четыре файла).
Команда и reviewer body совпадают с текущими исходниками; предыдущие пакеты и
пользовательские экспорты/архивы не изменены. В новой команде и роли одинаковый
маркер `Review policy: behavior-v2.`; это версия инструкции, не знак её приёмки.

## Применение и последующая проверка

1. Проверить diff и сделать новые source-файлы видимыми Git flake, не коммитя
   автоматически. До этого `.#...` не включает untracked файлы:

   ```fish
    git -C /home/samov/nix-config add -- home/apps/opencode/config/review-analysis.md
   ```

   Пользователь применяет только нужный HM-профиль:
    `home-manager switch --flake /home/samov/nix-config#samov-laptop`
    (либо `samov-laptop-old`/`samov-desktop`).
   NixOS не меняется; агент не выполняет сборку или activation.
2. Проверить наличие `/delegated-review` в TUI, при необходимости `/reload`.
   Для этого config-only изменения restart сервиса и переоткрытие binary не нужны.
3. На небольшом согласованном scope проверить обычное «поревьюй»: тот же поток,
   контекст/роль/модель, без ребёнка и исправлений. Затем отдельно вызвать
   `/delegated-review`: свежий `review`, выбранный диапазон/manifest/handoff и отчёт.
   Для Chrome дефолт остаётся последним записанным прогоном текущей сессии;
   не запускать повторные browser tests ради проверки маршрутизации.
4. Terminal failure → same-child continuation уже проверен native mock выше.
   Остальные эксперименты согласовывать отдельно: потерянный ID, running child
   без duplicate prompt, partial report, replacement, scope change и исчерпание
   бюджета. Реальный
   provider failure проверять при естественном возникновении, не создавая нагрузку
   для намеренного достижения concurrency limit. Эти оставшиеся проверки пока
   не выполнены.
