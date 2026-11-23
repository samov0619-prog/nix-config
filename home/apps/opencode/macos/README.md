# OpenCode — корпоративный Mac

Пользователь подтвердил: на корпоративном Mac уже установлена **2.4.0**.
Заголовки версий старого seed/R3 ниже — исторические, не текущий target.
File/symlink types и runtime-приёмка нового пакета на 2.4.0 ещё не проверены.

## Текущий staging-export Common/personal

`export.nix` и `../scripts/export-macos.py` готовят отдельный пакет из свежего `trf`,
без обновления seed/R3 и без установки. В нём сохранены team settings/policies,
`git-offline`, семь MCP, shared skills и исторические acceptance artifacts;
личные роли/четыре команды/manual discussion-map подключаются native personal JSONC.
Внешний `@safwan-o/opencode-voice`, mutable `cli.json`, credentials, DB и binary
не экспортируются и должны остаться на Mac. Шесть export/source-проверок прошли,
включая protected hashes и custom-XDG; это не Mac/runtime-приёмка.

На машине с этим Nix-репозиторием (Fish):

```fish
set stage /tmp/opencode/opencode-240-mac-(date +%Y%m%d-%H%M%S)
python3 -B /home/samov/nix-config/home/apps/opencode/scripts/export-macos.py "$stage"
```

Destination должен быть новым; exporter отказывается обновлять существующий каталог.
Для custom XDG передать `--personal-directory /Users/<user>/<config-root>/opencode-local`.
Staging в `/tmp` не является долговременной поставкой: после review сохраните пакет
в согласованном persistent location. Состав — [COMMON.md](COMMON.md) и
[PERSONAL.md](PERSONAL.md); порядок сравнения/переноса/приёмки — [INSTALL.md](INSTALL.md).

## Исходники инструкций

Отдельный корпоративный порт и HM на Mac — разные продукты. Для будущего
самостоятельного порта `../config/instructions.nix` предоставляет два результата:

- `corporate` → `opencode/AGENTS.md`: нейтральное ядро `config/AGENTS.common.md` +
  корпоративные contracts `config/AGENTS.corporate.md`, без домашних правил и
  личных агентов/routing, Goals, Fish или reviewer-зависимостей.
- `corporatePersonal` → `opencode-local/AGENTS-personal.md`: переносимые личные
  правила из `config/AGENTS.md` + Mac-specific workflow из
  `config/AGENTS.corporate-personal.md`. Здесь нет `nsh`, Nix/HM, `NSH_FLAKE`,
  домашнего checkout или домашних policy/scratch-путей.

Выбор делается по **способу установки**, не `isDarwin`. HM всегда устанавливает
варианты `homeBase` и `homePersonal` раздельно, даже на Mac, и никогда не включает
корпоративный файл. Decision-support/todo также не входит в корпоративные
инструкции. Остальные файлы/skills/settings экспортируются явным allowlist
`export.nix`, а не копированием домашнего конфига.

Подготовить только два instruction-файла на машине с этим Nix-репозиторием
(Fish; без сборки, установки и изменения живой конфигурации):

```fish
set rules /home/samov/nix-config/home/apps/opencode/config/instructions.nix
set stage (mktemp -d /tmp/opencode/opencode-instructions.XXXXXX)
mkdir -p "$stage/opencode" "$stage/opencode-local"
nix eval --offline --raw --file "$rules" corporate > "$stage/opencode/AGENTS.md"
nix eval --offline --raw --file "$rules" corporatePersonal > "$stage/opencode-local/AGENTS-personal.md"
```

1. Проверить оба результата и diff относительно актуального Mac-снимка, сохраняя
   последующие командные/личные изменения. Nix на самом корпоративном Mac не нужен.
2. Включить только согласованные результаты в новый scoped patch/пакет; не
   переносить весь `config/`, `AGENTS*.md` по маске или установленный HM `AGENTS.md`.
3. Применять отдельным согласованным обновлением после backup/check. Личный файл
   подключается штатным `instructions` в personal config; нейтральные правила уже
   включены в корпоративный результат, дублировать их в personal не нужно.

Это исходники **следующих** обновлений, не переделанный R3. Старые seed,
`trf-review/` и выпущенный R3-патч сохранены; новый Mac-патч не создан и ничего
на Mac не применено. Инженерные/evidence/formatting/verification правила находятся
в Common, личные Goals/Fish/communication/review — в personal; живая проверка
модельного поведения после будущего переноса остаётся необходимой.

`../config/personal-layers.nix` также готовит личный JSONC, четыре команды,
review/research и ручной discussion-map; домашний `default.nix` уже подключает свой
вариант. Полный корпоративный пакет собирает `export.nix`; shared skills/settings
и семь MCP входят в Common, внешний voice-plugin и mutable CLI остаются live.
Team policies/`git-offline` сохраняются; менять их можно только после
согласования с командой. Подробности и ограничения тестов — [PERSONAL-LAYER.md](../PERSONAL-LAYER.md).

### XTracker и ключи задач

Для будущего экспорта корпоративные инструкции используют **XTracker** вместо
Kaiten. Личный Mac-слой Samov задаёт `FBDC-<number>` для новых веток и коммитов:
остальной формат берётся из Git history, но старый `KT-…` не возвращает прежний
префикс. История, существующие ветки и логи не переименовываются.

Источник `../skills/task-summary-log/SKILL.md` подготовлен из свежего Mac-снимка
для отдельного переноса в `opencode/skills/task-summary-log/SKILL.md`; HM его не
устанавливает. Ключ необязателен, новые имена — `FBDC-123456_<short-name>.md`;
существующий лог обновляется на месте после проверки соответствия задачи.
Перед созданием проверяются и прежние имена, чтобы не дублировать логи.

Это правка инструкций, не удаление `MCP-KAITEN` или его env-переменных.
Seed/R3 и исходный ZIP не менялись; новый staging-export проверен, живая Mac-приёмка не выполнена.

## История: R3 поверх применённого R2

Ниже сохранён прежний порядок R3/seed, не инструкция установки нового пакета.
Для текущего обновления использовать только [INSTALL.md](INSTALL.md): свежий `trf`
уже содержит внешний voice-plugin и семь MCP, которых в старом seed нет.

Пользователь уже применил R2. Файл
`~/Downloads/opencode-mac-update-2026-11-16-r3.patch` применяется через `git apply`
из `~/.config` **поверх R2**, без его отката. Подготовка лежит в
[`trf-review/`](trf-review/README.md). В командном `AGENTS.md` остаётся только
независимый выбор источника ТЗ; review-routing, анализ, delegated review и Chrome
audit принадлежат `opencode-local`. **Goals and Approach** остаётся личным.
Две ошибочные общие policy-ссылки R3 удаляет, три прежние discovery-ссылки команд/роли
сохраняет. Роль и code-review-template читают policies напрямую из personal.
Порядок проверки/применения — [`trf-review/INSTALL.md`](trf-review/INSTALL.md).
Это точечный Git-патч, не полная конфигурация и не архив.
Старый seed ниже и исходный `trf.zip` не изменены; не заменять ими новую базу.
Model/MCP-приёмка и установка на Mac не выполнялись.

## Предыдущий самостоятельный seed

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
