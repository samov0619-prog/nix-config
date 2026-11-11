# Desktop portals: штатный маршрут Hyprland + GTK

## Найденная конфигурация

На Acer/desktop/Lenovo selected merged NixOS declarations одинаковы:

- `xdg.portal.enable=true`;
- extra portals: `xdg-desktop-portal-hyprland` и `xdg-desktop-portal-gtk`;
- `configPackages=[hyprland]`, без собственного `xdg.portal.config`;
- отдельный wlr backend выключен.

Это штатная композиция NixOS Hyprland module, не отсутствие маршрутизации.
Installed Acer `share/xdg-desktop-portal/hyprland-portals.conf` содержит
`default=hyprland;gtk`: выбирается первый backend, поддерживающий интерфейс.
Hyprland descriptor объявляет Screenshot/ScreenCast/GlobalShortcuts;
GTK descriptor — в частности FileChooser/Settings. `UseIn=gnome` в GTK descriptor
само по себе не исключает его из явно указанной fallback-цепочки.

Read-only status Acer показал portal и оба backend services active/running,
Result=success. Это не функциональная проверка выбора файла/экрана и не доказательство
того, какие environment/config overrides получает каждое клиентское приложение.
Ручные portal overrides, браузерные профили и permissions store не читались.

Никакой подтверждённый дефект этого маршрута не найден. Не добавлены собственный
per-interface config, `GTK_USE_PORTAL`, другой chooser, capture permissions,
новый backend или service restart. Print → slurp → Swappy остаётся отдельной
цепочкой: работа Print не доказывает работу ScreenCast portal.

## Сообщение Polkit-агента

Отдельный подтверждённый дефект Lenovo — Realtime pidns lookup в основном портале
1.20.4, не выбор backend: настоящий pidfd ошибочно обрабатывался как dirfd
`/proc/<pid>`. Пользователь одобрил основной portal 1.22.1 из уже pinned unstable,
где есть upstream PR #1713, без локального backport и обновления lock. Lenovo-only
overlay сохраняет точные stable GTK/Hyprland backends и native routing; для GTK
явно сохраняется также stable build-time dependency на основной portal.
Selected declarations и настоящие функции из upstream с native pidfd/ioctl
проверены, в том числе воспроизведение старого ENOTDIR. Пользователь применил
NixOS и перезагрузился: запущен portal 1.22.1, pidns error не повторился;
у PipeWire/Pulse/WirePlumber/onionbell видны RT data-loop threads с приоритетом 20.
Это native runtime evidence, но не трассировка D-Bus Realtime и не приёмка live
portal UI. См.
[boot-errors.md](../../hosts/laptop/boot-errors.md) для scope, тестов и применения.
Это не исправляет описанную ниже отдельную app-ID регистрацию Qt.

В журнале hyprpolkitagent было:

```text
Failed to register with host portal QDBusError("org.freedesktop.portal.Error.Failed", "Could not register app ID: Connection already associated with an application ID")
```

В [исходнике xdg-desktop-portal 1.20.4](https://github.com/flatpak/xdg-desktop-portal/blob/1.20.4/src/xdp-app-info.c)
этот ответ выдаётся, когда sender уже имеет cached app info при вызове host
registration. Это не сообщение «Polkit agent не зарегистрирован» и не доказательство
отсутствующего backend. Пользовательский password-request scenario прошёл,
но точная причина порядка запросов/смены D-Bus owner и влияние на другие Qt
функции не проверялись. Ошибка не скрыта, кеш не очищался, workaround не добавлен.
Возвращаться к диагностике, если появится воспроизводимый функциональный сбой.

## Проверки и приёмка

Декларации трёх GUI NixOS hosts проверены offline/noIFD без builds. Основные
настройки можно повторно посмотреть из корня репозитория, Fish:

```fish
for host in laptop-old desktop laptop
    nix eval --offline --json --option allow-import-from-derivation false \
        ".#nixosConfigurations.$host.config.xdg.portal" \
        --apply 'p: { inherit (p) enable config; extraPortals = map (v: v.pname or v.name) p.extraPortals; configPackages = map (v: v.pname or v.name) p.configPackages; wlr = p.wlr.enable; }'
end
```

Не вызывались portal methods, file chooser, PipeWire screencast, screen/window
capture, browser automation или permissions changes. Настоящие файлы, desktop
contents, screenshots и записи не читались/не создавались.

На Lenovo в существующем workflow checklist остаётся живая проверка:

1. В привычном приложении открыть диалог выбора файла и отменить его, ничего
   не загружая. Проверить нормальное появление диалога и возврат в приложение.
2. Когда понадобится демонстрация экрана, отдельно проверить выбор одного
   пустого тестового окна и немедленную остановку трансляции. Не показывать
   весь рабочий стол или личные данные ради аудита.

Это пользовательская ручная приёмка, не требование запускать screen share
сейчас. После этой source/status-проверки изменена только документация:
NixOS/HM activation и перезапуск services не нужны.
