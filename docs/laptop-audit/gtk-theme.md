# F11: тема обычных GTK3-приложений

[Решения](feedback.md) · [Qt appearance](../../home/linux/modules/qt-theme/README.md)

Bluetooth и Blueman сохраняются на Acer и Lenovo. Blueman 2.4.6 — обычное
GTK3-приложение, без собственной палитры как у Ardour.

## Причина и исправление

При read-only диагностике на Acer системный `color-scheme` был `prefer-dark`,
а Settings portal отдавал `gtk-theme = Adwaita` (светлая тема). Оба portal services
уже работали, `GTK_THEME` не был задан. Старый F11 менял только `color-scheme`;
для обычного GTK3 этого недостаточно.

Общий [toggle-theme.sh](../../home/linux/modules/hyprland/scripts/toggle-theme.sh)
теперь также записывает dconf `/org/gnome/desktop/interface/gtk-theme`:

| Следующий режим F11 | GTK3           | Qt5/Qt6        |
| ------------------ | -------------- | -------------- |
| Light              | `Adwaita`      | `Adwaita`      |
| Dark               | `Adwaita-dark` | `Adwaita-Dark` |

Имена GTK и Qt различаются регистром. Неопределённый/неизвестный исходный режим
по-прежнему переключается в dark. GTK3 Wayland backend получает имя темы через
GSettings/Settings portal и уведомления об изменениях; отдельная обёртка Blueman,
служба, polling, новый пакет или `GTK_THEME` override не нужны. Настройки шрифтов,
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
```

Пройдены 12 appearance/F11 тестов и 15 Ardour regression tests. В пяти fixture
сценариях настоящий F11 проверяет точные dconf writes, обе Qt-версии и сохранение
current_theme. Отдельный тест выполняет настоящий dconf и Qt helper на private
D-Bus с временным HOME/config: light/dark/default и сохранность стороннего ключа
шрифта. Он пропускается, если dconf/dbus-run-session не установлены; на Acer
выполнен, не пропущен. Это не проверка portal notification или реального GTK UI.
Личный dconf, Blueman UI и Bluetooth-подключения в тестах не менялись. Полные
сборки, activation и проверку живого окна агент не запускал.

1. После review при необходимости собрать только свой HM output:
   `nix build .#homeConfigurations.samov-laptop.activationPackage`.
2. Применить `home-manager switch --flake .#samov-laptop` (на desktop — свой
   профиль; Lenovo draft на Acer не применять). NixOS rebuild не нужен.
3. Открыть Blueman и нажать F11 в обе стороны. Ожидается смена светлой/тёмной темы
   открытого окна, без переподключения устройств. Перезапуск сессии из-за этой
   правки не требуется. Если окно не обновляется, проверить также закрытие/открытие
   Blueman и read-only portal `gtk-theme`; не менять сопряжения ради темы.
