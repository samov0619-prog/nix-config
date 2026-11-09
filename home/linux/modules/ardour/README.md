# Ardour: системная тема при запуске

Общий Linux GUI-модуль для Acer, desktop и Lenovo; server/Mac не затрагиваются.
Исходный `pkgs.ardour` не патчится и не пересобирается: `symlinkJoin` заменяет
только launcher и desktop entry. Обычная команда `ardour9`, меню приложений и
`X-NSM-Exec` используют одну обёртку. Аргументы, exit status и upstream launcher
(включая окружение аудио/видео) сохраняются. Major version берётся из пакета.

Перед запуском обёртка читает dconf
`/org/gnome/desktop/interface/color-scheme` — тот же режим, который меняет F11:

- `prefer-dark` → встроенная тема `dark`;
- `prefer-light`, `default`, unset → встроенная `captain_light` (как светлая
  ветка общего Qt helper для default/unset).

Это **не** GTK/Qt theme inheritance: палитра Ardour собственная. Используются
настоящие темы из Ardour 9.7. При обновлении major проверить их наличие и формат
`ui_config` по upstream `gtk2_ardour/ui_config.cc` / `ui_config_vars.inc.h`.

Меняется только `UI/Option[@name='color-file']` в существующем
`$XDG_CONFIG_HOME/ardour<major>/ui_config` (по умолчанию `~/.config`). Остальные
XML-настройки и комментарии сохраняются; XML serializer может поменять оформление.
Первый оригинал сохраняется побайтно в `ui_config.before-system-theme`, без
перезаписи при следующих переключениях. Файл остаётся mutable и принадлежит
пользователю; HM не управляет его содержимым через `xdg.configFile` или activation.
При совпадающей теме запись не выполняется; при изменении сохраняются file mode
и остальные параметры, запись атомарная. Symlink, повреждённый/неоднозначный XML,
неизвестный режим и ошибки чтения приводят к пропуску смены темы, не отказу запуска.

## Границы

- Только **при следующем открытии**: F11 больше не пишет в Ardour-конфиг.
  Нет Lua-hook, службы, опроса в фоне или автоматического перезапуска DAW.
- Lock удерживается через exec; второй запуск не меняет настройки. Дополнительно
  проверяется уже работающий upstream Ardour того же пользователя через `/proc`
  (включая обход обёртки); недоступный `exe` проверяется по Linux command name.
  Если идентичность процесса нельзя прочитать, смена темы пропускается.
- Отсутствующий `ui_config` не создаётся: первый запуск и перенос старых настроек
  выполняет сам Ardour. После его штатного закрытия работает следующий запуск.
- Пользовательские палитры `my-*.colors` не удаляются и могут влиять на выбранную
  базовую тему по обычным правилам Ardour. Прямой запуск binary из Nix store
  обходит обёртку. Параллельный прямой запуск вне неё не синхронизирован lock-ом.

## Проверки и применение

```fish
python3 -B home/linux/modules/ardour/test_launch.py
python3 -B home/linux/modules/qt-theme/test_apply.py
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/modules/ardour/test-declarations.nix
```

15 изолированных тестов выполняют реальный Python helper и Nix-generated launcher
с подменой desktop reader/DAW на fixtures: light/dark, аргументы/exit/exec lock,
сохранность настроек/backup/mode, пропущенный default option, отсутствие первого
конфига, malformed XML, symlink, неизвестный режим, второй запуск, process guard
и отсутствие записи F11 в обе версии Ardour. Process guard проверен на synthetic
`/proc`, не на реальном запущенном Ardour. Отдельно проходят 11 общих Qt/F11 тестов.
Выборочная merged evaluation проверяет wrapper ровно в трёх GUI-профилях,
исключение server/Mac и сохранение Audacious/pwvucontrol.

После `bbe8075` пользователь проверил сценарий на Acer и подтвердил «все работает».
Это пользовательская live-проверка, не независимая проверка всех вариантов запуска
или desktop/Lenovo. Агент полную HM-сборку не запускал, личные настройки не читал
и Ardour не открывал.

1. После review собрать только нужный HM output, например на Acer:
   `nix build .#homeConfigurations.samov-laptop.activationPackage`.
2. Применить `home-manager switch --flake .#samov-laptop` (на desktop — свой
   профиль). Lenovo draft на Acer не применять. NixOS rebuild не нужен.
3. Полностью закрыть Ardour, выбрать светлый режим через F11, открыть из меню:
   ожидается светлая палитра. Закрыть, выбрать тёмный, запустить `ardour9`:
   ожидается тёмная. При уже открытом Ardour F11 не должен менять его тему.
