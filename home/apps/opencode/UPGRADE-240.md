# OpenCode 2.4.0 — данные, backup и согласованный rollback

U5: **миграция копии и чтение свежей restore-копии старым binary прошли**.
Target: `44aed4fd144611879046ae923c25541f913780ad`. После изолированных проверок
пользователь применил HM и запустил 2.4.0; подтвердил Free/Paid, тему,
историю/вложения и подключение MCP. Восстановление живой установки не проверено.
Агент живые пути/сервис не менял.

## Пользовательское применение — 2026-11-23

Пользователь сообщил успешный switch и предоставил вывод:

```text
opencode v2.4.0+44aed4f
http://127.0.0.1:13420
http://127.0.0.1:13420
```

Это подтверждает выбранный binary и результат `service start/status`, не полную
приёмку API/истории/моделей/MCP. Сообщение о 388 unread Home Manager news items —
уведомление, не ошибка activation. Свежий backup готовился пользователем перед
switch; prompt показывает каталог `~/b/o/20261123T202050Z`, но отдельный вывод
его `BACKUP_OK`/hash checks агенту не передан. Не приписывать ему проверку первого
снимка. Проверенный первый backup и generation 65 сохраняем, GC не запускаем.

Последующим сообщением пользователь подтвердил: Free и Paid работают, смена темы
корректна, история и вложения на месте, MCP server подключается. Это ручная
домашняя smoke-приёмка, не проверка всех MCP tools, effort, квоты или recovery.
Mac и полное live restore остаются отдельными этапами.
Агенту запуск живых models/MCP не разрешён. При сбое нужен
согласованный rollback binary/config/Data/State, а не только Nix generation.

## Что происходит со старыми сессиями

- `session/info.ts:fromRow` читает сохранённые model/variant и metadata.
  Таблицы `local.model-routing` версии 1 и scoped overrides остаются в metadata;
  новая таблица из `routing-models.json` не подменяет их автоматически.
- Новый общий `SessionRunnerModel.select` читает **живую root policy** и использует
  её и для tool preflight, и для запроса. Child metadata не заменяет root policy.
  Legacy aliases Sol/Luna канонизируются при чтении, без переписи истории/БД.
- `/switch-paid` и `/switch-free` — явный reset профиля **всей семьи**. Команда
  поднимается к root, проверяет все модели/variants и записывает свежий
  `routingState(mode)`, сохраняя остальные metadata. Ручные root/child overrides
  внутри прежнего routing state удаляются. Это не «обновить только helpers» и
  не безопасная операция для сохранения всех прежних ручных настроек.
- Команда не переписывает durable models каждого ребёнка, не пересчитывает старые
  usage/messages и не меняет другую семью. Она инвалидирует/синхронизирует root
  cache. Уже отправленный запрос не отменяется и не меняет модель задним числом.
  Не переключайте профиль посреди работы, рассчитывая на атомарный hot migration:
  ранний preflight и последующий запрос — разные моменты чтения policy.
- Held background summary — текст в памяти; переключение профиля не гарантирует
  его удаления или переписывания Paid-моделью. Подробности U4 — в
  [CONFIG-CHECKLIST.md](CONFIG-CHECKLIST.md#u4-compaction-и-стоимость--source-пути-проверены-background-оставляем).
  Native compaction в этом переезде **не включается**.

## Точные пути и границы

По `packages/util/src/global-roots.ts`, `global.ts`, CLI `database-path.ts`,
`services/service-config.ts` и TUI `context/storage.tsx` target revision:

| Объект                              | Разрешение пути                                                                                                                      |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Data                                | `${XDG_DATA_HOME:-$HOME/.local/share}/opencode`                                                                                      |
| State                               | `${XDG_STATE_HOME:-$HOME/.local/state}/opencode`                                                                                     |
| Cache                               | `${XDG_CACHE_HOME:-$HOME/.cache}/opencode`                                                                                           |
| Config                              | `OPENCODE_CONFIG_DIR`, иначе `${XDG_CONFIG_HOME:-$HOME/.config}/opencode`                                                            |
| Personal JSONC                      | Явный `OPENCODE_CONFIG`; дома HM задаёт соседний `opencode-local/opencode.jsonc`                                                     |
| DB                                  | `OPENCODE_DB`: абсолютный путь или путь относительно Data; `:memory:` не файл                                                        |
| DB без override                     | Для `prod/latest/dev/beta/next` — `Data/opencode.db`; прочие каналы — `opencode-<sanitized-channel>.db`, если не отключён channel DB |
| Service config, домашний prod       | `Config/service-prod.json` — private settings/env/password                                                                           |
| Service registration, домашний prod | `State/service-prod.json` — текущие PID/URL/password, не переносимая регистрация                                                     |
| TUI storage, домашний prod          | `State/prod/tui/<key>.json`; locks — `State/prod/locks`                                                                              |
| Logs                                | `Data/log/`; приватные журналы plugins — также внутри State                                                                          |

Обозначения `${...:-...}` в таблице — описание fallback, **не Fish-команды**.
XDG применяется также на macOS: эти исходники не используют автоматически
`~/Library/Application Support`. У Mac нужно установить фактический channel,
а не предполагать `prod`. `latest/dev/beta/next` используют `service.json`,
прочие каналы — `service-<sanitized-channel>.json`; старые hashed registrations
могут мигрироваться с проверкой версии. `prod` и `latest` используют одну default
DB, но разные service/TUI namespaces: это **не изоляция данных**.

`Global.Path.config` — исходный XDG config path, а acquired Global service
учитывает `OPENCODE_CONFIG_DIR`. CLI settings находятся в global config, не
в personal JSONC. Сохранённый service env не переопределяет `XDG_STATE_HOME`:
registration остаётся там, где сервис был запущен. Проверять нужно окружение
именно старого server-процесса, включая service env и отдельные standalone/serve
процессы. Не выгружайте значения/секреты в отчёт; достаточно приватной карты путей.

## Почему одного отката binary недостаточно

Сравнены migration ID lists v2.1.4 (`68bc26b7…`, прежняя домашняя база) и v2.4.0:
50 прежних ID сохранены в начале списка, затем добавлены 14. Это сравнение ID,
не утверждение о побайтной идентичности всех старых migration bodies. На рабочей
копии backup ниже подтверждены именно эти 50 прежних ID и переход к 64.

`database/database.ts` на открытии файла включает WAL и вызывает migration apply.
`database/migration.ts` применяет отсутствующие ID по одному в transactions и
записывает journal; `down`/автоматического восстановления старой схемы здесь нет.
Последующая ошибка не отменяет уже завершённые предыдущие миграции. Неизвестные
старому binary новые ID не являются механизмом downgrade.

Среди изменений: `20261025154125_drop_session_pending` удаляет старую таблицу;
`20261025123711_blob` добавляет media blobs/ref; `20261029002625_session_part`
добавляет отдельное хранение частей сообщений. `session/history.ts` умеет читать
старые inline rows и новые parts; `session/projector.ts` по умолчанию пишет parts
и может переносить inline content при записи. Такая forward/read compatibility
не доказывает, что 2.1.4 правильно прочитает данные после работы 2.4.0.

**Не запускать старый binary поверх обновлённой DB.** HM rollback не восстанавливает
DB, mutable CLI, service env или plugin state. Не редактировать migration journal
для «понижения версии» и не смешивать DB с WAL/SHM от другого снимка.

## Процедура пользователя: остановленный согласованный снимок

Это процедура отдельного окна обслуживания. Выполненный пользовательский снимок
и проверка его рабочей копии зафиксированы ниже; live activation не выполнялась.

1. До обновления зафиксируйте приватно старый binary/store path и версию,
   HM generation, `flake.lock`/исходники, effective channel, config/data/state/cache,
   DB override и подключённые personal/env/voice paths. Не удаляйте прежние
   generations и не запускайте GC до приёмки/окончания rollback window.
   Для определения обычных путей можно использовать `opencode debug paths`
   **до** остановки; это не полная карта env другого уже работающего процесса.
2. Завершите задачи и закройте все TUI/desktop/web clients, standalone/serve и
   другие writers этой DB. Остановите выбранный managed service через его
   `opencode service stop`. Убедитесь, что не осталось writers и автоматического
   respawn через launchd/другую оболочку. До конца backup не запускайте `api`,
   `/reload` или другие команды, способные поднять service. При remote service
   остановитесь: нужен отдельный согласованный backup на стороне владельца данных.
3. Создайте **вне `/tmp`, Git и Nix store** приватный каталог со snapshot label,
   например `$HOME/opencode-backups/<timestamp>`, с mode 0700. Скопируйте с
   сохранением типов/ссылок (`cp -a`) полные config **и personal**, Data, State и
   при необходимости Cache. Если DB вне Data — отдельно скопируйте её и
   существующие `<db>-wal`/`<db>-shm` из того же остановленного состояния.
   Для больших repos/worktrees/snapshots проверьте объём заранее; не заменяйте
   полный согласованный снимок молча копированием одной DB.
4. В manifest запишите source→backup mapping, link targets и хеши файлов;
   проверьте читаемость копии и `PRAGMA integrity_check` **только на отдельной
   рабочей копии DB+sidecars**, не на оригинале/неизменяемом backup. Внешние
   цели ссылок (Nix store generation, env, plugins) тоже должны быть сохранены
   или гарантированно доступны; `cp -a` сохраняет ссылку, а не её внешнюю цель.
   Не публикуйте backup: DB/config/state могут содержать credentials и переписку.
5. Сначала соберите выбранный target и пройдите изолированную 2.4.0-приёмку,
   не указывая живые DB/auth/env/MCP. Отдельная проверка миграции реальных сессий
   возможна только на согласованной приватной копии, без resume/automations,
   provider requests или MCP calls. Для снимка ниже эта проверка **прошла**;
   она не заменяет восстановление установки или живую приёмку.
6. Только после review и приёмки примените домашний HM target (например
   `home-manager switch --flake /home/samov/nix-config#samov-laptop`), передайте
   server-процессу новое personal окружение, запустите `opencode service start`,
   проверьте status/TUI. NixOS activation для одного OpenCode не требуется.
   На корпоративном Mac — отдельный scoped config diff, не этот HM profile.

## Снимок и миграция рабочей копии — 2026-11-23

Пользователь закрыл оба клиента и остановил старый сервис **2.1.4+68bc26b**,
затем сообщил `SNAPSHOT_CREATED`, `CHECKSUMS_OK` и `BACKUP_OK` для
`/home/samov/backups/opencode/261123tNov111795463834z`.
Снимок содержит полные config/data/state/cache, `flake.lock`, paths и manifests
обычных файлов/ссылок. Пользовательский `integrity_check` выполнялся на отдельной
временной копии. Сохранена HM generation **65**; `PERSONAL=absent`.
Исходный backup остаётся неизменяемым; до завершения приёмки/rollback window
generation 65 сохраняем, GC не запускаем.

После отдельного разрешения агент скопировал только DB и имеющиеся WAL/SHM в
приватный `/tmp/opencode/opencode-240-migration-872kpr8y/`, сверив хеши.
SQLite открывалась только там. Перед запуском: **50 migration IDs**, **81 session**,
**11 809 messages**, 5 inbox rows, 0 suspended claims и 0 pending rows;
таблиц schedule/automation ещё нет, background-job KV rows — 0.

Использован штатный собранный `2.4.0+44aed4f`:
`serve --stdio --hostname 127.0.0.1 --port 0`, без `--service` и без API-запросов.
После startup receipt stdin закрыт; оба запуска завершились с code 0 и пустым stderr.
Это не отдельная migrate CLI-команда и не собственный SQL-мигратор:

- `packages/server/src/process.ts:126–134,267–274` включает restart continuity
  только с managed lifecycle. Обычный stdio serve её не получает.
- Automation runner запускается всегда. Здесь это безопасно **из-за проверенного
  отсутствия schedules/automations в исходной копии**: новые migrations создают
  schedule пустой, затем переносят ноль строк в automation. После запусков она
  также пуста. Одного `--standalone` или пустого config для этой гарантии мало.
- Отдельные user/mount/network/PID namespaces: живые `/home/samov` и
  `/run/user/1000` скрыты tmpfs, сеть изолирована. HOME/XDG/config/state/cache/tmp
  направлены в рабочий каталог. Пользовательское окружение, registrations,
  config/plugins/MCP/auth files не переносились; credentials внутри самой копии
  DB не читались в отчёт и не использовались для provider requests.
- Project/Claude discovery, model fetch и filewatcher выключены; fixture config
  задаёт `automations: false`, пустые plugins/MCP и deny `provider.use`.
  `strace` обоих запусков не содержит IPv4/IPv6 connects; только два локальных
  AF_UNIX lookup в `/var/run/nscd/socket` на запуск. Дочерних tool/MCP-процессов нет.

Результат:

- **50 → 64**, точное совпадение с migration ID inventory target; повторное
  открытие не меняет journal, схему или логические данные.
- `PRAGMA integrity_check`: `ok`; `foreign_key_check`: 0 нарушений до/после/повторно.
- Хеши строк всех **18 сохранённых non-journal таблиц** по исходным колонкам
  совпадают. Это включает session IDs/models/metadata, message data с inline
  parts/attachments, events, credentials, permissions и все 5 inbox rows.
  Содержимое строк не выводилось. Пустая `session_pending` штатно удалена;
  новая `time_busy` везде NULL.
- Новые `session_part`, `blob`, `blob_ref`, `job`, `automation`, `machine` пусты.
  Это migration/read-retention, не проверка новых part/blob writes или UI media.
- Повторно прошли manifest `SHA256SUMS` исходного backup и отдельно его DB/sidecar
  hashes, сохранённые до копирования. Живые пути не открывались SQLite и не менялись.

Приватные временные evidence: `before.json`, `after.json`, `reopened.json`,
`verification.json` и startup/syscall logs в указанном рабочем каталоге. Там же
механические probes; они не заменяют native migration. Каталог содержит историю и
credentials из DB, не публиковать; `/tmp` не гарантирует сохранность. Долговременный
итог — этот раздел и [BENCHMARK.md](BENCHMARK.md).

Старый binary на мигрированной DB не запускался. Проверка отдельной свежей
pre-upgrade restore-копии описана ниже; полного live restore она не заменяет.

## Изолированная restore-репетиция — 2026-11-23

После следующего разрешения создана **новая полная копия исходного backup**:
`/tmp/opencode/opencode-240-migration-872kpr8y/restore/snapshot/`.
Мигрированная DB из предыдущего прогона не использовалась. До startup прошли
manifest hashes, буквальное совпадение всех **27 symlink targets**, доступность
их Nix-store целей и старой generation 65; `cli.json` — обычный файл, не ссылка.
Все symlink targets находятся в Nix store. Это доступность сейчас, не GC protection.

Старый binary из `paths.txt`, **2.1.4+68bc26b**, запущен через native `serve --stdio`
в прежней namespace-изоляции. Loopback поднят только внутри отдельного network
namespace. Из restored snapshot использован Data; настоящий config/plugins/MCP,
service registration, PTY state и пользовательское окружение не активировались:
runtime config/state/cache отдельные, model fetch/project discovery выключены,
provider use запрещён. Поэтому это **restore Data + native read acceptance**, а не
полная активация старого рабочего окружения.

Через native API выполнены **207 GET requests**: info, active, постраничные sessions
и messages всех сессий. Payloads декодировались только в памяти, сохранялся общий
digest, а не тексты/секреты. Никаких prompts, imports, view/mutation или resume calls.

- Native API прочитала **81 session / 11 809 messages**. Session IDs, metadata,
  models/variants, message IDs/types и порядок совпадают с исходной DB.
- Active до/после — 0. Старый сервер чисто завершился по stdin EOF с code 0;
  stderr пуст. Нет outbound IPv4/IPv6 connects или tool/MCP execs;
  только локальные nscd lookups. Запросы API шли к изолированному loopback listener.
- Схема и **50 migration IDs** не изменились; integrity `ok`, FK violations 0.
  Логические row hashes всех таблиц, кроме `project`, совпадают;
  история, credentials, permissions и пять inbox rows не изменились.
- **Строгая проверка полной неизменности DB не прошла:** только у двух `project`
  rows `time_archived` изменился с NULL на timestamp. Все другие project columns
  совпадают. Причина подтверждена старым pinned source: `Project.sweepNode`
  включён в `packages/server/src/routes.ts`; `project.ts:404–475` архивирует idle
  projects с отсутствующими canonical directories. Оба каталога существуют на
  хосте, но намеренно скрыты tmpfs в тестовой изоляции. Это наблюдаемый эффект
  окружения, не потеря истории; проверка не ослаблена и не выдана за полный pass.
  Никакого обхода или production-fix ради устранения этого эффекта не добавлено.

Исходный backup повторно прошёл `SHA256SUMS`. Приватные evidence в `restore/`:
`inventory.json`, `before.json`, `after.json`, `api-result.json`, `verification.json`
и native logs. Исходный failed full-invariance assertion сохранён в probe;
отдельная механическая сверка установила точную границу изменений. DB/логи не
публиковать; сохранность `/tmp` не гарантируется, этот раздел — durable summary.

**Ещё не проверены:** полноценная активация restored config/state/plugins и
старого managed service, замена живых путей, UI истории/attachments/вкладок,
живые models/MCP и Mac. Restore поверх живых путей не выполнялся; новая HM
конфигурация не применялась, коммитов нет. Generation 65 сохраняем, GC пока не запускаем.

## Rollback в том же окне

1. Снова остановите все writers/автозапуски, как выше. Сохраните post-upgrade
   состояние отдельно: rollback к backup теряет последующие записи; не затирайте
   их и не выдавайте восстановление за автоматическое объединение историй.
2. Восстановите старую HM generation/binary **вместе** с её config/personal,
   полным Data/DB и durable State из одного pre-upgrade снимка. Подготовьте
   восстановление в отдельных каталогах и замените согласованные пути целиком,
   не накладывайте старые файлы поверх новых sidecars. Вне-Data DB и её sidecars
   восстанавливаются по manifest. Ни одна из этих операций не выполняется агентом
   без отдельного разрешения на точные пути/перезапись/activation.
3. Сохраните service config/password/env из снимка, но **не активируйте старую
   runtime registration с прежним PID/URL**: при подготовке restored State не
   переносите выбранные registration files (включая соответствующие legacy
   записи). Оригинальный backup оставьте нетронутым. Их создаст native service
   start. Восстановите старое окружение и проверьте config symlink targets;
   живой `cli.json` также должен быть обычным writable файлом.
4. Запустите именно старый binary/service, проверьте версию, старые session IDs,
   историю/attachments, profile/overrides, вкладки, permissions и отсутствие
   непредусмотренных задач. Если старый store path/backup невалиден — остановитесь,
   не пробуйте старый binary на новой DB как «временный» обход.

Source-fixtures сами по себе не проверяют backup completeness или реальную DB.
Отдельный прогон выше проверяет native migration конкретной копии реальной истории,
но не восстановление установки или model/MCP acceptance.
