# OpenCode 2.1.4 — корпоративный Mac

Архив содержит две соседние папки: командную `opencode/` и личную
`opencode-local/`. База — снимок `opc.zip`; корпоративные Git/task-log правила,
четыре skills, Copilot X5, локальный OpenAI proxy и три MCP сохранены.
Личные правила и overrides остаются в `opencode-local/`.
`node_modules`, история сессий и авторизация в архив не входят.

## Установка (Fish)

1. Закройте OpenCode. Сохраните копии своих текущих `~/.config/opencode` и
   `~/.config/opencode-local`, затем замените их папками из архива. Используйте
   OpenCode **2.1.4**; плагины написаны под native V2 API. Корпоративный порт
   самостоятельный: Home Manager и домашние `/switch-free`/`/switch-paid` ему
   не нужны. Данные/auth в отдельном OpenCode data directory не удаляйте.
2. Создайте приватный env-файл:
   ```fish
   cp ~/.config/opencode/.env.example ~/.config/opencode/.env
   chmod 600 ~/.config/opencode/.env
   ```
   Заполните URL и полные Authorization headers. Это **Fish-файл**; значения
   заключайте в одинарные кавычки. `.env` игнорируется Git. Не публикуйте его.
3. Перед запуском явно загрузите окружение и личный слой:
   ```fish
   source ~/.config/opencode/.env
   set -gx OPENCODE_CONFIG ~/.config/opencode-local/opencode.json
   opencode --standalone
   ```
   OpenCode не обязан автоматически читать `.env`. `OPENCODE_CONFIG` добавляет
   личный config к командному; **не** задавайте `OPENCODE_CONFIG_DIR` на личную
   папку: это заменит весь global root. Для постоянной Fish-сессии эти две
   строки можно добавить в приватный Fish config.
4. Для shared background service экспортов в новой вкладке недостаточно:
   уже работающий процесс не получает новое окружение. Сначала остановите
   его через `opencode service stop`, затем запускайте из подготовленной
   Fish-сессии. Если службу запускает launchd, задайте те же переменные и
   `OPENCODE_CONFIG` в её постоянном `EnvironmentVariables` и перезапустите
   службу. Изменение `.env` само по себе launchd не обновляет. Проверяйте
   `opencode service --help` для управления установленной версией.
5. Проверьте Copilot, локальный proxy (он должен быть уже запущен на
   `127.0.0.1:8080`), Wiki/Kaiten и Chrome MCP. Chrome должен предоставлять
   debugging endpoint на `127.0.0.1:9222`. Сохранённый `chrome-devtools-mcp@latest`
   требует Node/npm; это отдельная от pin OpenCode зависимость.

## Локальный голосовой ввод

В V2 TUI нет встроенной локальной диктовки; старый npm-плагин
`@hxnnxs/opencode-voice@0.2.3` использует V1 API. Здесь самостоятельный небольшой
V2-порт: **ffmpeg AVFoundation → WAV → whisper.cpp → текст в текущем prompt**.
Аудио не отправляется облачной службе. Автоотправки текста нет.

1. Установите локальные инструменты и модель (Fish):
   ```fish
   brew install ffmpeg whisper-cpp
   mkdir -p ~/.cache/opencode-voice
   curl --fail --location --output ~/.cache/opencode-voice/ggml-base.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin
   whisper-cli --help
   ```
   Можно использовать свою совместимую модель Whisper вместо загрузки.
2. В `/voice-settings` задайте абсолютный путь к модели, язык (`auto`/`ru`/`en`),
   AVFoundation microphone (`:0` по умолчанию) и клавишу (`ctrl+r`). Настройки
   находятся в приватном `opencode/voice.json`; после смены клавиши перезапустите
   OpenCode. macOS должен разрешить микрофон используемому терминалу.
3. Сфокусируйте основной prompt, нажмите Ctrl+R: начнётся запись. Повторное
   нажатие останавливает её и запускает локальное распознавание. `/voice-stop`
   отменяет операцию. `/voice` — та же toggle-команда. После распознавания
   проверьте текст и отправьте его самостоятельно.

Запись ограничена 10 минутами, распознавание — 2 минутами. WAV временный и
удаляется после операции; завершение плагина останавливает дочерний процесс.
Если за время записи сменился prompt/сессия, текст показывается в диалоге,
а не вставляется в другое место. V2 не предоставляет public appendPrompt API:
порт использует focused OpenTUI textarea **2.1.4**; при обновлении повторить
проверку вставки/фокуса. Старые onboarding/managed-engine dialogs не переносятся;
модель и recorder устанавливаются явно командами выше.

## Звук, permissions и обновления

Native notification plugin и mutable `cli.json` управляют звуком/громкостью.
Используйте native settings; V1 `/mute`/`/unmute` и второй аудиоплагин не установлены.

**Корпоративный Mac использует только стандартные встроенные звуки OpenCode.**
Домашние anime completion/error — личные, их перенос запрещён. Не копировать
домашний `cli.json`, `attention.sounds`, `sounds/*.mp3`/`permission.wav` и
`quiet-urgency.ts` ни в командный, ни в личный Mac-слой/архив. Сохранять личные
Mac-настройки громкости/paste/sidebar отдельно от командного репозитория.

На Mac наш `plugins/session-notifications` удалён; `opencode.notifications`
работает штатно. Не восстанавливать плагин и его отключающие CLI directives
при очередном переносе. Домашний `session-attention.patch` изолирует события,
но **не** кастомизирует звук и не входит в официальный Mac binary. Установка
домашней HM-конфигурации не меняет этот самостоятельный порт.

Запросы edit/shell сохранены, исключения для task logs/date сохранены. Git-сеть
остаётся за пользователем по корпоративным правилам; локальный `git-offline`
plugin дополнительно отключает Git transports и lazy fetch в shell subprocesses.
Это не sandbox для произвольного shell-кода.

`model-calls` сохраняет модели отдельных session-вызовов, включая нейминг,
generation, compaction и HTTP retries, в приватный XDG state
`opencode/model-calls/<session>.jsonl`. Просмотр той же утилитой (Fish):

```fish
python3 ~/.config/opencode/scripts/task-report.py --recent 5
python3 ~/.config/opencode/scripts/task-report.py --session <session-id>
```

Указаны resolved model/variant и API model/effort, если доступны. Это попытки
отправки, не доказательство завершения/billing; HTTP status означает headers.
WebSocket покрывает Open Responses `response.create`. Запись начинается после
установки; prompts/ключи/тела/URL не сохраняются. Вызовы вне session hooks не
покрываются. Token totals не складываются с журналом вызовов; это не invoice.

После изменения конфигурации или plugins выполните `/reload`. На Linux
проверены native V2 загрузка/config/layering и регистрация
voice-команд. Доступ к корпоративным MCP/Copilot, микрофон и само распознавание
нужно проверить на Mac; Linux smoke не подтверждает работу AVFoundation.

Kitty MIME clipboard protocol **5522** в OpenTUI 0.6.8/OpenCode 2.1.4 не
реализован. Не добавляйте глобальные Kitty workaround mappings. Дождаться
upstream-поддержки MIME paste/OSC5522/private mode 5522, затем повторить text
и image paste в Kitty: <https://sw.kovidgoyal.net/kitty/clipboard/>.
