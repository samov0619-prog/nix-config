# Съёмные накопители и открытие каталогов

## Согласованные изменения

- `home/linux/gui-set/default.nix`: меню udiskie задано через
  `settings.program_options.menu = "smart"`. Старый корневой `menu="nested"`
  игнорировался; `smart` — актуальное имя поддержанного иерархического режима
  в udiskie 2.6.2 (`nested` остаётся legacy alias).
- `home/linux/gui-set/xdg.nix`: `inode/directory` явно связан с существующим
  `yazi-xdg.desktop`, который запускает `kitty -- yazi %f`, `Terminal=false`.
  Так Browse в udiskie и другие вызовы `xdg-open` для каталога открывают Yazi,
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

## Воспроизводимые проверки

Из корня репозитория, Fish:

```fish
set declarations (mktemp /tmp/opencode/removable-declarations.XXXXXX.json)
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/gui-set/test-xdg-declarations.nix > "$declarations"
set udiskie_package (nix eval --offline --raw .#homeConfigurations.samov-laptop.config.services.udiskie.package.outPath)
python3 -B home/linux/gui-set/test_removable_launch.py --declarations "$declarations" --udiskie-package "$udiskie_package"
```

Пакет udiskie должен уже находиться в store, например после пользовательской
сборки/применения HM; evaluation сама его не строит. Нужны Python и Bash.

- Выбранные merged declarations пяти профилей проверяют явный directory handler,
  `Terminal=false`, поддержанную секцию меню и прежние automount/notify/tray,
  Neovim/Yazi/HTML settings; Mac/server остаются без этих GUI handlers.
- Шесть Python tests используют настоящий generated desktop text из
  `makeDesktopItem/writeTextFile`, AST-extracted installed udiskie `Config`
  и `prompt.browser`, а также извлечённые настоящие функции installed xdg-open.
  Fake Popen перехватывает Browse, fake Kitty/Yazi фиксируют argv и UID/EUID/cwd.
  Проверены menu=`smart`, контроль игнорируемого корневого `menu`, scope профилей,
  terminal contract, пути с пробелами/Unicode/кавычками/literal shell characters.
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

1. Пользователь применяет HM: на Acer `home-manager switch --flake .#samov-laptop`;
   desktop — `.#samov-desktop`. Lenovo draft на Acer не применять.
   NixOS rebuild и рестарт FileManager1 не нужны.
2. Для перечитывания меню выполнить `systemctl --user restart udiskie.service`.
   Автомонтирование остаётся включённым: не используй для проверки подключённый
   носитель, который не хочешь монтировать, и сначала заверши операции с дисками.
3. `xdg-mime query default inode/directory` должен вернуть `yazi-xdg.desktop`.
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
   отключать носитель. Эта живая приёмка пока не выполнена; не экспериментировать
   с основным диском или единственной копией важных данных.
