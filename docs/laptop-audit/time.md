# Фиксированный пояс и синхронизация часов

[Каталог](README.md) · [Решение пользователя](feedback.md)

## Политика

Личные workstation-профили используют **Europe/Moscow** и сетевую синхронизацию часов.
Server и installer сохраняют штатные настройки NixOS, без привязки пояса к месту
пользователя и без включения timezone geolocation.
Часовой пояс задаёт отображение местного времени, NTP корректирует сами часы;
отключение геолокации пояса не отключает синхронизацию.

На NixOS это [hosts/profiles/time.nix](../../hosts/profiles/time.nix):

- `time.timeZone = "Europe/Moscow"`;
- `services.timesyncd.enable = true`;
- `services.automatic-timezoned.enable = false`.

Flake явно включает policy только в `modules` laptop-old, desktop, laptop и
desktop-next. Её нет в общем `mkNixos`, server и server-installer.
NTP server defaults/DHCP discovery и RTC policy не меняются.
Не отключаем все location services: меняется только выбор timezone.
Расписания, заданные в локальном времени, теперь используют фиксированный пояс.

На server раньше явно задавался Europe/Moscow. По уточнению пользователя эта
привязка удалена, а не восстановлена: штатное `time.timeZone = null` не управляет
`/etc/localtime`; на fresh system пояс по умолчанию UTC, но он может быть задан
вручную. NTP по умолчанию включён для обычной системы, геолокация пояса — нет.
Для установленного сервера после будущего deploy проверить `timedatectl status`
и локальные расписания, не обещая и не навязывая переход в UTC. Сам сервер агент
не менял. UTC обычно удобен для сопоставления серверных логов, но это не новая
декларативная настройка. Часы всё равно должны синхронизироваться по сети.
Каркасы `*-next` от этого не становятся готовыми к установке.

## Проверка и применение NixOS пользователем

1. Проверить diff, затем собрать только затронутый текущий host:

   ```fish
   nix build --no-link .#nixosConfigurations.laptop.config.system.build.toplevel
   ```

2. На Acer применить NixOS, **не** Home Manager:

   ```fish
   sudo nixos-rebuild switch --flake .#laptop
   ```

   На desktop использовать `.#desktop` на его машине. Нужный будущий deploy VPS
   выполняется отдельно с рабочей станции через `--target-host`, внешний settings
   input и сверку target по [серверной инструкции](../../SERVER_AI_INSTRUCTIONS.md).
   Этот шаг не разрешает автоматический deploy на VPS или установку `*-next`.

3. При доступном интернете проверить:

   ```fish
   timedatectl status
   timedatectl timesync-status
   systemctl is-active systemd-timesyncd.service
   systemctl is-active automatic-timezoned.service
   ```

   Ожидается Europe/Moscow (UTC+03:00), активный timesyncd и после успешного обмена
   `System clock synchronized: yes`; automatic-timezoned inactive либо отсутствует.
   Последний `is-active` в этом случае возвращает ненулевой exit code — ожидаемо.
   Наличие NTP-настройки без сети само по себе не доказывает синхронизацию.

## Mac: вручную, не через standalone HM

В этом репозитории нет nix-darwin. HM `samov-mac` не управляет системными часами;
никаких `sudo` или macOS defaults mutations в activation не добавлено.

1. В System Settings → General → Date & Time оставить автоматическое получение
   даты/времени включённым, не меняя настроенный NTP server без необходимости.
2. Отключить автоматический выбор **часового пояса по местоположению** и выбрать
   Moscow / Europe/Moscow. На управляемом корпоративном Mac при запрете MDM
   обратиться к администратору, не обходить ограничения.
3. Проверить отображаемый пояс и работу сетевой синхронизации на Mac.

Системные изменения, live NTP и интерфейс macOS агентом не проверялись.
