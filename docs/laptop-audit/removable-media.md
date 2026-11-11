# Съёмные накопители и открытие каталогов

## Согласованные изменения

- `home/linux/gui-set/default.nix`: меню udiskie задано через
  `settings.program_options.menu = "smart"`. Старый корневой `menu="nested"`
  игнорировался; `smart` — актуальное имя поддержанного иерархического режима
  в udiskie 2.6.2 (`nested` остаётся legacy alias).
- `home/linux/gui-set/xdg.nix`: `inode/directory` и `inode/mount-point` явно связаны с существующим
  `yazi-xdg.desktop`, который запускает `kitty -- yazi %f`, `Terminal=false`.
  Оба типа также объявлены в desktop entry. Так Browse в udiskie и другие вызовы `xdg-open` для каталога открывают Yazi,
  а не штатный Kitty shell через прежний `kitty-open.desktop`.

Обе настройки общие для Acer/desktop/Lenovo HM. Mac/server не меняются.
Автомонтирование, уведомления, tray=`auto`, UDisks2/polkit, права и правила
авторизации остаются прежними. Не добавлены отдельный file-manager wrapper,
AppIndicator override, sudo или новое меню. Архивные/браузерные associations,
Neovim handler и FileManager1 не меняются. Browse каталога через MIME и
FileManager1 ShowItems — разные входы; исправления не подменяют друг друга.

Android/MTP остаётся отдельной отложенной задачей: эти изменения его не добавляют.
Состояние authentication-agent и настоящий storage authorization prompt этим
не проверены и не исправляются; исходные границы аудита — в [журнале](feedback.md).

## Диагноз Browse на Lenovo, 12.11.2026

На уже смонтированной exFAT-флешке `xdg-mime query filetype` в окружении udiskie
возвращает `inode/mount-point`. Для него default был пустым, хотя для обычного
`inode/directory` уже был выбран Yazi. Installed udiskie 2.6.2 вызывает `xdg-open`
с путём монтирования; generic route установленного xdg-utils 1.2.1 при отсутствии
обработчика доходит до браузерного fallback. Это объясняет сообщённый Firefox:
наследования `inode/mount-point` от directory в shared-mime-info недостаточно для
этого пути выбора default. Отдельный launcher udiskie не нужен.

Проверки были read-only: содержимое флешки не открывалось, mount/remount не выполнялись.
Пользователь затем применил HM и подтвердил успешный Browse. Read-only проверка
12.11.2026 подтверждает installed default `inode/mount-point` → `yazi-xdg.desktop`.
Это пользовательская UI-приёмка, не независимое наблюдение окна агентом и не
проверка всех носителей, unmount/eject или других хостов.

## Воспроизводимые проверки

Из корня репозитория, Fish:

```fish
set declarations (mktemp /tmp/opencode/removable-declarations.XXXXXX.json)
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/gui-set/tests/test-xdg-declarations.nix > "$declarations"
set udiskie_package (nix eval --offline --raw .#homeConfigurations.samov-laptop-old.config.services.udiskie.package.outPath)
python3 -B home/linux/gui-set/tests/test_removable_launch.py --declarations "$declarations" --udiskie-package "$udiskie_package"
```

Пакет udiskie должен уже находиться в store, например после пользовательской
сборки/применения HM; evaluation сама его не строит. Нужны Python и Bash.

- Выбранные merged declarations пяти профилей проверяют оба явных MIME defaults,
  `Terminal=false`, поддержанную секцию меню и прежние automount/notify/tray,
  Neovim/Yazi/HTML settings; Mac/server остаются без этих GUI handlers.
- Девять Python tests используют настоящий generated desktop text из
  `makeDesktopItem/writeTextFile`, AST-extracted installed udiskie `Config`
  и `prompt.browser`, а также извлечённые настоящие функции installed xdg-open.
  Настоящий installed xdg-mime выбирает default из изолированных mimeapps/desktop
  файлов; наблюдённый MIME подаётся тестом, не определяется на реальном устройстве.
  Fake Popen перехватывает Browse, fake Kitty/Yazi фиксируют argv и UID/EUID/cwd.
  Проверены menu=`smart`, контроль игнорируемого корневого `menu`, scope профилей,
  terminal contract, пути с пробелами/Unicode/кавычками/literal shell characters.
  Прежняя конфигурация без mount-point default и desktop MIME support оставляет
  MIME route без обработчика; marker обозначает browser fallback без запуска браузера.
- Старые шесть `test_xdg_text.py` также проходят с новым declaration output:
  generated `desktopText` для Neovim не изменился.
- Три mutation controls ожидаемо отвергнуты: старый корневой `menu`,
  `program_options.menu="flat"` и отсутствие Kitty в directory Exec.

Это не запуск настоящих GTK/AppIndicator, Kitty PTY, Yazi, MIME discovery,
YAML generator/parser или storage backend. Menu проверяется на словаре settings
из merged HM через настоящий udiskie reader; реальный YAML-файл не строится.
Устройства, содержимое дисков, mount/unmount/eject, D-Bus storage requests и
polkit dialogs не используются. Полные builds и installed layout не проверены.

## Применение и приёмка

1. Пользователь применяет HM: на Lenovo `home-manager switch --flake .#samov-laptop`;
   Acer — `.#samov-laptop-old`, desktop — `.#samov-desktop`. Lenovo профиль на Acer не применять.
   NixOS rebuild и рестарт FileManager1 не нужны.
2. Только если менялось меню, для его перечитывания выполнить `systemctl --user restart udiskie.service`.
   Для одной новой MIME association рестарт udiskie не нужен.
   Автомонтирование остаётся включённым: не используй для проверки подключённый
   носитель, который не хочешь монтировать, и сначала заверши операции с дисками.
3. `xdg-mime query default inode/directory` и
   `xdg-mime query default inode/mount-point` должны вернуть `yazi-xdg.desktop`.
   Проверить безопасный каталог без USB-устройства:

   ```fish
   set check_dir (mktemp -d /tmp/opencode/yazi-dir-check.XXXXXX)
   mkdir "$check_dir/папка с пробелами"
   xdg-open "$check_dir/папка с пробелами"
   ```

   Ожидается одно окно Kitty с Yazi в этом каталоге, не просто Fish prompt.
4. Когда будет подходящий тестовый носитель, отдельно проверить иерархическое
   меню в tray и его Browse: открывается тот же mount directory в Yazi.
   После завершения записи проверить штатное unmount/power-off и только затем
    отключать носитель. Browse принят пользователем на Lenovo; unmount/eject и
    остальные носители этим не проверены. Не экспериментировать
   с основным диском или единственной копией важных данных.
