# F11: тема обычных GTK3-приложений

[Решения](feedback.md) · [Qt appearance](../../home/linux/modules/qt-theme/README.md)

Bluetooth и Blueman сохраняются на Acer и Lenovo. Blueman 2.4.6 — обычное
GTK3-приложение, без собственной палитры как у Ardour.

## Причина и исправление

При read-only диагностике на Acer системный `color-scheme` был `prefer-dark`,
а Settings portal отдавал `gtk-theme = Adwaita` (светлая тема). Оба portal services
уже работали, `GTK_THEME` не был задан. Старый F11 менял только `color-scheme`;
для обычного GTK3 этого недостаточно.

Первый фикс (`b27e2e6`) добавил запись `gtk-theme`, но пользователь сообщил, что
это не помогло. Повторная диагностика подтвердила: установлен новый скрипт,
dconf/portal и реальный GTK3 получают `Adwaita-dark`, однако файла темы с этим
именем нет в runtime search paths. GTK3 молча загружает светлый fallback.
Встроенная тёмная палитра `Adwaita` с variant `dark` — не то же самое, что отдельное
имя темы `Adwaita-dark`. Проверки одних ключей dconf этого не обнаруживали.

Общий [toggle-theme.sh](../../home/linux/modules/hyprland/scripts/toggle-theme.sh)
теперь также записывает dconf `/org/gnome/desktop/interface/gtk-theme`:

| Следующий режим F11 | GTK3           | Qt5/Qt6        |
| ------------------ | -------------- | -------------- |
| Light              | `Adwaita`      | `Adwaita`      |
| Dark               | `Adwaita-dark` | `Adwaita-Dark` |

Имена GTK и Qt различаются регистром. Неопределённый/неизвестный исходный режим
по-прежнему переключается в dark. GTK3 Wayland backend получает имя темы через
GSettings/Settings portal и уведомления об изменениях; отдельная обёртка Blueman,
служба, polling или `GTK_THEME` override не нужны. Linux GUI set теперь устанавливает
штатный `pkgs.gnome-themes-extra`: его GTK3 `Adwaita-dark/gtk.css` импортирует
`resource:///org/gtk/libgtk/theme/Adwaita/gtk-contained-dark.css`. Собственная тема
не разрабатывается; это upstream alias на встроенную тёмную палитру. Настройки шрифтов,
значков, Bluetooth-адаптера и сопряжений не меняются. Activation не пишет dconf:
согласование произойдёт при следующем F11.

Это общая политика для обычных GTK3-приложений, не обещание для GTK2, приложений
с собственной CSS/палитрой, sandbox или принудительным `GTK_THEME`. XWayland и
такие исключения отдельно не проверены. Современные приложения, следующие
`color-scheme`, сохраняют прежний механизм; Qt helper, Alacritty и startup Ardour
не меняют своего поведения.

## Проверки и применение

```fish
python3 -B home/linux/modules/qt-theme/test_apply.py
python3 -B home/linux/modules/ardour/test_launch.py
python3 -B home/linux/modules/qt-theme/test_native_gtk.py
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/modules/qt-theme/test-declarations.nix
```

Пройдены 12 appearance/F11 тестов и 15 Ardour regression tests. В пяти fixture
сценариях настоящий F11 проверяет точные dconf writes, обе Qt-версии и сохранение
current_theme. Отдельный тест выполняет настоящий dconf и Qt helper на private
D-Bus с временным HOME/config: light/dark/default и сохранность стороннего ключа
шрифта. Он пропускается, если dconf/dbus-run-session не установлены; на Acer
выполнен, не пропущен. Это не проверка portal notification или реального GTK UI.
Личный dconf, Blueman UI и Bluetooth-подключения в тестах не менялись. Полные
сборки, activation и проверку живого окна агент не запускал.

После сообщения пользователя добавлен `test_native_gtk.py`: уже установленный
GTK3/Python runtime Blueman, изолированные settings, невидимый Gtk.Window и точная
копия upstream alias в fixture. Без alias GTK разрешает фон в `246,245,244`, с ним —
в `53,53,53`; встроенный dark variant даёт тот же тёмный цвет. В одном процессе
смена GTK settings light → dark → light возвращает обе палитры правильно.
Это реальные CSS-resolved colors GTK, не mock, но **не** проверка установленного
пакета gnome-themes-extra, отрисованного окна Blueman или portal events. В store
этого пакета при проверке не было; агент его не скачивал/не собирал. Выборочная
merged evaluation проверяет объявление пакета только в трёх Linux GUI-профилях,
сохраняя server/Mac и остальные Qt/nomacs declarations.

1. После review при необходимости собрать только свой HM output:
   `nix build .#homeConfigurations.samov-laptop.activationPackage`.
2. Полностью закрыть Blueman и другие проверяемые GTK3-приложения, затем применить
   `home-manager switch --flake .#samov-laptop` (на desktop — свой
   профиль; Lenovo draft на Acer не применять). NixOS rebuild не нужен.
   Для этой первой установки перезапуск приложения нужен: GTK мог закешировать
   светлый fallback под именем ещё не установленной тёмной темы.
3. Открыть Blueman и нажать F11 в обе стороны. Ожидается смена светлой/тёмной темы
   открытого окна, без переподключения устройств. Перезапуск сессии из-за этой
   правки не требуется. Если окно не обновляется, проверить также закрытие/открытие
   Blueman и read-only portal `gtk-theme`; не менять сопряжения ради темы.
