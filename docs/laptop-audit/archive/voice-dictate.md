# Архив Lenovo: Whisper и первоначальная проба Handy

С 15.11.2026 основной вариант Lenovo — [Handy Q4](../../../home/linux/laptop/handy/README.md).
Этот документ сохраняет историю Whisper, аудиополитики и первоначальной пробы,
а не актуальную инструкцию включения Whisper на Lenovo. Архивные Lenovo declarations:
[`whisper.nix`](../../../home/linux/laptop/archive/whisper.nix), не подключены.
Общий Whisper-модуль и его regression fixtures остаются активны для Acer/desktop.
Не удалять их как «неиспользуемые» по состоянию Lenovo.

Исходная приёмка ниже относится к прежнему этапу. Актуальные отмена и уведомления —
в [notification lifecycle](../../../home/linux/modules/notifications/README.md).
Настройки входа/выхода Lenovo и быстрый старт добавлены 15.11.2026, см. последний раздел.

[Общий модуль](../../../home/modules/voice-dictate/default.nix) сохраняет сценарий
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

Общий модуль используется Acer, desktop и Lenovo. На исходном этапе selected
merged HM evaluation подтвердила Acer Vulkan/device 1 и desktop/Lenovo без Vulkan,
device 0; в server/Mac helper не добавлен. Последующая настройка Intel Vulkan на
Lenovo описана в последнем разделе; Acer GPU index на него не переносится.

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

## 15.11.2026: Lenovo — встроенный микрофон и быстрый старт

Пользователь выбрал обычный сценарий: Bluetooth-наушники для воспроизведения,
встроенный микрофон Lenovo для записи; без наушников вывод идёт на динамики.
Bluetooth-микрофон остаётся для ручного выбора в `pwvucontrol`.

### Декларативная аудиополитика

`hosts/laptop/audio.nix` использует штатный
`services.pipewire.wireplumber.extraConfig`, без Lua, watchers или login hooks:

- встроенный Digital Microphone (`HiFi__Mic1__source`) получает `priority.session=2500`;
- output priority overrides отсутствуют: штатные наблюдавшиеся значения —
  динамики 1000, Bluetooth 1010; автоматический выбор выполняет WirePlumber;
- `bluetooth.autoswitch-to-headset-profile=false`: захват не должен сам переводить
  наушники из A2DP/aptX в HFP. Роли, список кодеков, Bluetooth PM и драйверы не меняются.

Это автоматические предпочтения, **не запрет ручного выбора**. Сохранённый default
из GUI/`wpctl set-default` имеет приоритет над `priority.session`. Перед правкой
`wpctl status` не показывал сохранённых Default Configured Devices. Если позже
пользователь выберет другой default, он не сбрасывается скриптом или при входе.
Конкретный A2DP-кодек по-прежнему согласуется с устройством; aptX не форсируется
для несовместимых гарнитур. Для Bluetooth-микрофона надо вручную выбрать HFP-профиль
и источник, затем самостоятельно вернуть A2DP/aptX. Автовозврат ручного HFP не добавлен.

Backport PipeWire X11 teardown и его removal contract сохранены. Остальные хосты
не получают эту аудиополитику. Input-правило матчится по наблюдавшемуся имени
Lenovo, а не универсальному имени для переноса на другое оборудование.

Первоначальная правка ошибочно подняла динамики до 1200, а Bluetooth-правило
с дополнительным условием `media.class=Audio/Sink` не применилось: наушники
остались на 1010. В установленном WirePlumber 0.5.14 `monitors/bluez.lua`
применяет правила до создания `LocalNode`; PipeWire 1.6.6 `emit_node` передаёт
свойства без `media.class`. Поэтому условие не совпадает, хотя созданный node
позднее виден как `Audio/Sink`. Оба output-правила удалены вместо усложнения policy.
На момент диагностики сохранённого output default не было; browser playback
stream в snapshot отсутствовал, поэтому привязка браузера не доказана.

`pwvucontrol` позволяет выбирать default input/output, профиль и устройство
отдельного активного playback stream. Для этого не нужно закрывать браузер.
В live settings `linking.follow-default-target=true`; обычные потоки должны
следовать default, но явный stream target может потребовать перемещения через GUI.
Выбор динамиков как сохранённого default может перекрыть последующее автоматическое
предпочтение Bluetooth; для проверки stock policy не закреплять динамики вручную.

### Вместо безусловных двух секунд

Только HM Lenovo включает `voiceDictate.fastLocalInput`. `input-ready.py` читает
штатный JSON `pw-dump`: если фактический default — локальный ALSA `Audio/Source`,
`pw-record` получает его `object.serial` как `--target`. `node.dont-fallback` и
`node.dont-reconnect` не дают автоматически уйти на другой источник, если выбранный
исчезнет; ручное перемещение потока не запрещено.

У `pw-record` нет отдельного CLI readiness-fd. Поэтому небольшой bounded helper
ждёт первый полный mono s16 PCM-кадр после WAV `data` header, не анализируя звук
и не считая тишину ошибкой. Проверка длится максимум 2 секунды, с шагом 10 мс,
только при старте активной записи; фонового опроса или постоянного демона нет.
Header без PCM не означает готовность. При timeout recorder останавливается,
WAV удаляется и показывается ошибка, а не преждевременное приглашение говорить.

Bluetooth, неизвестный источник/ошибка определения и прежние Acer/desktop
сохраняют консервативную двухсекундную паузу. Смена Whisper/модели/GPU и ускорение
загрузки распознавателя не входят в эту правку.

### Проверки и границы

- 40 small unit/fixture tests проверяют выбор JSON-источника, WAV header/PCM/тишину,
  startup timeout, pinning, fallback на старую паузу, hotkey во время ожидания,
  отмену записи/распознавания и очистку. Это не Bluetooth/UI-приёмка.
- Selected Nix evaluations проверяют native defaults только Lenovo, неизменность
  пакетов/патчей PipeWire и включение fast path только в HM Lenovo. Старый audio
  fixture ожидал выключенный UPower и сначала упал; expectation исправлен по
   согласованной [battery policy](../battery.md), сама power policy не менялась.
- Два коротких live-захвата встроенного микрофона с установленным `pw-record` и
  production Python helper получили PCM через **151.4 мс и 96.7 мс** от запуска
  recorder. Это не полная задержка горячей клавиши/уведомления и не проверка
  сохранности первого слога. После SIGINT `pw-record` вернул 1; исходник 1.6.6
  выдаёт success только при drained completion, так что эти прерванные probes
  не объявляются успешным естественным завершением recorder. WAV удалены;
  прослушивания, распознавания или чтения speech samples не было.
- После применения NixOS + HM пользователь подтвердил: ожидание исчезло, в том
  числе с подключёнными наушниками; первый слог сохранён, скорость транскрипции
  прежняя. Это приёмка старта записи, не исправности output routing.
- В последующем snapshot EDIFIER W800BT Plus присутствовали как A2DP/aptX output,
  но default оставался на динамиках (1200 против 1010). После удаления output
  overrides пользователь подтвердил переключение на наушники при подключении и
  на динамики при отключении, встроенный input и сохранность первых слогов.
  Read-only snapshot подтвердил default Bluetooth output, встроенный input и
  `api.bluez5.codec=aptx`, профиль `a2dp-sink`, состояние `running`.
  A2DP → HFP → A2DP не проверяли. Агент не переключал устройства и не перезапускал
  WirePlumber. Скорость CPU-транскрипции осталась неудовлетворительной.

### Применение на Lenovo

1. Review новых файлов и изменений. Пользователь уже добавил Python helper и его
   тест в index; не снимать staging. Git flake не включает untracked файлы.
2. Для исправления output достаточно NixOS:
   `sudo nixos-rebuild switch --flake .#laptop`. HM с fast-input уже применён;
   для будущих изменений HM — `home-manager switch --flake .#samov-laptop`.
   Не применять на Acer.
3. Перезапустить policy: `systemctl --user restart wireplumber` (кратко прервёт звук).
   Reboot, Hyprland reload и перезапуск VPN не нужны.
4. Проверить `wpctl settings bluetooth.autoswitch-to-headset-profile` → `false` и
   `wpctl status -n`: встроенный input, динамики без гарнитуры; с подключёнными
   наушниками — Bluetooth output, встроенный input. Сохранённый ручной выбор
   может перекрыть автоматические приоритеты.
5. Не закрывая браузер, включить видео и проверить звук: наушники при подключении,
   динамики после отключения, затем наушники после повторного подключения.
   Если default меняется, но поток остаётся на прежнем выходе, проверить его target
   на вкладке playback в `pwvucontrol`, не добавлять новые priority overrides.
    Отмена записи/распознавания ЛКМ и ручной HFP остаются отдельными UI-проверками.

## 15.11.2026: Intel Vulkan — подготовлено, ускорение ещё не измерено

Следующим шагом пользователь выбрал Intel iGPU вместо постоянного сервиса:
задержка заметно растёт с длиной записи. Это основание проверить вычислительный
backend, не доказательство доли загрузки модели или характера роста времени.

Используется уже имеющийся штатный `whisper-cpp.override { vulkanSupport = true;
withSDL = false; }` из stable nixpkgs (whisper.cpp 1.8.4). Только HM Lenovo включает
Vulkan/device 0. Small Q5_1, язык `ru`, параметры декодирования, быстрый старт
микрофона, отмена и очистка не меняются. Сервис и новые драйверы не добавляются.

Одного `-dev 0` недостаточно для изоляции NVIDIA: Whisper загружает backend-ы и
обнаруживает устройства до применения выбора GPU. Поэтому новый nullable option
`voiceDictate.vulkan.driverFile` задаёт штатный Vulkan Loader `VK_DRIVER_FILES`
**только в окружении процесса `whisper-cli`**, не глобально в HM/session и не для
recorder/clipboard. На Lenovo он указывает на установленный системный Intel ANV:
`/run/opengl-driver/share/vulkan/icd.d/intel_icd.x86_64.json`.
При `null` прежние хосты сохраняют обычное обнаружение драйверов; Acer остаётся
на своём device 1, desktop — на CPU. Если Intel-драйвер станет недоступен, не
считать завершившуюся транскрипцию доказательством GPU: backend/fallback надо
проверять по диагностическому выводу Whisper, без `-np`.

### Выполненные проверки

- Установленный `vulkaninfo --summary` с Intel-only `VK_DRIVER_FILES` увидел один
  GPU: **Intel(R) Graphics (PTL)**, vendor `0x8086`, device `0xb0a0`, integrated GPU,
  Mesa **26.1.8**, Vulkan **1.4.354**. NVIDIA `power/runtime_status` до и после
  этого probe оставался `suspended`; непрерывного мониторинга не было.
- 42 unit/fixture tests проходят: к прежним 40 добавлены исполнение GPU-команды
  с process-scoped ICD (включая quoting пути) и отсутствие ограничения драйверов
  у прочих Vulkan-хостов. Это fake Whisper, не GPU inference.
- Selected HM evaluation проверяет настройки и настоящий сгенерированный shell:
  Intel-only prefix/device 0 только у Lenovo, прежний Acer device 1 и desktop CPU.
  Эти проверки не собирают пакет и не подтверждают ускорение/качество распознавания.

### Применение и следующий замер

1. После review собрать HM Lenovo:
   `nix build .#homeConfigurations.samov-laptop.activationPackage`.
   Builds агент не запускал; Vulkan-вариант Whisper может потребовать сборки.
2. Применить `home-manager switch --flake .#samov-laptop`. Для этой правки не нужны
   NixOS rebuild, WirePlumber restart, Hyprland reload или перезапуск OpenCode.
3. В безопасном текстовом поле проверить короткую и длинную диктовку, первые слоги
   и отмену. Первый GPU-запуск может дополнительно тратить время на shader cache;
   по одному первому запуску не оценивать steady-state скорость.
4. После отдельного согласования нагрузки сравнить CPU (`-ng`) и Intel (`-dev 0`)
   одним Vulkan-enabled CLI, с тем же Intel-only окружением, моделью, параметрами и
   одними и теми же двумя WAV. В диагностическом запуске убрать только `-np`,
   сохранить `-nt`: проверить Intel/Vulkan backend, wall time, load/encode/decode
   timings и качество текста. Ничего не вставлять автоматически, личные записи
   и тексты не помещать в Git. Эти A/B-запуски пока не выполнены.
5. К постоянному сервису вернуться, только если загрузка модели окажется значимой
   частью оставшейся задержки. Прирост скорости Intel пока не обещан.

### Последующая пользовательская приёмка

После применения пользователь сообщил об ускорении примерно в **2–3 раза**, но
оставшаяся задержка всё ещё неудовлетворительна. Также сообщил о примерно 10%
CPU для записи длиной 40 секунд; способ усреднения и время распознавания не
зафиксированы. Это не controlled A/B и не основание прогнозировать CPU% других
движков. Один и тот же WAV на CPU/Intel с таймингами пока не сравнивали.

## Handy: Parakeet TDT v3 Q4 — isolated Lenovo trial

Пользователь выбрал пробу `pkgsUnstable.handy` с Parakeet TDT v3 Q4, затем при
неудовлетворительном результате — сравнение Q8, после него при необходимости
потоковый вариант. Q8 обычно интересен ради точности; он больше и не гарантирует
ускорения относительно Q4. Этот этап **не заменяет** рабочий Whisper helper.

Только HM Lenovo добавляет Handy (0.9.8 в текущем lock) и штатный Wayland input
tool `wtype`. Новых NixOS settings, групп `input`, прав `/dev/uinput`, services,
autostart и постоянных hotkeys нет. Настройки Handy остаются пользовательскими,
не HM-managed. Подключать upstream NixOS module для этой пробы не требуется.

Каталог Handy предлагает Q8_0 по умолчанию, а не выбранный Q4. Поэтому штатный
`xdg.dataFile` устанавливает symlink на закреплённый upstream GGUF в
`$XDG_DATA_HOME/com.pais.handy/models/parakeet-tdt-0.6b-v3-Q4_K_M.gguf`.
Файл **485 425 504 байта**, revision и SHA-256 взяты из bundled catalog Handy
0.9.8. Его native local-model discovery принимает symlinks и сопоставляет
альтернативное квантование с каталогом; патч/конвертация модели не нужны.
Существующий файл не перезаписывается принудительно. Модель скачает Nix при
пользовательской сборке/применении; агент веса не скачивал и Handy не запускал.
Модель HM-managed: не удалять/заменять этот файл через Handy; дальнейшую смену
квантования следует согласовать в Nix-конфигурации.

### Проба и возврат

1. После review собрать HM Lenovo:
   `nix build .#homeConfigurations.samov-laptop.activationPackage`.
   Handy из unstable может потребовать сборки; сама модель — ещё около 485 MB
   скачивания, не размер всей closure.
2. Применить `home-manager switch --flake .#samov-laptop`. NixOS rebuild,
   WirePlumber restart и reboot для этих declarations не нужны.
3. Первый запуск выполнить из терминала с process-scoped Intel-only ICD:

   ```fish
   env VK_DRIVER_FILES=/run/opengl-driver/share/vulkan/icd.d/intel_icd.x86_64.json handy
   ```

   Не запускать пробу через обычный launcher/autostart: этот package сам по себе
   не ограничивает Vulkan discovery Intel-драйвером. Уже запущенный без этого
   окружения экземпляр сначала закрыть через Quit; второй запуск single-instance
   приложения не меняет окружение первого.
4. В Models выбрать уже установленный **Parakeet TDT 0.6B v3 Q4_K_M**. Если модель
   не видна, использовать Rescan local models; не скачивать стандартный Q8.
   В acceleration выбрать Intel GPU, не CPU/Auto; input — встроенный микрофон,
   Wayland typing tool — `wtype`, язык — auto. Для первого сравнения оставить
   cloud/LLM post-processing и autostart выключенными. Handy на Linux по умолчанию
   не показывает recording overlay из-за возможного перехвата фокуса; пока не
   включать его. Проверить желаемое локальное хранение history/audio в настройках.
5. Для Wayland использовать штатные CLI actions Handy, не выдавать приложению
   доступ к raw input. Например, если комбинации свободны, в другом терминале
   добавить только временные Hyprland bindings:

   ```fish
   hyprctl keyword bind "SUPER CTRL SHIFT, R, exec, env VK_DRIVER_FILES=/run/opengl-driver/share/vulkan/icd.d/intel_icd.x86_64.json handy --toggle-transcription"
   hyprctl keyword bind "SUPER CTRL SHIFT, Escape, exec, env VK_DRIVER_FILES=/run/opengl-driver/share/vulkan/icd.d/intel_icd.x86_64.json handy --cancel"
   ```

   **Super+Ctrl+Shift+R** начинает/останавливает запись, **Super+Ctrl+Shift+Escape**
   отменяет операцию. Старый **Super+Shift+R** по-прежнему запускает Whisper.
6. В безопасном пустом текстовом поле проверить короткую и примерно 40-секундную
   RU/EN-диктовку, первые слоги, пунктуацию, вставку и отмену. Первый запуск
   оценивать отдельно от повторных. Parakeet v3 здесь batch: распознавание после
   остановки, не streaming. Настройки/отмена/уведомления старого helper не являются
   доказательством аналогичного поведения Handy; всё перечисленное требует пробы.
7. После пробы закрыть Handy через Quit и удалить только временные bindings:

   ```fish
   hyprctl keyword unbind "SUPER CTRL SHIFT, R"
   hyprctl keyword unbind "SUPER CTRL SHIFT, Escape"
   ```

   Рабочая диктовка остаётся на прежней клавише. Для полного удаления приложения
   и managed Q4 убрать их Lenovo declarations и повторно применить HM; личные
   настройки/history Handy автоматически не удалять.

### Проверки и ограничения

Selected HM declaration fixture прошёл для всех пяти HM-профилей: проверяет
версию/источник Handy из locked unstable,
наличие Q4 только у Lenovo, отсутствие forced overwrite, доступность `wtype` и
сохранение старых Whisper backend/hotkey declarations. Это evaluation без builds,
не UI/inference-тест. Скачивание, запуск, реальный Intel backend, скорость,
температуры, NVIDIA sleep и Wayland-поведение Handy пока не проверены.

## Последующие замеры и решение пользователя, 15.11.2026

Лёгкий `/proc` sampler (250 ms, 16 логических CPU = 100%) измерял пользовательские
записи, без чтения аудио/транскрипта и без опроса GPU. Это не same-WAV benchmark.

| Вариант | Запись | Распознавание после остановки | CPU-время процесса | Среднее / секундный пик CPU |
| --- | --- | --- | --- | --- |
| Whisper, HM №38, до Intel Vulkan | ≈47,3 с | ≈29,5 с | ≈108 CPU·с | ≈23% / 25% |
| Whisper, HM №39/40, Intel Vulkan | ≈48 с | ≈4,5–4,8 с | ≈3,8 CPU·с | ≈5% / 6% |
| Handy Q4, Intel Vulkan | 44,61 с retained audio | 3,03 с | ≈11–12 CPU·с | ≈20–25% / 42% |

Вторая частично сохранённая проба Whisper/Intel дала около 4 с, 3,3 CPU·с и
5% / 6%. В ней нет новой длинной записи Handy; из-за ошибки background shell
полное второе A/B не состоялось. Первый native log Handy подтвердил `Vulkan0`
на Intel. Изменение поколений, а не присутствие Handy, объясняет ускорение Whisper.
Потребление энергии, температуры и NVIDIA sleep во время диктовки не измерялись.

Handy печатал результат через Direct/wtype около 3,15 с; пользователь считает
вставку быстрой и удобной. Разницу между посимвольным отображением в Neovim и
кусками в OpenCode нельзя принимать за разницу ASR backend/streaming.

По трём отдельным коротким чтениям на каждом движке пользователь предпочёл
Handy Q4 за стабильность структуры/смысла фраз. Английские названия ошибались
у обоих; произношение и чтения различались, начало первой Handy-пробы могло
попасть до готовности микрофона. Это пользовательский выбор для реальной речи,
не формальный WER-рейтинг. Q8/streaming не понадобились; нагрузка Q4 принята.

Окно, перехватывающее остаток текста, оказалось `Hyprland controls`, не launcher.
Оно воспроизводилось и с Whisper №38. В двух присланных обрывах было 58 разных
символов; wtype 0.4 назначает новым символам последовательные виртуальные коды,
включая физический F1 (59). Это source-supported объяснение, но не трассировка
реального F1 event. Активная Handy-конфигурация использует штатный per-device
`keybinds = false` только для `hl-virtual-keyboard-wtype`; живая приёмка впереди.
