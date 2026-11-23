# OpenCode для Mac

Пользователь подтвердил: на Mac уже установлена **2.4.0**.
Заголовки версий старого seed/R3 ниже — исторические, не текущий target.
Типы затронутых ссылок сверены по пользовательскому выводу; пользователь подтвердил
применение R3, R4, прежнего README-патча и README-restore. Полная runtime-приёмка на 2.4.0 не подтверждена.

## Текущий staging-export Common/personal

`export.nix` и `../scripts/export-macos.py` готовят отдельный пакет из свежего `trf`,
без обновления seed/R3 и без установки. В нём сохранены team settings/policies,
`git-offline`, семь MCP, shared skills и исторические acceptance artifacts;
личные роли/пять команд/manual discussion-map подключаются native personal JSONC.
Mutable `cli.json`, credentials, DB и binary не экспортируются. Пользователь уточнил,
что voice-plugin на Mac не установлен; пакет его не устанавливает и не требует.
Если такой plugin появится отдельно, он также не управляется этим экспортом.
Ранее шесть export/source-проверок прошли,
включая protected hashes и custom-XDG; это не Mac/runtime-приёмка.

Публичное описание — «Общая конфигурация OpenCode» и личный слой. Имена
`corporate`/`corporatePersonal` в Nix и путях исходников оставлены для совместимости;
Git-защита, правила требований и MCP от названия не меняются.

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

## Патч поверх trf: типы discovery-ссылок

**R3 не применять до исправления brief:** пользователь уточнил, что
`/problem-brief` — только personal (дом и Mac `opencode-local`).
Экспорт исправлен: command body, README и JSONC registration находятся в personal,
Common их не содержит. Прежние патчи R1–R3 ошибочно оставляли brief в Common.
Пользователь подтвердил применение R3: нужен корректирующий diff поверх него,
не повторный R3. Тип оставшегося Common brief подтверждён: symlink на
`/Users/user/.config/opencode-local/commands/problem-brief.md`.

**R4 — `opencode-mac-update-2026-11-23-r4.patch`, поверх R3; уже применён.**
Он удаляет этот Common symlink и ошибочно добавленный Common README, восстанавливает
личное тело brief без frontmatter, регистрирует его в personal JSONC и обновляет
три README. Всего семь путей; прочие JSONC settings, providers/MCP/plugins,
mutable CLI и history не меняются. Личный brief README согласован с действующим
prompt, без изменения его смысла.

Артефакт:
`/tmp/opencode/opencode-240-migration-872kpr8y/opencode-mac-update-2026-11-23-r4.patch`.
SHA256: `7454f59df53bb1ab91939f26605de35d8aa3e767bd3522235192ac23845a7b10`.
Проверка на копии: сначала exact R3 поверх baseline с реальной brief-ссылкой,
затем R4 apply/check, полное сравнение результата и reverse/check с точным
восстановлением файлов и link target. Оба сценария — с `update-2026-11-16/`
и без него — проходят. Типы живого Mac учтены по пользовательскому выводу;
пользователь подтвердил применение R4 и прежнего README-патча (2026-11-24).
Runtime-приёмка на Mac ещё не подтверждена.

Историческая команда применения R4 — повторять на текущем Mac не нужно:

```fish
cd ~/.config
git apply --check ~/Downloads/Telegram\ Desktop/opencode-mac-update-2026-11-23-r4.patch
and git apply ~/Downloads/Telegram\ Desktop/opencode-mac-update-2026-11-23-r4.patch
```

При ошибке остановиться, не использовать `--reject` или принудительное применение.
После применения — `/reload` и одна `/problem-brief` из personal, без аргументов
и с явным запросом. Вручную удалять ссылки или откатывать R3 не нужно.

### Архитектурные принципы: Common и дом

[`updates/opencode-common-architecture-2026-11-24.patch`](updates/opencode-common-architecture-2026-11-24.patch)
добавляет семь базовых принципов в `AGENTS.md` сразу после `Engineering Choices`
и соответствующий раздел в `agents.README.md`. Это обновление **поверх предыдущего
патча с русским пояснением**; прочие правила и настройки не меняются.
Источник — `../config/AGENTS.common.md`: тот же блок входит в домашний HM `homeBase`,
без дублирования в personal. Русский README остаётся обычной документацией.

SHA256: `bfc759fa9c578931000cbe92c6d0eab00371adc7e33d745705a7862e47ef0e91`.
Прошли 33 локальных source/evaluation-теста, включая Linux/Darwin HM wiring
и сохранность прежних правил. На копиях restore/final с прежним русским README
прошли точные forward/reverse проверки; с текущим экспортом совпадают все 39 файлов.
Сборки, activation и живая проверка поведения модели не запускались.

На Mac (Fish), **из Common**:

```fish
cd ~/.config/opencode
and git apply --check ~/Downloads/Telegram\ Desktop/opencode-common-architecture-2026-11-24.patch
and git apply ~/Downloads/Telegram\ Desktop/opencode-common-architecture-2026-11-24.patch
```

При ошибке остановиться, не применять принудительно. Проверить разделы
`Architecture Principles` и «Архитектурные принципы» в двух файлах.
Дома изменения применяет пользователь через HM своего хоста; для Lenovo —
`home-manager switch --flake /home/samov/nix-config#samov-laptop`.
NixOS activation и перезапуск OpenCode для этого изменения не нужны.

### Пояснение AGENTS.md для людей

[`updates/opencode-common-agents-readme-2026-11-24.patch`](updates/opencode-common-agents-readme-2026-11-24.patch)
добавляет только `agents.README.md` в Common: краткое русское объяснение общих правил.
Это обычная документация, вне `instructions`, `{file:...}` и discovery-каталогов;
автоматически в модель не загружается. Чтение файла инструментами не запрещено.
Рабочий `AGENTS.md`, конфиги и personal не меняются.

Патч не зависит от версии README; проверен поверх restore и final.
SHA256: `0caac7ca9ef26b832944b2d0c301a8f79cc3e06e52d6336aebb4af067372c312`.
Прошли 23 локальных source/evaluation-теста, forward/reverse с точным сравнением
дерева и сверка всех 39 deployed-файлов с экспортом. Живые проверки не запускались.

В отличие от предыдущих патчей, этот применяется **из Common**, не из `~/.config`:

```fish
cd ~/.config/opencode
and git apply --check ~/Downloads/Telegram\ Desktop/opencode-common-agents-readme-2026-11-24.patch
and git apply ~/Downloads/Telegram\ Desktop/opencode-common-agents-readme-2026-11-24.patch
```

При ошибке остановиться; существующий файл не перезаписывать принудительно.
Достаточно прочитать новый README: `/reload`, перезапуск и activation не нужны.

### Финальный README-патч

[`updates/opencode-mac-readme-final-2026-11-24.patch`](updates/opencode-mac-readme-final-2026-11-24.patch)
применяется **поверх уже применённого README-restore**; предыдущие патчи не повторять.
Меняются только шесть README: Common, personal и описания четырёх команд.
Описание пятой, `/problem-brief`, сохранено без изменений.
Common возвращён к исходной структуре `trf` с необходимыми поправками для 2.4.0;
personal сокращён до подключения, регистрации и ссылок на пять команд.
Полезные scope/recovery/evidence пояснения двух review-команд восстановлены из `trf`.
Config, prompts, skills, плагины, CLI и история не меняются.

SHA256: `d339c086ba3d43de1ab00c28f1158f5d560a27c84e757453e3e54baad75fcc88`.
Прошли 22 focused source/evaluation-теста, проверки локальных ссылок и точные
forward/reverse проверки полного дерева с исторической папкой и без неё.
Это не живая Mac/model/MCP-приёмка. Сборки и activation не запускались.

После передачи файла на Mac (Fish):

```fish
cd ~/.config
git apply --check ~/Downloads/Telegram\ Desktop/opencode-mac-readme-final-2026-11-24.patch
and git apply ~/Downloads/Telegram\ Desktop/opencode-mac-readme-final-2026-11-24.patch
```

При ошибке остановиться, не применять с `--reject`/force. Затем прочитать
`opencode/README.md` и `opencode-local/README.md`, проверить ссылки на пять команд.
Выполнять команды установки из README не нужно. Обновление только документации:
сборка, activation, `/reload` и перезапуск не требуются.

### История: README-restore (уже применён)

Прежние короткие Common/personal README неправильно заменили исходную инструкцию
из `trf.zip` (208 строк). Переименование не разрешало удалять установку, V2,
env, сервисы, resolve, таблицу структуры, plugins/skills и checklist.
`COMMON.md` восстановлен по исходному README с актуализацией для 2.4.0:
семь MCP/XTracker, отдельный personal, необязательный voice и реальные plugin paths.
`PERSONAL.md` дополнен таблицей discovery, JSONC-примером agents/commands
без симлинков, разрешением `{file:...}` и native registry-проверками.
Checklist по-прежнему экспортируется без изменений; возвращены явные ссылки на него.
Config, prompts, policies и типы файлов этим восстановлением не меняются.

`opencode-mac-readme-2026-11-24.patch` — прежний патч только нейминга,
не восстановление документации. Пользователь подтвердил его применение вместе с R4;
не повторять и не откатывать их. Не считать этот README-патч окончательной версией.

Предыдущий docs-only патч —
[`updates/opencode-mac-readme-restore-2026-11-24.patch`](updates/opencode-mac-readme-restore-2026-11-24.patch).
База: **R4 + применённый `opencode-mac-readme-2026-11-24.patch`**. Меняются только
`opencode/README.md` и `opencode-local/README.md`; runtime-файлы не затрагиваются.
SHA256: `fc75ed2af920e20a12f533721d970f0e87a3a4229490b40b4f48df80c51738c7`.
На копии подтверждённой базы прошли forward/check, сравнение полного дерева и
deployed-файлов с текущим экспортом, reverse/check с точным восстановлением.
Оба сценария — с `update-2026-11-16/` и без неё — проходят.
Все **22** focused source/evaluation-проверки прошли, включая семь export-проверок,
сохранность разделов/локальных ссылок README и protected hashes.
Это не живая Mac/runtime/model/MCP-приёмка.

Историческая команда применения — на текущем Mac не повторять:

```fish
cd ~/.config
git apply --check ~/Downloads/Telegram\ Desktop/opencode-mac-readme-restore-2026-11-24.patch
and git apply ~/Downloads/Telegram\ Desktop/opencode-mac-readme-restore-2026-11-24.patch
```

При несовпадении остановиться и сохранить локальные изменения для merge,
не использовать `--reject`/force. После применения достаточно прочитать два README:
заголовок Common — «Общая конфигурация OpenCode», установка/env/resolve/структура
и ссылка на checklist присутствуют, personal содержит пример agents/commands.
Сами команды установки/проверки из README автоматически выполнять не нужно.
Это только документация: сборка, activation, `/reload` и перезапуск не требуются.

### История исправления симлинков

Первый `opencode-mac-update-2026-11-23.patch` был ошибочно подготовлен по обычным
файлам из ZIP: Mac `git apply --check` сообщил `wrong type` для трёх Common entries.
R2 использовал относительные targets из исторического R3 README, но Mac check
также не прошёл: тип совпал, строки targets — нет. Пользователь предоставил
`readlink`: `agents/review.md` и `commands/delegated-review*.md` указывают на
одноимённые пути через **`/Users/user/.config/opencode-local/`**. ZIP и прежняя
документация не заменяют проверку текущих типов и буквальных link targets.

Предыдущий `opencode-mac-update-2026-11-23-r3.patch` учитывает эти абсолютные
targets и удаляет именно три Common-симлинка (mode 120000), сохраняя/обновляя
обычные personal-файлы. SHA256:
`a401614e194d936d3b68d3de3a2a3b6ba203be5850b607aa164d4b43db4b8519`.
На fixture с точными пользовательскими ссылками воспроизведены три ошибки R2;
R3 прошёл apply/check, сравнение с тогдашним экспортом и reverse с восстановлением
содержимого и link targets. От R2 отличаются только три deletion blocks.
Пользователь подтвердил Mac apply R3; runtime-приёмка не подтверждена.
Приватный временный артефакт:
`/tmp/opencode/opencode-240-migration-872kpr8y/opencode-mac-update-2026-11-23-r3.patch`.
Первый патч/R2 заменены R3; уже применённый R3 не повторять и не откатывать ради R4.

## Исходники инструкций

Самостоятельный Mac-конфиг и HM на Mac — разные варианты установки. Для
самостоятельного порта `../config/instructions.nix` предоставляет два результата:

- `corporate` → `opencode/AGENTS.md`: нейтральное ядро `config/AGENTS.common.md` +
  правила требований/Git из `config/AGENTS.corporate.md`, без домашних правил и
  личных агентов/routing, Goals, Fish или reviewer-зависимостей.
- `corporatePersonal` → `opencode-local/AGENTS-personal.md`: переносимые личные
  правила из `config/AGENTS.md` + Mac-specific workflow из
  `config/AGENTS.corporate-personal.md`. Здесь нет `nsh`, Nix/HM, `NSH_FLAKE`,
  домашнего checkout или домашних policy/scratch-путей.

Выбор делается по **способу установки**, не `isDarwin`. HM всегда устанавливает
варианты `homeBase` и `homePersonal` раздельно, даже на Mac, и никогда не включает
правила самостоятельного Mac-конфига. Decision-support/todo также не входит в его
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
   последующие командные/личные изменения. Nix на самом Mac не нужен.
2. Включить только согласованные результаты в новый scoped patch/пакет; не
   переносить весь `config/`, `AGENTS*.md` по маске или установленный HM `AGENTS.md`.
3. Применять отдельным согласованным обновлением после backup/check. Личный файл
   подключается штатным `instructions` в personal config; нейтральные правила уже
   включены в Common, дублировать их в personal не нужно.

Это исходники экспорта, не переделанный R3. Старые seed, `trf-review/` и выпущенный
R3-патч сохранены; последующие incremental-патчи и подтверждённые применения
перечислены выше. Инженерные/evidence/formatting/verification правила находятся
в Common, личные Goals/Fish/communication/review — в personal; полная живая проверка
модельного поведения на Mac остаётся необходимой.

`../config/personal-layers.nix` также готовит личный JSONC, пять команд,
review/research и ручной discussion-map; домашний `default.nix` уже подключает свой
вариант. Полный Mac-пакет собирает `export.nix`; shared skills/settings
и семь MCP входят в Common, mutable CLI остаётся live; voice-plugin не требуется.
Team policies/`git-offline` сохраняются; менять их можно только после
согласования с командой. Подробности и ограничения тестов — [PERSONAL-LAYER.md](../PERSONAL-LAYER.md).

### XTracker и ключи задач

Инструкции Mac-конфига используют **XTracker** вместо
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
уже содержит семь MCP, которых в старом seed нет.

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
