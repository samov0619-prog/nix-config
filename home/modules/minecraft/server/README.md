# Управление сервером

## Запуск

```bash
systemctl --user start minecraft.target
```

По умолчанию запуск ручной. Для остановки и полного перезапуска стека:

```bash
systemctl --user stop minecraft.target
systemctl --user restart minecraft.target
```

Это альтернативные операции, не обязательная последовательность. Три службы имеют
`PartOf=minecraft.target`: stop останавливает Java/Packwiz, restart повторяет
serve → update → Java. Backup watcher и уже запущенная передача независимы от target.
`Restart=always` не отменяет явную остановку через systemd.

Packwiz serve считается готовым после успешного HTTP-запроса к
`http://127.0.0.1:8180/pack.toml`: curl игнорирует `.curlrc`, обходит proxy, ограничивает запрос одной
секундой и повторяет ошибки до примерно 30 секунд; общий start timeout — 40 секунд.
`ExecStartPost` участвует в `After`, поэтому update ждёт этой проверки. Это HTTP
readiness, не проверка корректности всего pack: его проверяет сам installer.
После успеха update остаётся `active (exited)` (`RemainAfterExit=true`), чтобы
restart target повторял update, а обычный рестарт Java не обновлял моды неожиданно.

При ошибке serve/update Java не должна стартовать. Сам `minecraft.target` через
WantedBy может остаться active при неработающем дочернем service: проверять нужно
службы и журнал, не один target. После устранения причины перезапустить target.
Автоматический рестарт только Packwiz не является восстановлением всего стека.
Остановка Java использует штатный SIGTERM и timeout systemd; сохранение реального
мира и достаточность времени остановки требуют отдельной проверки на рабочем сервере.

## Автозапуск: явный opt-in

В конфигурации нужного Home Manager host:

```nix
minecraft.server.autoStart = true;
```

Default — `false`. Опция добавляет target к user `default.target`, то есть запуску
пользовательского systemd manager, не обязательно GUI-логину (например, при linger).
Применять через HM, не через ручной `enable`. Возврат к `false` убирает эту привязку;
для немедленной остановки уже работающего стека использовать `stop minecraft.target`.
`minecraft.server = null` по-прежнему не создаёт ни серверные, ни backup units.

## Логи

```bash
journalctl --user -u minecraft-server -f
```

## Синхронизация backup

Watcher `ftb-backups-fabric-1214.path` включён независимо от Minecraft через
user `default.target`. `PathChanged` следит за закрытием записанного
`backups/backups.json`, а не за каждым изменением растущего ZIP. Уже существующий
manifest при включении watcher сам по себе не означает немедленный upload.

`backup-sync.py` рассчитан на стандартный плоский каталог FTB Backups 2 **1.0.29**:
`backups.json` и перечисленные в нём ZIP. Архивы вне этого каталога, вложенные
каталоги, другие форматы и посторонние файлы блокируют весь sync, а не молча
исключаются из зеркала. Пути из старого manifest перебазируются по имени архива
на текущий каталог; содержимое manifest сохраняется без переписывания.

### Условия допуска

- Нужен хотя бы один архив; отсутствующий источник, пустой каталог или один
  `backups.json` не допускаются.
- Все записи должны быть завершены: `complete=true`; отсутствующее поле
  принимается как `true` по upstream-контракту старых записей. `complete=false`
  откладывает весь набор до следующего события, а не отправляет неполное зеркало.
- Проверяются положительный размер, его совпадение с файлом, синтаксис SHA‑1,
  непустой ZIP central directory и точное соответствие файлов manifest.
  Символические ссылки вместо source/файлов не допускаются.
- Manifest и файловые идентификаторы повторно проверяются после подготовки.
  Полный SHA‑1/CRC содержимого **не вычисляется**, восстановление этим не проверено.
  После `complete` архивы должны оставаться неизменяемыми, как у указанного FTB.

### Временный набор и зеркало

Рядом с `backups/` создаётся приватный служебный `.ftb-backup-sync/` с маркером
владения, lock и `snapshot/`. ZIP закрепляются hard links; manifest копируется.
Это не копирует гигабайты данных, но **временно удерживает место** архивов,
удалённых локальной ротацией во время передачи. Нужна одна файловая система
с поддержкой hard links; при отказе нет fallback на живой каталог.

Параллельный запуск откладывается через `flock`; lock передаётся rclone, чтобы
пережить завершение одного wrapper. После обычного выхода, включая
ошибку rclone, snapshot удаляется. После принудительного завершения он может
остаться и удерживать место до следующего запуска: тот очищает только snapshot
в своём приватном marked cache. Неизвестный cache или ссылки вместо служебных
путей не очищаются. Исходный `backups/` helper не удаляет и не ротирует.

Rclone синхронизирует **весь** подготовленный набор, включая manifest, в прежний
`gd-backups:minecraft_backups_fabric_1.21.4`, с прежним `--bwlimit 2200k --quiet`.
Добавлены `--check-first --delete-after --drive-use-trash=true`: удаления — после
передачи, через штатную корзину Drive. Лимит пяти задаёт FTB, не helper; защищённые
FTB snapshots могут увеличить набор. Ротация во время upload не удалит hard links,
но зеркало отражает выбранный набор, не гарантирует latest-state в каждый момент.

Это **не** независимый архив: корректный, но уменьшенный source может удалить
cloud-only файлы. От частичного случайного удаления или неверно выбранного мира
guard полностью не защищает. Drive trash занимает квоту до 30 дней; постоянное
удаление и очистка общей корзины не включены.

### Проверка и применение

1. Безопасные локальные фикстуры, только fake rclone, без сети:

   ```bash
   python3 -B home/modules/minecraft/server/test_backup_sync.py
   ```

2. Необязательно: отдельно собрать нужный HM output без activation, например Acer.
   Сам `home-manager switch` тоже сначала собирает конфигурацию; отдельный build
   нужен только для разделения сборки и применения:

   ```bash
   nix build --no-link .#homeConfigurations.samov-laptop.activationPackage
   ```

3. До первого реального upload отдельно проверить source, настроенный remote,
   свободную квоту и восстановление на изолированных данных. Старое облако само
   не восстановится: `sync` не скачивает мир. На Acer в последней диагностике
   source и rclone remote отсутствовали; не создавать пустой source ради проверки.
4. После личного review применить `home-manager switch --flake .#samov-laptop`
   (на desktop — `samov-desktop`). NixOS rebuild не нужен. Watcher автоматический:
   при появлении завершённого набора он может начать реальный sync.
5. Смотреть журнал и причину пропуска/ошибки:

   ```bash
   journalctl --user -u ftb-backups-fabric-1214.service -n 50 --no-pager
   systemctl --user status ftb-backups-fabric-1214.path ftb-backups-fabric-1214.service
   ```

`Backup sync deferred` — активная запись/гонка/другой запуск, exit 0 без передачи;
`Backup sync blocked` — небезопасный источник/staging или файловая ошибка, exit 2.
Ошибка rclone передаётся systemd. Автоматического retry по таймеру нет: следующее
изменение manifest даёт новую попытку; постоянная incomplete-запись блокирует
sync до устранения причины. Ручной start service выполняет **реальный sync**, не тест.
Unit fixtures не проверяют настоящий systemd watcher, Drive/API, сеть или restore.

## Проверки lifecycle без Minecraft

Из корня репозитория, без сборок и запуска user services:

```fish
nix eval --impure --json --offline --option allow-import-from-derivation false \
  --expr 'let f = builtins.getFlake (toString ./.); in import ./home/modules/minecraft/server/test_module.nix { lib = f.inputs.nixpkgs.lib; }' \
  | python3 -B home/modules/minecraft/server/test_lifecycle.py /dev/stdin
```

Нужны локально доступные flake inputs, Python, curl и systemd-analyze. Nix fixtures
проверяют null/manual/opt-in, зависимости и неизменность backup. Python проверяет
граф через `systemd-analyze verify` на fixture units с подставленными executable
paths; ни одна unit не запускается. Настоящая curl-команда проверяется на tiny
loopback HTTP fixture: success без proxy/влияния `.curlrc`, retry после 503, ограниченный отказ 404.
Тест занимает около 33 секунд, параметры retry не ослабляются ради ускорения.
Это не тест настоящих Packwiz/Java, native HM unit rendering или runtime stop/restart.

Полную ручную проверку выполнять позже **на машине с подготовленным сервером**:

1. Применить HM после review (команды выше); на Acer запускать Minecraft ради теста
   не требуется. Оставить `autoStart=false`, пока не выбран другой режим.
2. Запустить target, проверить `packwiz-serve`, `minecraft-packwiz-update` и
   `minecraft-server` через `systemctl --user status`; в журнале update должен
   завершиться до запуска Java. Проверить подключение клиента.
3. Остановить target: Java и Packwiz должны стать inactive; проверить завершение
   сохранения мира в журнале. Backup watcher при этом остаётся включённым.
4. Запустить снова и отдельно проверить restart target: update повторяется, старые
   Java/Packwiz не остаются параллельно. Это действия с реальным миром, не fixtures.
