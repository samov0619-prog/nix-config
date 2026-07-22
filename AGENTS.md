# AGENTS.md — Карта репозитория для AI-сессий

## Архитектура

Flake: NixOS + standalone Home Manager, один пользователь `samov`.
NixOS и HM управляются раздельно: NixOS через `nixosConfigurations`, HM через `homeConfigurations`.
Нет нотации/скриптов применения — используй `sudo nixos-rebuild switch --flake .#<host>` и `home-manager switch --flake .#samov-<host>`.

### Flake

- Каналы: `nixpkgs` + `home-manager` = 26.05; `nixpkgs-unstable` передаётся через `specialArgs`.
- Системы: `x86_64-linux`, `aarch64-darwin`.
- Хелперы: `pkgsFor`, `pkgsUnstableFor`, `mkHM`, `mkNixos`.
- Overlays: `filemanager1-common` + `freesm` — только для desktop/laptop HM.
- `nvim-config` и `xremap-flake` передаются в `extraSpecialArgs`.

### NixOS-хосты

| | laptop | desktop | server |
|---|---|---|---|
| CPU | Intel | AMD | VPS |
| GPU | Intel iGPU + NVIDIA PRIME | NVIDIA only | — |
| Ввод | xremap + uinput | нет | — |
| Сеть | NetworkManager, v2raya, Amnezia | NetworkManager, v2raya, Amnezia | SSH, AWG2, AdGuard, NaiveProxy, SFTP |
| Boot | GRUB EFI removable | GRUB nodev | GRUB /dev/sda |
| Доп. | Hibernate/zram, Bluetooth, brightnessctl, thermald | нет | NAT, ACME, profile download |
| stateVersion | 25.11 | 25.11 | 25.11 |

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
    ├── core-set/                # xray, adb, btop, Home Manager GC timer
    ├── gui-set/                 # Hyprland ecosystem, audio, screenshots, file manager
    ├── modules/                 # Hyprland, Waybar, tofi, xremap, FileManager1
    ├── desktop/                 # desktop leaf and raw host overrides
    ├── laptop/                  # laptop leaf and raw host overrides
    └── server/                  # server CLI, Mason prerequisites, server Neovim config

hosts/server/
├── default.nix                  # system baseline and server module imports
├── settings.nix                 # VPS-specific domain, ports, interface, SFTP key
├── vpn.nix                      # AWG2 bootstrap, NAT, profile generation
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

- `home/modules/kitty/default.nix` генерирует `kitty.conf` через build-деривацию: `build.py` читает конфиг + `map.txt` и дублирует каждую `map`-строку с русской раскладкой.
- `map.txt`: две строки — латиница и транслит (йцукен→qwerty).
- Активные настройки в сгенерированном конфиге: Fish, 10k scrollback, nvim pager, font size 14, NotoSansM Nerd Font Mono, grid layout, remote control, powerline tabs.

### Alacritty + toggle-theme

- Темы хранятся в `~/.config/alacritty/themes/{dark,light}.toml` как symlinks.
- `toggle-theme.sh` (F11): меняет dconf GNOME color-scheme, Qt env, Alacritty symlink, Ardour UI, уведомляет через hyprctl.
- `alacritty-preview` позволяет пролистать все темы из alacritty-theme.

### Hyprland

- Конфиги хостов — raw `.conf` файлы, подключаемые через `xdg.configFile`. Не NixOS-модули.
- Laptop: без compose:ralt (xremap перехватывает), есть `on_focus_under_fullscreen`.
- Desktop: compose:ralt активен, есть `new_window_takes_over_fullscreen`.
- Оба: dwindle, zero gaps/borders, UWSM autostart, waybar, terminal-layout-en.sh.

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
- Server дополнительно подключает `nvim-config` через `xdg.configFile."nvim"`; Lazy/Mason собирают пользовательские компоненты вне Nix store.
- Git editor и алиасы vi/vim → nvim.

### Server services

- Никакого Docker: AWG2 использует NixOS `wg-quick`, AdGuard Home и Caddy — обычные systemd services.
- `settings.nix` содержит незасекреченные VPS-specific значения и должен быть заполнен перед установкой; private keys и профили живут вне Git в `/var/lib/amneziawg` и `/var/lib/naiveproxy`.
- `awg-add-client <name>` публикует AmneziaVPN `.conf` и QR; `naive-add-client <name>` публикует Karing/sing-box JSON.
- `vpn-download` разрешает только `internal-sftp` по одному ключу в `/srv/vpn-download/files`; shell и forwarding запрещены.
- AdGuard DNS доступен только через `awg0` и localhost; UI — через SSH tunnel на `127.0.0.1:8008`.
- Caddy/NaiveProxy включается после заполнения domain и ACME email; Caddy собран с pinned `forwardproxy` plugin.

### Disko + nixos-anywhere

- `disko` pinned as a flake input; shared layouts live in `hosts/disko/layouts.nix`.
- Remote VPS install uses `nix run github:nix-community/nixos-anywhere -- --flake .#server root@<vps-ip>` from another machine in provider rescue mode.
- `root@<vps-ip>` is SSH syntax for the remote rescue host. A local laptop/desktop install needs no IP: boot a NixOS installer USB, run Disko locally, then `nixos-install --flake .#laptop-next`.
- Before any destructive install, replace every `REPLACE_ME` after checking `lsblk`; future desktop must also confirm BIOS vs EFI with `efibootmgr -v`.
- Current laptop retains `/swapfile` plus `resume_offset`; `laptop-next` uses a swap partition with `resumeDevice = true`, so the two schemes never coexist on one host.

## Полезные команды

```bash
# NixOS
sudo nixos-rebuild switch --flake .#laptop
sudo nixos-rebuild switch --flake .#desktop
sudo nixos-rebuild switch --flake .#server

# Fresh remote VPS (provider rescue mode)
nix run github:nix-community/nixos-anywhere -- --flake .#server root@<vps-ip>

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
