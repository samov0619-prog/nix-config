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

| | laptop | desktop | server |
|---|---|---|---|
| CPU | Intel | AMD | VPS |
| GPU | Intel iGPU + NVIDIA PRIME | NVIDIA only | — |
| Ввод | xremap + uinput | нет | — |
| Сеть | NetworkManager, v2raya, Amnezia | NetworkManager, v2raya, Amnezia | SSH, AWG3.1, AdGuard, NaiveProxy, SFTP |
| Boot | GRUB EFI removable | GRUB nodev | GRUB on `settings.nix.diskDevice` |
| Доп. | Hibernate/zram, Bluetooth, brightnessctl, thermald | нет | NAT, ACME, profile download |
| stateVersion | 25.11 | 25.11 | 26.05 |

### Home Manager-конфигурации

| | samov-laptop | samov-desktop | samov-server | samov-mac |
|---|---|---|---|---|
| База | users + core-set | users + core-set | users + core-set | users + core-set |
| GUI | gui-set | gui-set | — | — |
| Apps | minecraft + creative | minecraft + creative | — | — |
| Minecraft module | server + instance | server + instance | server only | — |
| Leaf | linux/laptop | linux/desktop | linux/server | — |
| Overlays | filemanager1-common, freesm | filemanager1-common, freesm | нет | нет |
| Архитектура | x86_64-linux | x86_64-linux | x86_64-linux | aarch64-darwin |

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
├── settings.nix                 # VPS-specific domain, ports, interface, SFTP key
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

Disko is imported directly by fresh `server`, `laptop-next`, and `desktop-next`
targets. It runs only through an explicit Disko/nixos-anywhere command, never
through `nixos-rebuild switch`. Current `laptop` and `desktop` intentionally do
not import Disko.

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

### OpenCode + RLM

- `home/core-set/devtools/opencode/default.nix` — кастомная установка с `LD_LIBRARY_PATH`-фикс file watcher (nix-ld не помогает, т.к. opencode уже пропатчен).
- RLM tool и plugin вендорят `node_modules/zod` рядом через `withZod`, т.к. на NixOS файлы — симлинки в /nix/store.
- tools/plugin ставятся через `xdg.configFile`, а НЕ через `programs.opencode.tools`.
- Модели: main `openai/gpt-5.6-terra`, small `opencode/deepseek-v4-flash-free`.
- `rlmRecursive = true` включает plugin-tool `rlm_subquery`.
- Проверка после правок: `opencode run "ping"`, в логе `plugin rlm.ts loading`, file.watcher backend=inotify без ERROR.

### Kitty langmap

- `home/modules/kitty/default.nix` собирает version-matched template из ${pkgs.kitty} с common и Linux/macOS fragments, затем `build.py` дублирует каждую `map`-строку с русской раскладкой. Не возвращать полную snapshot-копию upstream `kitty.conf` в репозиторий.
- `map.txt`: две строки — латиница и транслит (йцукен→qwerty).
- Активные настройки в сгенерированном конфиге: Fish, 10k scrollback, nvim pager, font size 14, NotoSansM Nerd Font Mono, grid layout, remote control, powerline tabs. Linux сохраняет stock Kitty shortcuts; macOS `kitty_mod = Cmd+Shift`, `Cmd+N`/`kitty_mod+N` создают nvim tab, `Cmd+E` — Yazi, panes `kitty_mod+Left/Right`.

### Alacritty + toggle-theme

- Темы хранятся в `~/.config/alacritty/themes/{dark,light}.toml` как symlinks.
- `toggle-theme.sh` (F11): меняет dconf GNOME color-scheme, Qt env, Alacritty symlink, Ardour UI, уведомляет через hyprctl.
- `alacritty-preview` позволяет пролистать все темы из alacritty-theme.

### Hyprland

- Конфиги хостов — raw `.conf` файлы, подключаемые через `xdg.configFile`. Не NixOS-модули.
- Laptop: без compose:ralt (xremap перехватывает), есть `on_focus_under_fullscreen`.
- Desktop: compose:ralt активен, есть `new_window_takes_over_fullscreen`.
- Оба: dwindle, zero gaps/borders, UWSM autostart, waybar, terminal-layout-en.sh.

### Window management policy

- Не добавлять manual resize bindings или resize-by-mouse: workflow использует Dwindle без ручной подгонки размеров. Fullscreen и app maximize policy сохраняются.
- Основные window controls: `Super+T` (Dwindle split), `Super+F`/`Super+Shift+F` (floating/tiled focus), `Super(+Shift)+HJKL`, workspaces и переносы между ними. Laptop: horizontal three-finger touchpad swipe переключает workspace.
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
- `hosts/server/settings.nix` описывает ровно один VPS и участвует в каждом `nixosConfigurations.server` evaluation/build/deploy. Перед любой server evaluation, build или deploy агент обязан сверить целевой SSH host с `diskDevice`, WAN interface, IPv4 endpoint и IPv6 VPN ULA в settings; при несовпадении или двух одновременно обслуживаемых VPS остановиться и запросить отдельный host configuration. Никогда не переключать settings между live VPS для обычного обновления.
- `awg-add-client <name>` публикует structured AmneziaVPN `.vpn` и QR, а также native `.conf` и QR; `naive-add-client <name>` публикует Karing/sing-box JSON.
- `vpn-download` разрешает только `internal-sftp` по одному ключу в `/srv/vpn-download/files`; shell и forwarding запрещены.
- AdGuard DNS доступен только через `awg0` и localhost; UI — через SSH tunnel на `127.0.0.1:8008`.
- Caddy/NaiveProxy включается после заполнения domain и ACME email; Caddy собран с pinned `forwardproxy` plugin.

### AmneziaVPN clients

- `pkgs/amnezia-vpn/` вендорит Linux-клиент `5.0.1.5` с `amneziawg-go`
  `v3.1.20260814`, который upstream release использует для AWG 3.1.
- Локальный клиент `5.0.1.5` проверенно работает с deployed AWG3.1 server.
- Overlay подключён только к NixOS desktop/laptop в `flake.nix`; оба хоста
  используют `pkgs.amnezia-vpn`, а daemon PATH содержит `iptables`,
  `ip6tables` и `gawk`.
- При обновлении `nixpkgs-unstable` NixOS warning появляется только если его
  официальный `amnezia-vpn` новее локального. Перед удалением override
  проверить backend AWG и service PATH; автоматически на upstream не
  переключаться.

### Disko + nixos-anywhere

- `disko` pinned as a flake input; shared layouts live in `hosts/disko/layouts.nix`.
- Remote VPS install uses `nix run github:nix-community/nixos-anywhere -- --flake .#server root@<vps-ip>` from another machine in provider rescue mode.
- `root@<vps-ip>` is SSH syntax for the remote rescue host. A local laptop/desktop install needs no IP: boot a NixOS installer USB, run Disko locally, then `nixos-install --flake .#laptop-next`.
- Before any destructive install, replace every `REPLACE_ME` after checking `lsblk`; future desktop must also confirm BIOS vs EFI with `efibootmgr -v`.
- Current laptop retains `/swapfile` plus `resume_offset`; `laptop-next` uses a swap partition with `resumeDevice = true`, so the two schemes never coexist on one host.

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

**Никогда не запускай `nixos-rebuild switch` или `home-manager switch`.**
Пользователь применяет системную и Home Manager-конфигурацию самостоятельно
после личной проверки. Для проверки агент может выполнять только evaluation
или build без активации, например `nix eval` или `nix build`.

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
sudo nixos-rebuild switch --flake .#server

# Fresh remote VPS: run preflight first. Try only the kexec bootstrap, then
# use the provider ISO fallback documented in SERVER_AI_INSTRUCTIONS.md.
nix run github:nix-community/nixos-anywhere -- --flake .#server --phases kexec root@<vps-ip>
nix build .#nixosConfigurations.server-installer.config.system.build.isoImage
# After a NixOS installer is running:
nix run github:nix-community/nixos-anywhere -- --flake .#server --phases disko,install,reboot root@<vps-ip>

# Home Manager
home-manager switch --flake .#samov-laptop
home-manager switch --flake .#samov-desktop
home-manager switch --flake .#samov-server

# Проверка
nix flake check
nix eval .#nixosConfigurations.laptop.config.system.build.toplevel --no-build 2>&1 | head
```

## Текущее состояние хостов

- **laptop**: эталон, максимально актуален. HP i7 + Intel/NVIDIA, ext4, GRUB EFI, Hibernate/zram.
- **desktop**: старше laptop. AMD + NVIDIA, два монитора (DVI 1680x1050 + HDMI 3840x2160@3x). Нет Bluetooth/uinput/xremap/hibernate.
- **server**: модульный VPS stack без Docker, Disko и generic virtio hardware modules. До первой установки заполнить `hosts/server/settings.nix` по данным rescue environment.
- **mac**: только standalone HM (users + core-set). Без nix-darwin, без GUI, без проверки совместимости Linux-пакетов.
