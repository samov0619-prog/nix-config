# Медиаклавиши: playerctl и MPV MPRIS

## Изменение

Общий Linux GUI HM set устанавливает `playerctl` и подключает
`programs.mpv.scripts = [ pkgs.mpvScripts.mpris ]`. Область — Acer/desktop/Lenovo,
не Mac/server. Уже существующие Play/Pause/Next/Prev bindings больше не зависят
от отсутствующей команды. Плагин предоставляет MPV стандартный интерфейс MPRIS.

Громкость и mute по-прежнему используют wpctl; это отдельная цепочка.
Бинды, MIME defaults и личные настройки проигрывателей не меняются.
Новые службы, playerctld и маршрутизация по активному окну не добавлены.

MPRIS работает независимо от workspace: например, Chrome обычно позволяет
поставить YouTube на паузу из другого окна. Но при нескольких плеерах обычный
playerctl не гарантирует выбор нужного приложения. Возможности next/previous
зависят от самого плеера и текущего медиа; не каждый поток поддерживает переход.
Без доступного MPRIS-плеера команда может сообщить `No players found`.

## Проверки без воспроизведения

Из корня репозитория, без builds/IFD:

```fish
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/gui-set/test-media-declarations.nix
```

Selected merged declarations проверяют наличие playerctl, единственный MPV MPRIS
plugin, путь `--script=…/mpris.so` в настоящем рецепте wrapper и установку именно
этого MPV package. Также проверяются прежние Audacious/pwvucontrol, отсутствие
playerctld и явных audio/video defaults, отсутствие добавлений на Mac/server.

Единый запуск пяти профилей превысил лимит 25 секунд. Проверки затем прошли
двумя отдельными evaluation — три GUI profiles и Mac/server:

```fish
nix eval --impure --offline --json --option allow-import-from-derivation false --expr 'let c = import ./home/linux/gui-set/test-media-declarations.nix; in { desktop = c.samov-desktop; laptop = c.samov-laptop; lenovo = c.samov-laptop-next; }'
nix eval --impure --offline --json --option allow-import-from-derivation false --expr 'let c = import ./home/linux/gui-set/test-media-declarations.nix; in { mac = c.samov-mac; server = c.samov-server; }'
```

Механически сверены восемь audio bindings каждого GUI host, включая прежний
volume-up 5% с пределом 100%. Физические клавиши/remap/repeat/lock state,
построенный wrapper, установленный layout, D-Bus и MPRIS реальных Chrome,
Audacious/MPV не проверены. Агент не запускал media/volume commands,
не читал metadata, playlists/history и не воспроизводил звук/видео.

## Применение и живая приёмка

1. Пользователь применяет HM: Acer — `home-manager switch --flake .#samov-laptop`,
   desktop — `home-manager switch --flake .#samov-desktop`.
   Lenovo draft на Acer не применять. NixOS rebuild/новые службы не нужны.
2. Проверить `command -v playerctl`; закрыть и заново открыть MPV, если он работал
   до switch: старый процесс не получит плагин автоматически.
3. Оставить один доступный плеер, например YouTube в Chrome, начать воспроизведение
   вручную. Перейти на другой workspace и нажать медиаклавишу Play/Pause:
   ожидается пауза/возобновление без переключения окна. Это проверка настоящего
   браузерного MPRIS и клавиши, не гарантия работы каждого сайта/браузера.
4. Отдельно повторить с MPV и подходящим тестовым файлом, затем при необходимости
   с Audacious. Не оценивать выбор между несколькими плеерами как focus-aware:
   такая policy не реализована. Громкость проверить отдельно на безопасном уровне.
