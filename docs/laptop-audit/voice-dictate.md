# Диктовка: ошибки распознавания и безопасная передача текста

[Общий модуль](../../home/modules/voice-dictate/default.nix) сохраняет сценарий
`Super+Shift+R`: первое нажатие запускает запись с текущего default input PipeWire,
повторное останавливает её, распознаёт русский текст, копирует и печатает его.
Модель Small Q5_1, язык, нормализация пробелов, задержка перед приглашением говорить
и сочетание клавиш не меняются. Это локальное распознавание, не облачный вызов.

## Две согласованные правки

- Неуспешный pipeline распознавания теперь явно удаляет временный `recording.wav`,
  показывает критическое уведомление `Transcription failed` и завершается с ошибкой.
  Частичный stdout не копируется и не печатается. Раньше Bash strict mode завершал
  скрипт раньше удаления файла/уведомления. `writeShellApplication` в pinned nixpkgs
  включает `pipefail`, поэтому ошибка Whisper не маскируется успешными tr/sed.
- Распознанный текст передаётся через `printf '%s' "$text" | wtype -`, а не в argv.
  По [wtype 0.4 source](https://github.com/atx/wtype/blob/v0.4/main.c) одиночный `-`
  читает stdin, тогда как аргумент с начальным дефисом разбирается как опция.
  Ввод не получает дополнительный LF/Enter; копирование через wl-copy сохраняется.

Это не переработка всего lifecycle: PID-файл, остановка recorder и поведение
параллельных нажатий не меняются. Cleanup здесь относится к завершившемуся
pipeline распознавания, не является гарантией удаления после SIGKILL, сбоя системы
или любой ошибки записи. Отсутствующая речь по-прежнему даёт `No speech recognized`,
пустая запись — `No audio was recorded`.

## Область и проверки

Общий модуль используется Acer, desktop и Lenovo. Selected merged HM evaluation
подтвердила сохранение Acer Vulkan/device 1 и desktop/Lenovo без Vulkan, device 0;
в server/Mac helper не добавлен. Acer GPU index не переносится на Lenovo: выбор
его backend остаётся отдельной живой проверкой.

```fish
python3 -B home/modules/voice-dictate/tests/test_voice_dictate.py
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/modules/voice-dictate/tests/test-declarations.nix
```

Восемь fixtures исполняют production shell body с strict mode: ошибка Whisper,
ошибка с частичным выводом, начальный дефис, Unicode/кавычки/shell characters,
прежняя нормализация, пустой текст, пустая запись и прежние параметры распознавания.
Whisper, clipboard, wtype, notifications и recorder подставные; `kill` заменён
shell-функцией без реальных сигналов. Три целевые проверки ожидаемо отклоняют
старый код. Проверяется stop/transcription branch, не настоящий recorder lifecycle,
Vulkan/CPU, Nix-built wrapper, Bluetooth, clipboard или ввод в целевое приложение.
Агент не включал микрофон, не читал реальные записи/буфер, не запускал сборки.

## Применение и ручная приёмка

1. После ревью на Acer: `home-manager switch --flake .#samov-laptop-old`.
   На desktop использовать свой `.#samov-desktop`; Lenovo draft на Acer не применять.
   NixOS rebuild, service restart и Hyprland reload для этой правки не нужны.
2. В безопасном тестовом текстовом поле выполнить обычную диктовку двумя нажатиями
   Super+Shift+R, начиная говорить после уведомления. Проверить текст без лишнего
   Enter, уведомление об успехе и обычную вставку из буфера.
3. После завершения убедиться, что `$XDG_RUNTIME_DIR/voice-dictate/recording.wav`
   отсутствует, не открывая содержимое. Ошибку Whisper безопасно проверяют fixtures;
   ради неё не ломать рабочую модель или GPU. Lenovo повторяет живую приёмку после
   установки и выбора backend.
