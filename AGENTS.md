# AGENTS.md — Карта репозитория для AI-сессий

## Архитектура

Flake: NixOS + standalone Home Manager, один пользователь `samov`.
NixOS и HM управляются раздельно: NixOS через `nixosConfigurations`, HM через `homeConfigurations`.
Нет нотации/скриптов применения — используй `sudo nixos-rebuild switch --flake .#<host>` и `home-manager switch --flake .#samov-<host>`.

### Flake

- Каналы: `nixpkgs` + `home-manager` = 26.05; `nixpkgs-unstable` передаётся через `specialArgs`.
- Системы: `x86_64-linux`, `aarch64-darwin`.
- Хелперы: `pkgsFor`, `pkgsUnstableFor`, `mkHM`, `mkNixos`.
- Overlays: `filemanager1-common` + `freesm` — только для desktop/laptop HM;
  локальный `amnezia-vpn` — только для NixOS desktop/laptop.
- `xremap-flake` передаётся в `extraSpecialArgs`.

### NixOS-хосты

|              | laptop                                             | desktop                         | server                                 |
| ------------ | -------------------------------------------------- | ------------------------------- | -------------------------------------- |
| CPU          | Intel                                              | AMD                             | VPS                                    |
| GPU          | Intel iGPU + NVIDIA PRIME                          | NVIDIA only                     | —                                      |
| Ввод         | xremap + uinput                                    | нет                             | —                                      |
| Сеть         | NetworkManager, v2raya, Amnezia                    | NetworkManager, v2raya, Amnezia | SSH, AWG3.1, AdGuard, NaiveProxy, SFTP |
| Boot         | GRUB EFI removable                                 | GRUB nodev                      | GRUB on `settings.nix.diskDevice`      |
| Доп.         | Hibernate/zram, Bluetooth, brightnessctl, thermald | нет                             | NAT, ACME, profile download            |
| stateVersion | 25.11                                              | 25.11                           | 26.05                                  |

### Home Manager-конфигурации

|                  | samov-laptop                | samov-desktop               | samov-server     | samov-mac        |
| ---------------- | --------------------------- | --------------------------- | ---------------- | ---------------- |
| База             | users + core-set            | users + core-set            | users + core-set | users + core-set |
| GUI              | gui-set                     | gui-set                     | —                | —                |
| Apps             | minecraft + creative        | minecraft + creative        | —                | —                |
| Minecraft module | server + instance           | server + instance           | server only      | —                |
| Leaf             | linux/laptop                | linux/desktop               | linux/server     | —                |
| Overlays         | filemanager1-common, freesm | filemanager1-common, freesm | нет              | нет              |
| Архитектура      | x86_64-linux                | x86_64-linux                | x86_64-linux     | aarch64-darwin   |

### Модульная структура HM

```
home/
├── users/samov/                 # username, homeDirectory, stateVersion = "25.11"
├── core-set/                    # shell, devtools, security, common CLI packages, rclone
├── gui-set/                     # browsers, MPV, Alacritty, Kitty, ueberzugpp
├── apps/
│   ├── creative.nix             # Blender
│   └── minecraft/               # FreesmLauncher, Packwiz, JDK, current instance paths
├── modules/
│   ├── alacritty/               # terminal module + themes
│   ├── kitty/                   # generated langmap-aware kitty.conf
│   └── minecraft/server/        # Packwiz → Fabric → backup-sync implementation
└── linux/
    ├── core-set/                # xray, adb, btop
    ├── gui-set/                 # Hyprland ecosystem, audio, screenshots, file manager
    ├── modules/                 # Hyprland, Waybar, tofi, xremap, FileManager1
    ├── desktop/                 # desktop leaf and raw host overrides
    ├── laptop/                  # laptop leaf and raw host overrides
    └── server/                  # server CLI, Mason prerequisites, server Neovim config

hosts/server/
├── default.nix                  # system baseline and server module imports
├── settings.nix                 # example only; real settings are an external input
├── settings-template/           # fail-closed default server-settings input
├── installer.nix                # minimal settings-based provider ISO, no Disko/services
├── vpn.nix                      # AWG3.1 bootstrap, NAT, profile generation
├── adguard.nix                  # private DNS and imported filter set
├── proxy.nix                    # Caddy + NaiveProxy plugin + Karing profiles
└── sftp.nix                     # one-key, chrooted profile download account

hosts/
├── disko/                        # reusable GPT/EFI/ext4/(swap) layouts and docs
├── laptop/                       # current laptop + legacy swapfile/resume config
├── desktop/                      # current desktop + existing storage config
├── laptop-next/                  # fresh 26.05 laptop target with Disko swap partition
├── desktop-next/                 # EFI Disko template; verify hardware before use
└── server/                       # fresh 26.05 VPS target with Disko
```

`flake.nix` is the source of truth for host composition: a feature exists on a
host only when its module is listed in that host's `modules` array.

Workstation mDNS lives in `hosts/profiles/mdns.nix`, explicitly imported by laptop,
desktop and both `*-next` outputs, not server/installer. Avahi + IPv4 NSS resolve
LAN devices such as the Zynthian Pi via `*.local`; UDP 5353 is open, own-service
publishing is disabled. Selected merged declarations/composition are checked by
`hosts/profiles/test-mdns.nix`; real Pi connectivity is not yet checked.

Disko is imported directly by fresh `server`, `laptop-next`, and `desktop-next`
targets. It runs only through an explicit Disko/nixos-anywhere command, never
through `nixos-rebuild switch`. Current `laptop` and `desktop` intentionally do
not import Disko.

Lenovo draft: `laptop-next` now has a separate `samov-laptop-next` HM output and
`home/linux/laptop-next` leaf. Existing profiles are unchanged. The NixOS draft
deliberately fails an assertion pending hardware/PRIME and target disk;
see `hosts/laptop-next/README.md`. Agreed: plain ext4 + 48 GiB swap,
no zram initially (commented opt-in with evidence-based conditions), weekly GC
keeping 10 NixOS + 10 HM generations. Initial login matches Acer: one tty1 autologin
per boot, the same public bootstrap password and password-authenticated sudo,
no Hyprlock/fprintd; improvements wait for live Lenovo. No extra Acer groups or
trusted-users privileges are copied. Do not apply the Lenovo HM
profile on Acer. Native PPD/Waybar switching is Lenovo-only. The leaf selects a
local Waybar override for dynamic previous/current/next tooltip labels, sharing
one cycle helper with clicks; stock Waybar has no such placeholders. See
`home/linux/laptop-next/waybar/README.md` for checks and update obligations.
Only the helper/patch/declarations are checked, not the full binary or live UI.
Lenovo graphics now follows unstable release packages via
`hosts/laptop-next/graphics.nix`: latest kernel, matching NVIDIA latest/open,
Mesa 64/32-bit and linux-firmware. A separate unfree-enabled `pkgsGraphics` import
is passed only to this NixOS output; a local overlay replaces only linux-firmware,
preserving other firmware and existing hosts/HM package sets. No beta/testing,
hardcoded version, lock update or automatic updater. PRIME/Bus IDs and GPU power
policy remain pending. Declaration fixtures and selected merged NixOS attributes
(including NVIDIA/open derivation evaluation, not builds) are checked; live
graphics/resume and full builds are not. See `docs/laptop-audit/graphics.md`.

## Ключевые паттерны и gotchas

### stateVersion

- Базовый `home.stateVersion` задан как `lib.mkDefault "25.11"` в `home/users/samov/default.nix`; legacy desktop/laptop/mac сохраняют это значение.
- Fresh server использует `system.stateVersion = "26.05"` и явно импортирует `home/users/samov/state-26.05.nix` через `flake.nix`.
- Для нового fresh host повторить ту же схему: system state в `hosts/<host>/default.nix`, Home Manager state module в его `modules` array.
- Когда все хосты перейдут на 26.05, удалить `state-26.05.nix`, заменить common `mkDefault` на `"26.05"` и убрать ненужные version-gated compatibility branches.

### Version-gated настройки

Три места гейтятся через `(lib.versionOlder config.home.stateVersion "26.05")`:

- `home/gui-set/default.nix:10` — Firefox configPath (`.mozilla/firefox` на старых хостах).
- `home/core-set/shell.nix:65` — Yazi shellWrapperName `yy` на старых хостах.
- `home/linux/modules/hyprland/default.nix:12` — configType `hyprlang` на старых хостах.

На новых хостах с stateVersion >= 26.05 условия ложны, поведение по умолчанию.

### Home OpenCode

- Shared exploration policy lives in `home/apps/opencode/config/AGENTS.md`. Use native
  glob/grep/read and tool-output artifacts; mechanical extraction needs no extra
  model. RLM is archived under `archive/rlm-disabled`, excluded from installation
  and normal tests. Home changes do not update the corporate Mac profile.

- Ручной порт на корпоративный Mac: актуальный снимок `~/.config/opencode`
  → объединить общие Linux-улучшения с корпоративными особенностями → полный
  архив для замены всей папки конфигурации. Сохранять модели, proxy, MCP,
  voice/TUI, permissions и npm-манифесты; перенос global-rules → AGENTS
  выполнять внутри архива. `node_modules` не включать: OpenCode устанавливает
  зависимости из package.json при запуске. Короткая инструкция — только
  README архива; отдельного сборщика/мигратора нет. Полные снимки/архивы могут
  содержать авторизацию: держать вне Git, не выводить секреты в логи.

- `home/apps/opencode/default.nix` — HM laptop/desktop на pinned OpenCode 2.1.4
  (отдельный flake input, не nixpkgs-unstable). `package.nix` добавляет
  `patches/session-routing.patch`, `patches/manual-model-routing.patch`, `patches/model-variants.patch`, `patches/session-attention.patch`,
  `patches/question-location.patch` и Linux runtime libraries. V1-модуль/исследования —
  `archive/v1`, не импортируются. README/BENCHMARK описывают текущий V2.
- Исходники сгруппированы: `config/` (V2 settings и global rules), `plugins/`,
  `patches/` (включая общий session-attention helper), `scripts/`, `skills/`,
  `sounds/`; структура установки в `~/.config/opencode` не меняется.
- Native V2 config — `config/v2-settings.nix`; установленные plugins — directories с `index.ts`/`tui.ts`
  и API `@opencode/plugin`, не V1 `@opencode-ai/plugin`.
  Model-routing собирается одним store-каталогом, HM `recursive = true` сохраняет
  managed leaf paths. Отдельные store-файлы ломают относительные импорты Bun;
  PTY проверять также с `OPENCODE_TEST_HM_GENERATION` из собранного профиля.
  Server plugins — directory symlinks `*-v2` в store с обычным `index.ts`:
  V2 discovery молча исключает entrypoint, чей realpath вне real plugin root.
  Старые leaf paths убираются HM cleanup; IDs/history сохраняются. Проверять
  server runtime также с `OPENCODE_TEST_HM_GENERATION`, не только копиями.
  Resolver остаётся штатным. После HM updates, меняющих store-каталоги плагинов,
  завершить активные задачи, выполнить `opencode service restart`, затем
  `opencode service status`: кеш Bun может оставить старый entrypoint и молча
  исключить плагин даже после `/reload`. Проверку containment не отключать.
  Закрывать все клиенты заранее не обязательно; restart прерывает серверные задачи.
  После замены binary переоткрыть TUI. Обычные config edits не требуют restart.
  Runtime smoke с HM generation проверяет загрузку ссылок в новом процессе.
- Глобального formatter и его CLI-зависимостей в OpenCode нет. Короткое правило в
  `config/AGENTS.md` требует использовать объявленный проектом CLI только для
  изменённых файлов; без правил сохранять оформление, без global fallback или
  форматирования моделью. Runtime smoke проверяет отсутствие автоформатирования.
- `decision-support.nix` — явный домашний opt-in через
  `programs.opencode.decisionSupport.enable`: короткие configured instructions,
  on-demand `decision-check` и `agent-todo-v2`. Todo — ручной Markdown/Git в
  `~/agent-todo/todo.md`, не HM-managed content. Native question показывает изменения
  и ручные правки; запись/локальный коммит только после согласия, Plan guard
  независим от session grants. Stable IDs и hash user-message в Markdown
  дедуплицируют подтверждённые обращения; Visits считает интерес, а независимый
  Priority — High/Normal/Low (по умолчанию Normal). Visits — интерес, не срочность.
  Нет фонового семантического детектора/LLM или polling.
  F3/`agent-todo-open` открывает файл в Kitty/Neovim на laptop/desktop, F1 содержит
  этот bind. Live UI/compositor проверяются на целевой машине; runtime smoke
  проверяет native forms API/Git в изолированном HOME.
  Новые заметки: `## [ ] N. Заголовок`, затем закрытый `<details>` с
  `<summary>` — кратким резюме задачи в одном предложении, не общим «Подробности»
  и не дублем короткого говорящего заголовка; ID, счётчик, цель/возврат/заметки внутри.
  `changes.add` назначает следующий номер кодом; title передавать без номера.
  Номер не является stable ID или приоритетом. Ручные `[ ]`/`[x]`, номера и старый
  формат сохранять; автоматической перенумерации нет.
  HTML-спойлер не включает folds в обычном Neovim buffer.
  Чтение `~/agent-todo/*` явно разрешено без prompt, запись остаётся за edit/Plan
  guard и подтверждением изменений. Todo UI, reason и служебные поля — английские;
  новый контент по умолчанию английский даже при русском запросе, русский только
  по явному указанию. Старый контент автоматически не переводить. Артефакты
  (код, конфиги, команды, логи, ошибки, пути, IDs, URLs, дословный текст) сохранять
  на исходном языке и без перефразирования; переводить только по прямому запросу
  перевода конкретного артефакта. Язык запроса сам по себе не делает его артефактом.
  `changes.update` меняет явные Priority/Status (Todo/In progress/Done).
  `sort: true` — только по запросу: In progress → Todo → Done; первые две группы
  по Priority, Visits ↓, Created ↑; Done по Completed ↓. Даты Unknown идут в конце,
  равенства сохраняют порядок. Номера/IDs и содержимое не переписываются; старые
  даты восстанавливаются по ограниченной локальной Git-истории с пометкой источника.
  Created/Completed и Total/Done/In progress вычисляет код; ручное закрытие помечается
  Observed, повторное открытие снимает Completed. Без фонового наблюдения.
  Только затронутые заметки/строки вместо unified diff; ручные правки показаны
  отдельно без обрезания. В 2.1.4 question description не прокручивается: todo-плагин
  использует `agent-todo-tui.tsx`: public dialog/slot/keymap/form API, одна полная
  заметка на вкладку с внутренней прокруткой, сразу первая задача. Без Proposal,
  счётчиков Review/Change и HTML-обёрток; в Markdown spoilers сохраняются.
  ←/→, Tab/Shift+Tab циклически листают, ↑/↓ прокручивают заметку, Home/End — начало/конец.
  На финальной вкладке ↑/↓ выбирают Submit/Reject/own answer; Ctrl+↑/↓ прокручивают
  пояснение, путь, commit и ручные правки. Подсказка в привычном native-стиле;
  PgUp/PgDown не листают вкладки. Одна native form — только consent/cancel transport;
  `agent-todo-review.ts` связывает поля с IDs и Submit с конкретным предложением.
  Без TUI presenter stock form не даёт случайно сохранить обрезанный текст.
  Непрозрачная подложка плагина скрывает underlying Questions до удаления формы
  после ответа/отмены, без правки host tree/cache. PTY 140×40 и 160×48 проверяет
  отсутствие второго видимого Questions/own-answer/hint, включая финальную вкладку.
  Только финальный Submit без комментариев сохраняет весь файл одним коммитом;
  Reject/Esc/закрытие/уход с сессии отменяют пакет. Reload не даёт автоматического согласия.
  Fingerprint проверяется перед формой и записью; локальное листание не вызывает
  сервер/модель. `a` открывает own answer текущей заметки, Enter сохраняет комментарий
  в форме, Tab сохраняет и листает. Любой комментарий блокирует запись; инструмент
  возвращает `feedback: [{id,title,feedback}]`, глобальный `batchFeedback` и исходный
  `draft`. Модель меняет только затронутые формулировки, сохраняет остальные черновики
  и снова запрашивает согласие. Реальный PTY 80×24 проверяет конец длинной заметки,
  циклическую навигацию, изоляцию/восстановление комментариев и однократный commit.
  `changes.add` принимает
  формулировки, код собирает Markdown/spoilers и сохраняет остальные записи побайтно;
  `changes.replace` делает точечные unique-match правки внутри stable ID, без metadata.
  Для возврата достаточно `revisited`. Полный `content` — совместимый путь только
  для явно запрошенной перестройки файла. Вложенный `changes` не попадает в огромную
  строку native generic-tool summary; старые вызовы в истории не переписываются.
  Merge/diff/counters/review/Git выполняются кодом, без модельных вызовов между
  вкладками. Новый binary patch не нужен. Esc перехватывает только `QuestionTool.CancelledError` и
  завершает tool обычным `declined`; остальные ошибки/abort не подавляются.
  `question-location.patch` сохраняет Location
  nested native question из Promise-плагина: без него форма есть в API, но не
  видна TUI. PTY smoke проверяет реальные кнопки. Этот patch меняет server runtime:
  после первого применения завершить задачи и выполнить `opencode service restart`,
  проверить `opencode service status`, переоткрыть TUI; одного `/reload` недостаточно.
- `/switch-free`/`/switch-paid` — локальные TUI-команды, без LLM. Режим живёт
  в metadata корневой сессии и влияет на последующие запросы существующих детей.
  Paid role table — единый `plugins/model-routing/routing-models.json`: Sol High work, Sol XHigh plan,
  Luna Max explore, Sol High compaction/summary, Luna Low title. Free — Big Pickle
  для всех ролей, без автоматического paid fallback. Обычная compaction до
  явного переключения сохраняет наследование session model.
  Manual model selection keeps one Free/Paid helper stack: configured Sol/Luna
  select Paid, Big Pickle selects Free, and unknown identities prompt for the
  helper stack. Do not infer a stack from provider names or catalog prices.
  Model/effort overrides are scoped to session and agent in live-root metadata;
  effort changes preserve helpers and never save a global model preference.
  Old global variant preferences must not override configured agent defaults.
  Explicit `/switch-free` or `/switch-paid` resets all overrides for the family;
  automatic agent switching preserves them. Home selections carry their metadata
  into native session creation. `manual-model-routing.patch` awaits durable policy
  updates before applying selection; reopen TUI after replacing the binary.
  `LocalProvider` wraps `DialogProvider`: NEVER call `useDialog()` from its init.
  The nested `App` binds its dialog instance through `bindHelperDialog` with cleanup;
  unknown-model selection cancels safely before binding or after disposal.
  После metadata mutation вызывать `data.session.invalidate(id)` перед `sync(id)`:
  sync кеширует hydration и иначе оставляет старый режим/модель в TUI. PTY проверяет
  public `ui.model.current()` после переключений и настоящего model picker, не одну DB.
  В каталоге только настоящие Sol/Luna с variants High/XHigh и Low/Max, без
  role-specific aliases `(plan)`/`(summary)`/`(explore)`. `model-variants.patch`
  нормализует старые session/model-routing ссылки при чтении, без правки DB/history.
  Старый `variant = "default"` у alias означает его прежний effort, а не потерю
  XHigh/High/Max; явный non-default variant сохраняется. Проверять старые сессии
  через настоящий runtime, не только plain-object unit fixture.
- Auto compaction: soft input 244000 − buffer 32000 = 212000; output 128000,
  keep.tokens 15000. V2 не имеет прежнего `prune=false`; между шагами возможен overshoot.
- `plugins/limits/` — local V2 hooks/RPC/TUI, без стороннего quota-плагина,
  отдельного LLM и idle network polling. OpenAI ChatGPT OAuth usage snapshot,
  общий per-account cache и event-driven active workers (не открытые вкладки).
  Проценты доступны только через legacy Codex OAuth; token sharing показывает
  `Limits: not exposed by token sharing`, без legacy HTTP/cache/WS и credential
  fallback. Active и ручные checkpoints сохраняются. `default.nix` напоминает
  `OPENCODE QUOTA API` при HM evaluation/build и activation (штатный жёлтый warnEcho).
  Проверять openai/codex#54219/API вручную при обновлении; удалять reminder только
  после реальных процентов/reset times, account switching и per-window warnings,
  не просто закрытия issue. Ссылки/границы проверки — README/BENCHMARK.
  Пятичасовой резерв 15/20/25% для 1/2/3 workers, warning на 10 п.п. раньше;
  недельные пороги — каждый пятичасовой × 3/22 с округлением до целого процента.
  Статусный `⚠` рядом с каждым сработавшим окном: ранний серый, основной жёлтый;
  без отдельного поля предупреждения, автоматических бюджетных инструкций модели
  и `notices`. Latch сохраняется после checkpoint, уменьшения
  workers и обновления порогов до подтверждённого renewal / >95% остатка.
  `/limits-reset` — подтверждённый override текущих limiting windows, не quota reset;
  `/checkpoint` — явный reviewed handoff request, `/checkpoint-reset` — pending.
  `Checkpoint +/✓` всегда отображается и означает agent-reported смысловую готовность,
  не Git status. Review → fixes → repeat review до отсутствия blockers; Git commit
  только при разрешении, без Git — связный код/текст и resume plan. Plan не обходит.
  Checkpoint state — session metadata; private hashed account cache — XDG state.
  `Session.Info.metadata` необязательно: отсутствие означает pending; server hooks
  не должны ломать prompt/tool admission. `checkpoint_ready` — direct tool с
  `codemode: false`. Unit/mock и узкий native runtime `test_v2_runtime.py --limits`
  покрывают отсутствие metadata, prompt/tool и создание/сброс checkpoint; живой
  OAuth/quota, installed HM layout и настоящий TUI/PTY не проверены. См. README.
- Audio — только native notifications/OpenTUI; mutable `cli.json` seeded once,
  `attention.sound`/volume/custom permission/done/error sounds. Старые V1
  notifications/mute plugins не устанавливаются. `quiet-urgency.ts` независимо
  от mute вызывает только `silent-attention.py`, без BEL/второго player.
  `session-attention.patch` + общий `session-attention.ts` изолируют native
  звук/notifications/error-toasts и local urgency по открытой сессии TUI и её
  потомкам; не по cwd/global tabs. Home/plugin routes и неизвестная ancestry
  молчат. Native события подагентов/остановки внутри этой области сохраняются.
  Это не single-owner election для одной сессии в нескольких TUI. После замены
  binary переоткрыть TUI (не только `/reload`); общий server менять не нужно.
  Самостоятельный Mac archive с официальным binary не содержит этот patch.
  Quiet urgency устанавливается одним store-каталогом с TS helper и Python kitten;
  imports/assets относительны к real entrypoint. Не подставлять пути flake source
  через replaceVars: прежний output не имел Nix references, и GC удалял helper.
  Для исторического отказа todo после GC эта причина не подтверждена; при проверке
  он был загружен. Известный кеш при retarget plugin symlink — отдельный случай.
- Звуковая граница: домашние anime done/error и freedesktop permission — только
  для личных laptop/desktop. Корпоративный Mac использует стандартные встроенные
  звуки и штатный `opencode.notifications`; удалённый `session-notifications`
  не восстанавливать. При Mac-порте не копировать домашний `cli.json`,
  `attention.sounds`, аудиофайлы или `quiet-urgency`; сохранять Mac CLI preferences
  отдельно от командного репозитория. Кастомизация native sound settings и
  изоляция через binary patch независимы. См. `home/apps/opencode/macos/README.md`.
- `workspace-context.ts` использует native V2 TUI data/router; реальный PTY smoke:
  `OPENCODE_TEST_BINARY` указывает на собранный V2 binary (см. BENCHMARK).
- Permissions — native baseline плюс Git network policies и `git-offline.ts`
  (transport/lazy-fetch env). Cached `remote show -n` не равен сетевому `show`.
  `permission-stats.ts` — native event stream, прежний history + session/request IDs.
- `opencode-task-report --session <id>` — read-only per-task accounting; методика
  в `home/apps/opencode/BENCHMARK.md`. Старые ledger-файлы XDG state
  `opencode/task-usage` сохраняются. `model-calls.ts` пишет отдельные session
  transport attempts (kind, model/variant, wire model/effort, HTTP headers status)
  в private0600 `opencode/model-calls/<session>.jsonl`, без prompts/URLs/headers.
  Отчёт читает журнал отдельно от token totals; старые title models не восстановить.
  Title usage есть в native V2 events, но не добавляется к message totals отчёта;
  это не invoice или измеритель подписочной квоты. WS response.create проверен
  unit-тестом, реальный HTTP — mock runtime с retries и обеими compaction.
- Verification coverage after changes: build without activation, isolated V2
  runtime/mock Responses, native and summarizing compaction, title/summary/children,
  and real TUI PTY. This is a coverage checklist, not authorization to run it
  automatically. Leave builds to the user unless explicitly requested; obtain
  separate approval before resource-intensive runtime or PTY checks.
  `tests/test_v2_runtime.py <binary>`: обычный, `--native`, `--catalog`, `--mac`.
  Live Kitty/audio/Waybar и Mac AVFoundation проверяются на целевой машине.
- Mac source overlay — `home/apps/opencode/macos/`; актуальная база — `Downloads/opc.zip`.
  Полный архив вне Git, два слоя opencode/opencode-local, native `{env:...}`,
  `.env.example` в Fish и явный source. Для shared service нужно окружение
  самого server/launchd, не только TUI. Локальный voice V2 использует ffmpeg +
  whisper.cpp, V1 npm voice plugin не подключать. Инструкция — README архива.

### Kitty langmap

- `home/modules/kitty/default.nix` собирает version-matched template из `${pkgs.kitty}` с common и Linux/macOS fragments, затем `build.py` дублирует каждую active `map`-строку с русской раскладкой. Commented upstream examples никогда не активировать. Не возвращать полную snapshot-копию upstream `kitty.conf` в репозиторий.
- `map.txt`: две строки — латиница и транслит (йцукен→qwerty).
- Активные настройки в сгенерированном конфиге: Fish, 10k scrollback, nvim pager, font size 14, NotoSansM Nerd Font Mono, grid layout, remote control, powerline tabs. Linux сохраняет stock Kitty shortcuts; macOS `kitty_mod = Cmd+Shift`, `Cmd+N`/`kitty_mod+N` создают nvim tab, `Cmd+E` — Yazi, panes `kitty_mod+Left/Right`.

### Alacritty + toggle-theme

- Темы хранятся в `~/.config/alacritty/themes/{dark,light}.toml` как symlinks.
- `toggle-theme.sh` (F11): меняет dconf GNOME color-scheme, Qt env, Alacritty symlink, Ardour UI, уведомляет через hyprctl.
- `alacritty-preview` позволяет пролистать все темы из alacritty-theme.

### Hyprland

- Qt appearance — shared `home/linux/modules/qt-theme` on Acer/desktop/Lenovo only:
  native qt5ct/qt6ct proxies with Adwaita, no fixed `QT_STYLE_OVERRIDE`. F11 updates
  mutable appearance-only INI keys; native plugin watchers reload open Qt Widgets
  apps (qt6ct debounce ~3 seconds), no daemon/polling. HM activation also migrates
  nomacs to `System.css` + `qt6ct-style`, with one-time backups and unrelated
  preferences preserved. Close Qt apps before activation and start a fresh session
  to replace stale environments; old `uwsm/env-toggle` is no longer sourced.
  Helper/F11 fixtures, five profiles' selected merged attributes and isolated real
  nomacs Qt6 startup/live/reopen rendering passed. Qt5, all other apps, installed
  HM layout and live Wayland/F11 remain unverified. See the module README.
- Конфиги хостов — raw `.conf` файлы, подключаемые через `xdg.configFile`. Не NixOS-модули.
- Laptop: без compose:ralt (xremap перехватывает), есть `on_focus_under_fullscreen`.
- Desktop: compose:ralt активен, есть `new_window_takes_over_fullscreen`.
- Оба: dwindle, zero gaps/borders, UWSM autostart, waybar, terminal-layout-en.sh.
- Системный Wayland bell: `onionbell.service` в HM-модуле Hyprland воспроизводит общий `xdg-system-bell-v1` (не только Kitty). Пакет pinned в `pkgs/onionbell`, с compatibility-правкой для отсутствующего `clients.pseudo` и `ogg-first-span.patch`: Rodio 0.21 принимает пустой первый Vorbis span за EOF; полное декодирование короткого bell в PCM устраняет тишину. Регрессионный тест пропускает настоящий freedesktop `bell.oga` через output mixer. Kitty использует `enable_audio_bell yes` в `common.conf`. После перехода с 0.55/0.56 на Hyprland со встроенным звуком bell (upstream PR #15502) удалить onionbell service, чтобы исключить двойное воспроизведение.
- `ipc-eof.patch` в onionbell завершает IPC reader при обрыве соединения вместо busy loop с ростом памяти. Независимые `ipc-test-harness.patch` и `ipc-tests.rs` проверяют реальные Unix-сокеты без аудиоустройства; повторное чтение после EOF ограничено guard-ом. При обновлении pinned `rev` проверить пакет без `ipc-eof.patch` по `pkgs/onionbell/README.md`: удалить только этот фикс, когда все EOF-тесты проходят без него, тесты сохранить. `flake.lock` не обновляет этот pin; конфликт patch — повод для review, не доказательство upstream-исправления.
- Для живой проверки выхода через `pw-record` обязательно задавать `--properties '{ stream.capture.sink = true }'` вместе с `--target <sink-name>` и проверять PipeWire links от `monitor_FL/FR`: без этого WirePlumber может записывать микрофон вместо выхода. Ненулевой peak сам по себе не доказывает воспроизведение bell.
- HM-модуль предупреждает `ONIONBELL CLEANUP`, когда выбранный Hyprland получает зависимость `libcanberra` — признак native bell из PR #15502, включая backports. Проверка выполняется при evaluation/build/switch без сетевых запросов. Сначала применить NixOS update и перезайти в Hyprland, остановить onionbell и проверить `printf '\a'`; после успешной проверки удалить пакет, конфиг, службу и сам reminder из HM, затем применить HM.

### Window management policy

- Не добавлять manual resize bindings или resize-by-mouse: workflow использует Dwindle без ручной подгонки размеров. Fullscreen и app maximize policy сохраняются.
- Основные window controls: `Super+T` (Dwindle split), `Super+F`/`Super+Shift+F` (floating/tiled focus), `Super(+Shift)+HJKL`, workspaces и переносы между ними. `Super+N` открывает отдельное Kitty nvim window. Laptop: horizontal three-finger touchpad swipe переключает workspace. `Super+W` открывает semantic workspace/window switcher.
- `F1` открывает read-only `hypr-controls` через Tofi; поддерживать его список в соответствии с фактическими bind-ами laptop/desktop.

### Minecraft server

- `home/modules/minecraft/server/default.nix` — пользовательский systemd модуль: Packwiz serve → update → Fabric, плюс backup path/service.
- `minecraft.server = null` по умолчанию: import generic-модуля сам по себе ничего не запускает.
- `home/apps/minecraft/default.nix` задаёт instance с путями `/home/samov/Projects/minecraft/`, памятью `20G`, FreesmLauncher, Packwiz и JDK.
- Desktop/laptop импортируют оба модуля в `flake.nix`; server импортирует только generic-модуль.
- Чтобы включить идентичный Minecraft stack на server, добавить `./home/apps/minecraft` в `samov-server.modules` в `flake.nix`.

### filemanager1-common

- `pkgs/filemanager1-common/` — месон-сборка D-Bus сервиса FileManager1.
- `home/linux/modules/filemanager1-common/` — HM-модуль с options: fileManager, wrapperScript, terminalCommand.
- По умолчанию: Yazi через Alacritty.

### xremap (laptop only)

- Модификаторы:物理 Super → Alt,物理 Alt → Super, Menu → Alt.
- GUI: Super+key → Ctrl+key (copy/paste/cut/undo/redo).
- Терминал: Super+C/V → Ctrl+Shift+C/V, остальной Ctrl не трогается.

### Neovim

- Сейчас ставится только `neovim-unwrapped` из nixpkgs без конфигурации.
- Server хранит Neovim repo, Lazy/Mason и Tree-sitter parsers вручную вне Nix
  store. Home Manager намеренно не подключает `~/.config/nvim` через
  `xdg.configFile`; для VPS используется ручная ветка `server-build`.
- Git editor и алиасы vi/vim → nvim.

### Nix generations и GC

- Store paths удаляются только когда на них не ссылается ни один GC root. NixOS
  system profile, Home Manager profile и modern `nix profile` независимы, но
  могут удерживать одни и те же store paths.
- На NixOS единственный полный cleanup запускается `sudo systemctl start
nix-gc.service`; штатный `nix-gc.timer` вызывает этот же service. Не запускать
  отдельный user timer или `nix-collect-garbage` как регулярную альтернативу.
- `nix-gc-run` запускает этот же service и выводит очистку профилей и store в
  реальном времени. `systemctl start` намеренно не передаёт stdout service в
  вызвавший терминал.
- Общий `hosts/profiles/gc.nix` запускается перед `nix-gc.service`: `nix-gc-env`
  очищает system/legacy profiles, `samov-profile-gc` очищает XDG Home Manager и
  modern user Nix profile от имени `samov`, затем `nix-gc.service` очищает store.
- Home Manager generations сохраняются по host policy: server `+2` daily,
  laptop `+3` weekly, desktop `+5` weekly. Это обеспечивает rollback именно
  конфигурации Home Manager.
- Короткий retention текущего laptop (Acer): три поколения NixOS и три HM,
  weekly GC — вынужденный компромисс из-за недостатка места на SSD, не общая
  рекомендация. После переименования в laptop-old эта причина сохраняется.
  Для Lenovo (`laptop-next`) согласованы 10 поколений NixOS и 10 HM, weekly GC через
  общий service. Запас места оценить после updates; не переносить агрессивную
  политику Acer автоматически.
- Modern `nix profile` сохраняет только current generation через `nix profile
wipe-history`: Nix не предоставляет API "keep N", а его history откатывает
  bootstrap CLI, не Home Manager configuration. Не применять `nix-env` к modern
  `nix profile`: эти форматы несовместимы.
- Текущий `~/.nix-profile` на laptop содержит рабочий `home-manager`; не удалять
  сам current user profile. Проверка 2026-09: очистка 33 старых `nix profile`
  generations и последующий store GC освободили около 14 GiB, а повторный GC
  удалил 0 paths.
- `nix-collect-garbage` без flags удаляет только уже недостижимые store paths;
  он не удаляет profile generations. Сначала очищаются generations, затем store.
- `samov-mac` импортирует `home/modules/profile-gc` только как future interface.
  Когда Mac получит расписание, реализовать `launchd` agent: Home Manager prune,
  `nix profile wipe-history`, затем `nix-collect-garbage`. macOS не имеет
  NixOS `nix-gc.service` или system profile.

### Server services

- Никакого Docker: AWG3.1 использует NixOS `wg-quick`, AdGuard Home и Caddy — обычные systemd services.
- `settings.nix` содержит незасекреченные VPS-specific значения. `server-preflight` сначала показывает read-only inventory и открывает wizard только при валидных disk/IPv4 candidates; administrator key всегда вводится вручную полным OpenSSH public key. При отсутствии global IPv6 с default route wizard требует явное `y` для продолжения без IPv6; по умолчанию выходит без записи settings. После явного подтверждения он записывает локальный, некоммитящийся settings-файл. Private keys и профили живут вне Git в `/var/lib/amneziawg` и `/var/lib/naiveproxy`.
- `hosts/server/settings.nix` — только пример. Реальные settings живут вне Git в `~/.config/nix-config/server/settings.nix` и передаются через `--override-input server-settings "path:$HOME/.config/nix-config/server"` (подразумевает `--no-write-lock-file`). Никаких private keys/passwords: input попадает в Nix store. Default input явно отказывает для server/installer; остальные hosts и server HM независимы. Preflight/verifier используют `SERVER_SETTINGS_DIR` или XDG default; verifier также принимает `--server-settings DIR`. Не фиксировать локальный путь в `flake.lock`. Перед server deploy агент обязан сверить SSH target с disk, WAN interface, IPv4 endpoint и IPv6 VPN ULA; при несовпадении остановиться. Один input описывает один live VPS, не переключать его между серверами. Для nixos-anywhere использовать готовые `--store-paths`: этот CLI не принимает override-input. Полные команды — `SERVER_AI_INSTRUCTIONS.md`.
- `awg-add-client <name>` публикует structured AmneziaVPN `.vpn` и QR, а также native `.conf` и QR; `naive-add-client <name>` публикует Karing/sing-box JSON.
- `vpn-download` разрешает только `internal-sftp` по одному ключу в `/srv/vpn-download/files`; shell и forwarding запрещены.
- AdGuard DNS доступен только через `awg0` и localhost; UI — через SSH tunnel на `127.0.0.1:8008`.
- Caddy/NaiveProxy включается после заполнения domain и ACME email; Caddy собран с pinned `forwardproxy` plugin.

### AmneziaVPN clients

- `pkgs/amnezia-vpn/` вендорит Linux-клиент `5.0.1.5` с `amneziawg-go`
  `v3.1.20260814`, который upstream release использует для AWG 3.1.
- Локальный клиент `5.0.1.5` проверенно работает с deployed AWG3.1 server.
- Linux split fixes в `pkgs/amnezia-vpn`: пустой DNS не добавляется в
  AllowedIPs; `linux-routing.patch` + `linux-default-route.h` читают netlink
  dump без общего лимита 8 KiB и исправляют dangling `qPrintable` в маршрутах.
  `checkPhase` запускает socket fixtures и ASan/UBSan на реальном
  `buildAllowedIp`; ручная проверка обоих режимов описана в README пакета.
- Overlay подключён только к NixOS desktop/laptop в `flake.nix`; оба хоста
  используют `pkgs.amnezia-vpn`, а daemon PATH содержит `iptables`,
  `ip6tables` и `gawk`.
- При обновлении `nixpkgs-unstable` NixOS warning появляется только если его
  официальный `amnezia-vpn` новее нерабочего upstream 5.0.3.0. Этот release
  завершает AWG3.1 handshake, но не назначает `amn0` VPN IPv4 из dual-stack
  `Address`, оставляя DNS недоступным. Перед удалением override проверить
  включение upstream PR #2840 (IPv4 assignment) и #3231 (endpoint routes),
  затем проверить backend AWG и service PATH; автоматически на upstream не
  переключаться.

### Disko + nixos-anywhere

- `disko` pinned as a flake input; shared layouts live in `hosts/disko/layouts.nix`.
- Remote VPS install uses verified `--store-paths` for nixos-anywhere from another machine in provider rescue mode; obtain both closures with the external settings override per `SERVER_AI_INSTRUCTIONS.md`. Keep both GC-root links via `--out-link` under `~/.local/state/nix-config/deploy/server/` until successful installation, not `--no-link` results that GC may remove.
- `root@<vps-ip>` is SSH syntax for the remote rescue host. A local laptop/desktop install needs no IP: boot a NixOS installer USB, run Disko locally, then `nixos-install --flake .#laptop-next`.
- Before any destructive install, replace every `REPLACE_ME` after checking `lsblk`; future desktop must also confirm BIOS vs EFI with `efibootmgr -v`.
- Current laptop retains `/swapfile` plus `resume_offset`; `laptop-next` uses a swap partition with `resumeDevice = true`, so the two schemes never coexist on one host.

## Форматирование этого репозитория

Форматировать только изменённые файлы через CLI, не весь репозиторий и не моделью.
Эти правила принадлежат проекту; глобальной настройки formatter в OpenCode нет.
Neovim-конфигурация не меняется. Новые конфиги не означают массовый style rewrite.

| Файлы                                | Инструмент и источник правил                                                                                                                         | Команда из корня репозитория                                                         |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Nix                                  | nixfmt 1.3.1, defaults (100 columns, 2 spaces), как nixd → `nixfmt`; flake pin                                                                       | `nix fmt -- file.nix`                                                                |
| TS/JS/MJS, JSON/JSONC, CSS, Markdown | Prettier, `.prettierrc.json` + `.prettierignore`; defaults текущего Neovim Prettier 3.9.5                                                            | `prettier --write path/to/file`                                                      |
| Python                               | Ruff, `[tool.ruff]` / `[tool.ruff.format]` в `pyproject.toml`; defaults текущего Neovim Ruff 0.17.2 (88 columns, 4 spaces, Python 3.11, без preview) | `ruff format path/to/file.py`                                                        |
| Shell                                | Beautysh 6.4.3, `[tool.beautysh]` в `pyproject.toml`: 4 spaces, `paronly`, как в Conform                                                             | `beautysh path/to/file.sh`                                                           |
| Lua                                  | LuaLS / EmmyLuaCodeStyle, `.editorconfig`, 2 spaces как LSP options Neovim; не StyLua                                                                | Форматировать через LuaLS в редакторе; без соответствующего CLI сохранять оформление |

Использовать доступный CLI той же версии, что в редакторе; если его нет, сообщить,
не подменять другим formatter и не устанавливать без запроса. Версии Prettier/Ruff/
Beautysh здесь описывают проверенный снимок, не отдельную систему установки/pinning.
Одинаковый конфиг сам по себе не гарантирует byte-identical output разных версий.
`nix fmt` использует nixfmt из flake.lock; nixd уже вызывает установленный `nixfmt`
из того же nixpkgs через `home/core-set/nix-authoring.nix` (после применения профиля).
У nixfmt нет нативного файла конфигурации стиля; выдуманный `.nixfmt`/nixd config
не добавлять. Beautysh читает `pyproject.toml` только из cwd: запускать из корня.
На `hosts/server/preflight.sh` Beautysh 6.4.3 даёт существующую ошибку
`indent/outdent mismatch`; не менять скрипт ради форматтера и не скрывать ошибку.
Python lint fixes (`ruff check --fix`) не являются форматированием.

Для C/C++, Rust, raw `.conf`, patches, ключей и прочих типов без объявленного
formatter сохранять существующее оформление. Generated locks не форматировать.
Neovim раньше не выбирал Prettier без config/dependency; `.prettierrc.json` теперь
явно включает его для поддерживаемых типов в этом проекте, включая CSS/Markdown.

## Полезные команды

## Обновление flake и конфигураций

`nix-flake-update-verify` — декларативная команда из `home/core-set`.
Она обновляет ровно один root input и выполняет настоящие `nix build --no-link`
только для выбранного host. Большой update может потребовать дополнительное
место в `/nix/store`, сопоставимое с размером текущего closure; при массовом
пересборе ориентироваться на запас до двух размеров текущего closure.
Backup OpenCode-сессий для этой операции не нужен: update и build не меняют
установленный OpenCode или его storage.

На laptop обновить один input и проверить только laptop outputs:

```bash
nix-flake-update-verify --hosts laptop --input nixpkgs
```

- Inputs: `nixpkgs`, `nixpkgs-unstable`, `home-manager`, `browser-previews`,
  `disko`, `freesm`, `nix-gc-env`, `xremap-flake`; `all` доступен только
  явно через `--input all`.
- Hosts: `laptop`, `desktop`, `server`, `server-installer`, `mac`; `--hosts
all` проверяет все hosts, поддерживаемые текущей платформой: Linux hosts на
  Linux и `mac` на macOS.
- Linux hosts `laptop`, `desktop` и `server` строят свои NixOS и Home Manager
  outputs; `server-installer` строит только NixOS ISO output; `mac` строит
  только свой Home Manager output на macOS.
- `laptop-next` и `desktop-next` намеренно не поддерживаются: это
  непроверенные шаблоны будущего оборудования.

После переноса одного и того же `flake.lock` на другую машину проверить её
host без изменения lock-файла:

```bash
nix-flake-update-verify --hosts desktop --no-update
nix-flake-update-verify --hosts server --no-update
```

Локальный server build не подключается к VPS. Сверка server settings с VPS
нужна перед deploy, не перед verification.
Для `server`, `server-installer` и Linux `--hosts all` verifier требует внешний
`settings.nix` до update/build. По умолчанию — `~/.config/nix-config/server`,
переопределение — `--server-settings DIR` или `SERVER_SETTINGS_DIR`.
Override применяется только к серверным NixOS outputs и не записывается в lock.

На Mac:

```bash
nix-flake-update-verify --hosts mac --no-update
```

Для обновления input на Mac заменить `--no-update` на `--input <name>`.

При любой ошибке команда немедленно завершается и оставляет `flake.lock` для
обычного Git review или rollback. Nix печатает исходную ошибку, после чего
скрипт выводит machine-readable summary, например:

```text
FAILED: phase=build; input=nixpkgs; host=laptop; output=home-manager; exit=1
```

Команда не делает switch, Git commit или автоматический rollback.

## Применение конфигурации

- NEVER run `nixos-rebuild switch` or `home-manager switch`. The user applies
  NixOS and Home Manager configurations after personal review.
- Leave Nix closure verification builds to the user by default. This includes
  `nix build`, `nix flake check`, rebuild/build commands, and scripts that invoke
  builds, including `nix-flake-update-verify`. Run a specific build only when the
  user explicitly requests it; general review or commit approval is not enough.
- Lightweight evaluation without realizing derivations is allowed. Obtain
  approval before expensive evaluation.
- Provide the smallest verification command for the affected host/output.
  Do not run the full verification matrix automatically.

### Область применения изменений

В итогах всегда явно указывать, как применять каждую группу изменений:

- `hosts/<host>/` и NixOS-модули: пользователь запускает `nixos-rebuild` с
  рабочей станции; для VPS — через `--target-host` SSH alias.
- `home/` и Home Manager-модули: пользователь запускает Home Manager для
  нужного профиля; server Home Manager активируется на VPS по SSH.
- Документация и ручное состояние (Neovim, Lazy, Mason, созданные VPN
  профили): Nix activation не требуется; явно привести ручную команду, если
  она нужна.

```bash
# NixOS
sudo nixos-rebuild switch --flake .#laptop
sudo nixos-rebuild switch --flake .#desktop
sudo nixos-rebuild switch --flake .#server --override-input server-settings "path:$HOME/.config/nix-config/server"

# Fresh remote VPS: run preflight first. Try only the kexec bootstrap, then
# use the provider ISO fallback documented in SERVER_AI_INSTRUCTIONS.md.
# First obtain verified $disko_script/$nixos_system per SERVER_AI_INSTRUCTIONS.md.
nix run github:nix-community/nixos-anywhere -- --store-paths "$disko_script" "$nixos_system" --phases kexec root@<vps-ip>
nix build --override-input server-settings "path:$HOME/.config/nix-config/server" .#nixosConfigurations.server-installer.config.system.build.isoImage
# After a NixOS installer is running:
nix run github:nix-community/nixos-anywhere -- --store-paths "$disko_script" "$nixos_system" --phases disko,install,reboot root@<vps-ip>

# Home Manager
home-manager switch --flake .#samov-laptop
home-manager switch --flake .#samov-desktop
home-manager switch --flake .#samov-server

# Проверка
nix flake check --override-input server-settings "path:$HOME/.config/nix-config/server"
nix eval .#nixosConfigurations.laptop.config.system.build.toplevel --no-build 2>&1 | head
```

## Текущее состояние хостов

- **laptop**: текущий Acer с Intel/NVIDIA, ext4, GRUB EFI, Hibernate/zram; точная модель здесь не зафиксирована. Перед установкой Lenovo переименовать в laptop-old, имя laptop передать Lenovo. Снимок stable inputs требует актуализации; короткий GC-retention обусловлен нехваткой места на SSD Acer.
- **desktop**: старше laptop. AMD + NVIDIA, два монитора (DVI 1680x1050 + HDMI 3840x2160@3x). Нет Bluetooth/uinput/xremap/hibernate.
- **server**: модульный VPS stack без Docker, Disko и generic virtio hardware modules. Preflight пишет внешний settings input по данным rescue environment; в Git остаётся только пример.
- **mac**: только standalone HM (users + core-set). Без nix-darwin, без GUI, без проверки совместимости Linux-пакетов.
