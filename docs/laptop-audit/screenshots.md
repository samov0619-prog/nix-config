# Скриншоты и буфер обмена

## Согласованный сценарий

На Acer, desktop и Lenovo **Print → выделить область → Swappy**. Сохранение
в `~/Screenshots` и копирование выполняются вручную: `Ctrl+s` и `Ctrl+c`
в Swappy. Автосохранение, новые хоткеи и clipboard manager не добавляются.
Существующий Print теперь указан в справке F1.

Общий [Hyprland module](../../home/linux/modules/hyprland/default.nix) устанавливает
`hypr-screenshot-region` через `writeShellApplication` с явными runtime inputs
`grim`, `slurp`, `swappy`. Helper сначала получает непустой успешный выбор и только
потом запускает прежний pipeline `grim -g "$geometry" - | swappy -f -`.
При отмене, ошибке `slurp` или пустом выборе capture/editor не запускаются.
Ошибки захвата после успешного выбора по-прежнему обрабатывают сами grim/Swappy;
это не новая система обработки всех ошибок screenshot tools.

Раньше команда в трёх raw Hyprland configs игнорировала статус `slurp` внутри
`$(...)`: Esc всё равно запускал grim с пустой геометрией и Swappy. Подставные
инструменты подтвердили вызовы; исходник grim 1.5.0 отвергает неверную геометрию.
Это лишний запуск с ошибкой, **не доказательство захвата всего экрана**.

## Сохранение и clipboard

- Shared module сохраняет `swappy/config` только с `save_dir` и создаёт
  `Screenshots/.keep`. `auto_save` и `early_exit` не включаются. По
  [Swappy 1.8.0 README](https://github.com/jtheoof/swappy/blob/v1.8.0/README.md)
  Ctrl+s сохраняет, Ctrl+c копирует, Esc/q закрывают редактор. Выход без сохранения
  не обещает backup снимка.
- `wl-clipboard` остаётся в GUI package list. Swappy документирует использование
  `wl-copy`, чтобы копия могла пережить закрытие редактора; наличие пакета — ещё
  не проверка настоящего Wayland clipboard на каждом хосте.
- В просмотренных активных Nix-декларациях `home/` и `hosts/` не обнаружены
  `cliphist`, `copyq`, `greenclip`, `clipman` или запуск `wl-paste` watcher.
  Это не инвентаризация установленных вручную программ/процессов и не гарантия
  отсутствия истории в приложениях. Сам буфер и его содержимое не читались.
- Отдельная диктовка явно записывает распознанный текст через `wl-copy` и печатает
  через `wtype`; её поведение здесь не меняется. Tofi passmenu по-прежнему печатает
  пароль через stdin, без копирования в буфер.
- F12 **внутри workspace canvas** — отдельный существующий screenshot path в
  `pkgs/hypr-spaces/src/main.cpp`; он сохраняет canvas напрямую и не менялся.

## Проверки и применение

```fish
python3 -B home/linux/modules/hyprland/tests/test_screenshot.py
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/modules/hyprland/tests/test-screenshot.nix
```

Семь fixtures исполняют production shell body с Bash strict mode и подставными
slurp/grim/Swappy: cancel, failure с непустым stdout, пустой успешный выбор,
поток синтетических байтов, отрицательные координаты без final LF, literal quoting,
три бинда и F1. Child PATH содержит только mocks, без session/display variables.
Selected merged declarations проверяют helper только на трёх GUI-профилях,
сохранение прежнего Swappy config и пакетов; Mac/server остаются без helper.
Также повторно прошли пять тестов passmenu. Это не проверка собранного wrapper,
настоящего PNG/Wayland/GTK, установленного layout или физической клавиши Lenovo.
Сборки и activation агентом не выполнялись.

1. После ревью применить свой профиль: на Acer
   `home-manager switch --flake .#samov-laptop-old`, на desktop — `.#samov-desktop`.
   Lenovo draft на Acer не применять. NixOS rebuild не нужен.
2. Выполнить `hyprctl reload`. Нажать Print, затем Esc: Swappy не должен открыться.
3. Снова Print, выделить безопасную тестовую область: Swappy должен открыться.
   Проверить Ctrl+s и файл в `~/Screenshots`; затем Ctrl+c, закрыть редактор и
   вставить снимок в выбранное приложение. Содержимое агенту передавать не нужно.
4. Проверить наличие Print в F1. На Lenovo повторить после установки и проверки
   фактической клавиатуры.
