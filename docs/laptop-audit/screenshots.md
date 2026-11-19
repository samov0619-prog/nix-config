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

### Курсор при выделении: upstream-fix Slurp

На Lenovo с Hyprland 0.55.4 и масштабом 1.6 пользователь уточнил симптом:
курсор маленький **во время выделения**, после Esc обычный размер возвращается.
Постоянный сброс масштаба после скриншота не воспроизведён. Hyprland и GTK3 видят
логический экран 2000×1250 при физических 3200×2000; PNG в физических пикселях
сам по себе не означает неисправность масштабирования.

Протокольный запуск установленного Slurp 1.5.0 подтвердил: Hyprland рекламирует
`wp_cursor_shape_manager_v1` версии 2, но Slurp его не подключает и устанавливает
собственную cursor surface с buffer scale 2. Без `XCURSOR_THEME` библиотека
Wayland возвращает запасную стрелку 10×16 даже при запросе размера 48; buffer
scale 2 уменьшает её дополнительно. Отдельный запуск с `XCURSOR_THEME=Adwaita`
и обычным размером 24 дал буфер 48×48; пользователь сообщил, что крестик выглядит
нормально. Снимки в этих двух сравнениях не создавались.

Adwaita была только диагностикой: пользователь выбрал **курсор темы Hyprland**,
а не отдельную тему для выделения. Поэтому настройка `XCURSOR_THEME` не добавлена.
Общий HM-модуль использует [Slurp с upstream-backport](../../pkgs/slurp-cursor-shape/README.md)
и для helper, и для ручного запуска `slurp`. Точный upstream commit
[`0465f03a`](https://github.com/emersion/slurp/commit/0465f03a7949da338d90a0788451815a02b6f1d2)
подключает уже реализованный `cursor-shape` и исправляет cleanup. Теперь Slurp
сможет запросить crosshair у Hyprland, а тему и размер определит compositor.
Fallback Xcursor для compositor без протокола остаётся прежним. После исправления
installCheck пользователь подтвердил рабочее поведение; отдельная агентская
проверка темы Rose Pine и размера собранного пакета не выполнялась.

По проверенным upstream tags и рецепту nixpkgs unstable последний релиз — 1.5.0,
без этого исправления. Связка grim/slurp/Swappy приведена в
[wiki Hyprland](https://wiki.hypr.land/Useful-Utilities/Screenshots-and-Recording/).
Hyprshot и Grimblast также вызывают Slurp, поэтому простая замена на них не
устраняет причину. Переход на другой редактор или полный screenshot UI не нужен
для согласованного сценария выделение → Swappy.

Подготовка исправления: локальный patch byte-for-byte совпал с upstream;
четыре source/callback contracts проходят на 1.5.0 с backport и на исходнике
самого upstream-fix. На неизменённом 1.5.0 воспроизводятся три ожидаемых отказа:
нет binding, guard темы и cleanup manager. Семь helper fixtures и selected
merged Nix declarations **только Lenovo** проходят; проверено наличие ровно
одного исправленного Slurp. Это маленький C callback harness с заглушками,
не сборка Slurp и не проверка живого compositor. Nix-файлы обработаны `nix fmt`;
Ruff/Prettier отсутствуют, Python syntax и локальные ссылки документации проверены.

Точечный removal probe корректно различает релиз без исправления и upstream-fix.
Полный inventory-check пока заблокирован посторонними незарегистрированными
`home/modules/kitty/macos/kitty-keybindings-fix.patch`, `kitty-keybindings.patch`
и `kitty-ui.patch`; они не изменялись в этой задаче. Общий checker не объявляется
успешным; его прежние fingerprints не обновлялись.

Первая пользовательская сборка Slurp дошла до installCheck и упала на поиске
`/build/source/build/main.c`: Meson оставляет текущий каталог в `source/build`,
а добавленная проверка ошибочно принимала `$PWD` за корень исходников. Путь
исправлен на `$NIX_BUILD_TOP/$sourceRoot`, сама проверка не отключена. Новый
shell fixture проходит для обычного sourceRoot и имени с пробелами. Реально
вычисленная Nix-фаза также исполнена из временного `source/build` на исправленном
исходнике 1.5.0: четыре contracts проходят, заглушены только `runHook`. Повторная
сборка пакета и проверка живого курсора агентом не запускались.

После повторной попытки пользователь подтвердил: «все ок работает». Это
пользовательская приёмка исправленного сценария на Lenovo, не независимая
проверка полного protocol/UI/save/copy matrix или остальных хостов.

После review и включения новых файлов в Git-backed flake пользователь применяет
`home-manager switch --flake /home/samov/nix-config#samov-laptop`. Только для этой
правки NixOS rebuild, restart сессии и `hyprctl reload` не нужны. Проверить:

1. F10/Print: крестик обычного размера из темы compositor на масштабе 1.6.
2. Esc: Swappy не открывается, обычный курсор восстанавливается.
3. Завершить безопасное выделение: Swappy открывается; ручное сохранение и
   копирование работают как раньше, размер PNG не изменён этой правкой.

### Исходные проверки screenshot helper

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
