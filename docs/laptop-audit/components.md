# Каталог компонентов Acer

[Обзор и границы](README.md) · [Полные цепочки импортов](modules.md)

Это группировка настроек и пользовательски значимых компонентов, не полный
per-output provenance и не рекомендация немедленно удалить опциональное ПО.
Пути в таблицах относительны корню репозитория; каждый локальный module source
связан ссылкой в [карте](modules.md). Версии — из датированного среза, не обещание latest.

Каталог сохраняет исходный срез `a2d1767`. После ревью Aider и EasyEffects
отключены в декларациях laptop/desktop, но profile activation ещё не выполнялась.
Текущие решения и открытые вопросы см. в [журнале ревью](feedback.md).

## Система и оборудование

| Группа                | Состав / source                                                                                                            | Класс и перенос                                                                                           |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Загрузка и storage    | `hosts/laptop/{default,hardware}.nix`: GRUB EFI removable, initrd systemd, ext4, firmware, Intel microcode, kernel modules | **База + железо.** Сканировать Lenovo заново; не переносить disk identifiers                              |
| TPM workaround        | `hosts/laptop/default.nix`: system/initrd TPM2 отключены, комментарий о задержке загрузки                                  | **Совместимость Acer.** Причину на Lenovo не предполагать; не отключать автоматически                     |
| Swap/hibernate        | Там же: swapfile 16 GiB + resume offset, zram 50%, swappiness 10                                                           | **Железо/policy.** Fresh scaffold использует swap partition; схемы не смешивать                           |
| Питание               | Там же: governor `performance`, thermald, игнорирование lid/power/suspend/hibernate keys                                   | **Workflow + железо.** Отдельно выбрать battery/suspend/security policy Lenovo                            |
| Графика               | Там же: Intel media driver/`iHD`, NVIDIA `legacy_580`, `open = false`, modesetting, PRIME offload, фиксированные Bus IDs   | **Железо + совместимость.** NVIDIA target 580.173.02 не универсальный драйвер Lenovo                      |
| Ввод/яркость          | Там же: uinput, группа input, brightnessctl; HM xremap                                                                     | **Workflow + железо.** Проверить keyboard events и права; remap — личный выбор, не NixOS requirement      |
| Сеть                  | Там же: NetworkManager, отключён wait-online                                                                               | **База + policy.** Проверить зависимости сервисов от готовой сети                                         |
| Discovery             | Там же: Avahi, mDNS и firewall opening                                                                                     | **Опция.** Уточнить необходимость и допустимость в публичных сетях                                        |
| VPN/proxy             | Там же: v2raya с Xray; локальная Amnezia 5.0.1.5; HM также Xray                                                            | **Workflow + совместимость.** Разобрать роль каждого; raw credentials/profiles не инвентаризировать в Git |
| Bluetooth             | Там же: BlueZ + Blueman                                                                                                    | **Опция + железо.** Зависит от периферии и адаптера                                                       |
| Звук                  | Там же: PipeWire, WirePlumber, ALSA 32-bit, Pulse/JACK, rtkit                                                              | **База desktop**, JACK/32-bit по сценариям игр/DAW                                                        |
| Removable media/права | Там же: UDisks2, polkit; HM udiskie                                                                                        | **Workflow.** Не заменяет аудит правил авторизации                                                        |
| Сессия                | Там же: getty → Bash login → UWSM → Hyprland; XWayland, portals                                                            | **База выбранного GUI.** Не требуется headless ОС; XWayland — compatibility layer                         |
| Учётная запись        | Там же: initial password, autologin-once, wheel/trusted-user, input/adbusers/dialout                                       | **Security review до Lenovo.** Значения пароля не копируются; текущий пароль/runtime не проверены         |
| Эксплуатация          | `hosts/profiles/gc.nix` + host policy: weekly GC, три NixOS/HM поколения; Nix fetch concurrency, automatic timezone        | **База + policy.** Retention Acer обусловлен SSD; timezone имеет сетевой сценарий                         |
| Fonts                 | Host fonts defaults + Noto/Droid Nerd fonts; Kitty также добавляет Noto                                                    | **Workflow.** Повторные references не доказывают двойное хранение                                         |
| Steam                 | `hosts/laptop/default.nix`: Steam и steam-run                                                                              | **Опция, тяжёлое?** Проверять вместе с 32-bit/graphics dependencies                                       |
| nix-ld                | Там же: C/C++ runtime, zlib, OpenSSL, curl, glib                                                                           | **Workflow/совместимость** для внешних бинарей, в том числе Mason; не основа чистого NixOS                |

Значительная часть 113 system outputs — generated NixOS environment, а не
самостоятельно выбранные приложения: Nix/rebuild/install/help, systemd, PAM/shadow,
sudo, coreutils, filesystem tools, iproute/firewall, D-Bus, libc, manuals и compression
utilities. Наличие, например, OpenSSH client package не доказывает включённый SSH
daemon; `bcache-tools`/LVM utilities не доказывают используемую схему диска.
Для этих entries точное upstream option provenance ещё предстоит дописать.

## CLI, разработка и пароли — Home Manager

| Группа            | Состав / source                                                                                                                           | Класс и замечания                                                                                |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Shell/navigation  | `home/core-set/shell.nix`: Fish, fzf, Atuin, zoxide, direnv + nix-direnv                                                                  | **Workflow.** History/sync и разрешение direnv требуют отдельного security review                |
| Shell environment | Там же: чтение внешнего secrets env, proxy helper                                                                                         | **Workflow/security.** Переносить механизм отдельно от содержимого; env parser ещё не проверен   |
| CLI utilities     | `home/core-set/packages.nix`: ripgrep, fd, unzip, socat; `core-set/default.nix`: rclone                                                   | **Workflow**, не универсальный OS minimum                                                        |
| File workflow     | `core-set/shell.nix`: Yazi 26.9.1, compress plugin с API patch, archive rules, wrapper `yy` для legacy state                              | **Workflow + совместимость.** Yazi и plugin из unstable; на новом state меняется default wrapper |
| Editor            | `core-set/devtools/neovim.nix`: neovim-unwrapped 0.12.3, EDITOR, vi/vim aliases                                                           | **Workflow.** Конфиг/Lazy/Mason/parsers — внешнее mutable состояние; не декларативный перенос    |
| Nix authoring     | `core-set/nix-authoring.nix`: nixfmt 1.3.1, nixd, git-filter-repo                                                                         | **Опция dev.** git-filter-repo не повседневное требование Nix                                    |
| SDK               | Явные `core-set/{go,node,python,native-build,treesitter,devenv}.nix`: Go, Node, Python, GCC/Make, Tree-sitter CLI, devenv                 | **Опция dev, тяжёлое?** Решить global vs project devShell после выяснения сценариев              |
| GitHub CLI        | `core-set/devtools/github.nix`: gh                                                                                                        | **Workflow dev.** Не включает разрешение агенту выполнять remote Git operations                  |
| Обновления        | `core-set/nix-flake-update-verify.nix`: helper с runtimeInputs Git/Nix/Python/coreutils                                                   | **Workflow.** Его запуск действительно строит outputs; в этом шаге не запускался                 |
| Password workflow | `core-set/security.nix`: GPG, gpg-agent, pass, hour cache, external cache запрещён; Linux GUI добавляет pinentry-qt и pass-secret-service | **Workflow/security.** Не замена disk encryption или screen lock; секреты и ключи вне отчёта     |
| Linux CLI         | `home/linux/core-set`: btop, Xray, android-tools, adbfs-rootless, phone mount helpers                                                     | **Опции.** ADB и proxy не обязательны для каждого laptop                                         |

HM также создаёт служебные session-vars, manuals, MIME outputs и desktop entries.
Git присутствует в вычисленном HM package list; helper явно использует его в
runtimeInputs, но это ещё не точная атрибуция всех Git references и настроек.

## GUI, терминалы и интеграция

| Группа                     | Состав / source                                                                                                  | Класс и замечания                                                                                                |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Терминал основной workflow | `home/modules/kitty`: Kitty 0.47.0, upstream version-matched template, common/Linux fragments, langmap generator | **Workflow.** `home.packages` + generated config — корректная схема без `programs.kitty.enable`                  |
| Второй терминал            | `home/modules/alacritty`: Alacritty 0.17.0, темы, preview; Hyprland toggle-theme всё ещё обслуживает его         | **Опция.** Переход не завершён; не удалять до проверки theme/integration dependencies                            |
| Браузеры                   | `home/gui-set`: Firefox 152.0.4 и Chrome 154.0.8037.57 из browser-previews                                       | **Workflow/опции, тяжёлое?** Chrome — MIME default; Firefox configPath legacy-gated                              |
| Media                      | Там же MPV 0.41.0; `home/linux/gui-set`: Audacious 4.5.1                                                         | **Опции.** Разные сценарии; не объявлять дублями без обсуждения                                                  |
| Files/images               | ueberzugpp из GUI; swayimg 5.6 из unstable; FileManager1 local overlay, Yazi opener, XDG MIME/archive rules      | **Workflow + совместимость.** FileManager1/Tofi/XDG/Hyprland используют Kitty; изображения — swayimg             |
| Desktop shell              | `home/linux/modules/{hyprland,waybar,tofi}`: Waybar 0.15.0, Tofi 0.9.1, hyprpaper; `linux/gui-set`: Mako         | **Workflow.** Raw Hyprland/Waybar configs — laptop leaf; нужен отдельный startup audit                           |
| Menus/helpers              | Tofi pass/session/mount menus, `hypr-controls`, semantic switcher, `agent-todo-open`                             | **Workflow.** Helpers тянут runtimeInputs (pass/ripgrep/wtype/util-linux и др.), не все отдельные top-level apps |
| Window context             | Hyprland module: local hypr-spaces, Lua context для Neovim/Yazi, terminal focus watcher                          | **Workflow + совместимость.** C++ plugin зависит от Hyprland ABI; Lua hook не управляет всем Neovim config       |
| Bell                       | Там же: onionbell 0.2.0, freedesktop sound, audio/IPC patches                                                    | **Совместимость.** При рабочем native Hyprland bell удалить обход после проверки, иначе возможен двойной звук    |
| Screenshots/clipboard      | `linux/gui-set`: grim, slurp, swappy, wl-clipboard, libnotify; helpers используют wtype                          | **Workflow.** Clipboard/input permissions учитывать при security review                                          |
| Audio UI/DAW               | Там же pwvucontrol, EasyEffects 8.2.4, Ardour 9.7                                                                | **Опции, тяжёлое?** Базовый звук не требует DAW/effects                                                          |
| Desktop utilities          | Там же FreeFileSync 14.9, qBittorrent 5.2.2, udiskie; Qt Adwaita integration, cursor                             | **Опции/workflow.** Синхронизация/торренты требуют отдельных data/network решений                                |
| Input remap                | `linux/modules/xremap`: внешняя HM implementation + Acer modifier/terminal rules                                 | **Workflow + железо.** Проверить фактическую клавиатуру Lenovo до переноса                                       |
| Host UI overrides          | `linux/laptop`: raw monitor mode, battery name, keyboard config; voice Vulkan device override                    | **Железо.** Не копировать Acer connector/battery/GPU index как Lenovo defaults                                   |

## Отдельные приложения и скрытые зависимости

| Сценарий                 | Подключение                                                                                                                         | Класс и замечания                                                                                                     |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| AI coding                | `home/apps/opencode`: pinned OpenCode 2.1.4 + local patches/plugins, stats/report helpers, decision-support                         | **Опция + сопровождение.** Авторизация/history/todo mutable; наличие plugins не означает отдельный daemon для каждого |
| AI coding альтернативный | `home/apps/aider`: `aider-chat-full` 0.86.1, output name содержит Playwright/browser/Bedrock extras                                 | **Опция, тяжёлое?** Измерить реальную необходимость полного варианта, не считать минимальным Aider                    |
| Диктовка                 | `home/modules/voice-dictate`: PipeWire capture → Whisper.cpp → clipboard/wtype; multilingual small Q5_1 model, Vulkan build         | **Опция + железо, тяжёлое?** Модель/runtimeInputs вне отдельного app entry; GPU index Acer не переносим               |
| Minecraft client/tooling | `home/apps/minecraft`: FreesmLauncher overlay, Packwiz, JDK headless 21                                                             | **Опция, тяжёлое?** Client/tooling отличать от server                                                                 |
| Minecraft server         | Generic `home/modules/minecraft/server` + instance из apps: Packwiz bootstrap, Fabric jar, update/server/backup units, memory `20G` | **Опция/resource policy.** Это конфигурация JVM, не измеренное потребление; downloads/worlds/backup mutable           |
| 3D                       | `home/apps/creative.nix`: Blender 5.1.1                                                                                             | **Опция, тяжёлое?** Проверять GPU/backend на Lenovo                                                                   |

Важно сохранять уровни зависимостей: model fetch, Java jars, Kitty template generation,
fonts, Yazi plugins, Hyprland shared library, VPN backends и OpenCode patches не обязаны
иметь отдельную строку в `home.packages`. Этот каталог отмечает их наличие, но пока не
измеряет closures, cache sizes, startup cost или использование GPU/RAM.

## Предварительно известные механизмы запуска

- NixOS: getty/Bash/UWSM цепочка в host module; HM Hyprland module использует
  `package = null`, `portalPackage = null`, `systemd.enable = false`, оставляя
  binary/portal NixOS и управление сессией UWSM. Это не две установки compositor.
- Raw Hyprland config запускает Waybar через `uwsm app` и terminal focus watcher
  через `exec-once`. Не все компоненты GUI выражены user services.
- HM snapshot содержит 12 service definitions: EasyEffects, FileManager1,
  ftb-backups, gpg-agent, hyprpaper, minecraft-packwiz-update, minecraft-server,
  onionbell, packwiz-serve, pass-secret-service, udiskie, xremap. Имена сгруппированы
  здесь без локальных путей; фактическое состояние процессов не проверено.
- Minecraft services связаны с `minecraft.target`, backup path — с `default.target`.
  Наличие server unit **не доказывает автозапуск Minecraft при login**.
- HM объявляет targets `minecraft`/`tray`, backup path и не объявляет timers в
  выбранном срезе; HM sockets пока не собраны. Отсутствие Mako в списке services
  не доказывает отсутствия D-Bus activation.
- NixOS snapshot содержит 70 enabled service definitions и timers `fstrim`,
  `logrotate`, `nix-gc`; это не 70 постоянно работающих служб.

Полный startup/provenance audit — следующий небольшой шаг. Все спорные удаления,
security changes и hardware adaptations остаются решениями для отдельного ревью.
