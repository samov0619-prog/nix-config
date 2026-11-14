# Карта репозитория для AI-сессий

## Как пользоваться

Это короткая точка входа, не журнал всех изменений. Читай только документацию
затронутой темы из таблицы ниже; связанные файлы не нужно загружать заранее.
Подробная [тематическая карта](docs/agent-context/README.md) помогает найти редкие
сценарии. Новые сведения и приёмку записывай в README/аудит компонента, не сюда.

## Структура и границы

- Flake: NixOS + **standalone** Home Manager, пользователь `samov`.
  Система и HM применяются отдельно. Источник истины для состава хостов —
  `flake.nix`: наличие файла модуля ещё не означает его подключение.
- `hosts/<host>/` — NixOS; `hosts/profiles/` — общие системные модули;
  `home/core-set/` и `home/gui-set/` — общая HM-база;
  `home/linux/<host>/` — Linux HM leaf; `home/linux/modules/` и `home/modules/` —
  переиспользуемые HM-модули; `pkgs/` — локальные пакеты и патчи.
- **`laptop` / `samov-laptop` — Lenovo; `laptop-old` / `samov-laptop-old` — Acer.**
  Не применять профиль Lenovo на Acer. Старых `laptop-next` aliases нет.
  `desktop-next` — непроверенный шаблон, не текущий desktop.
- Для будущих хостов конфигурация Lenovo (`hosts/laptop/` и `home/linux/laptop/`)
  — основной источник истины для актуальных пользовательских решений и поведения.
  Старые Acer/desktop не считать эталоном по умолчанию. Аппаратные параметры,
  storage, драйверы и host-specific fixes переносить только после проверки нового
  оборудования; это не разрешение применять профиль Lenovo на другом хосте.
- `server` — VPS; реальные settings передаются внешним `server-settings` input,
  tracked `hosts/server/settings.nix` — только пример. `samov-mac` — только HM,
  без nix-darwin. Корпоративный OpenCode Mac управляется отдельно от домашнего HM.
- Stable `nixpkgs`/HM — 26.05. `nixpkgs-unstable` используется выборочно;
  `nixpkgs-kernel` — только released Lenovo kernel, не RC/testing.
  Mesa должна оставаться совместимой со stable userspace/glibc.
- Не поднимать `stateVersion` вслед за input update: desktop/Acer/mac сохраняют
  25.11, fresh Lenovo/server — 26.05; HM использует отдельный state-модуль.

## Обязательные ограничения

- **Никогда не запускать `nixos-rebuild switch` или `home-manager switch`.**
  Пользователь применяет конфигурацию после своего review.
- Builds оставлять пользователю: `nix build`, `nix flake check`, rebuild/build и
  `nix-flake-update-verify` запускать только по прямому запросу на конкретную
  сборку. Review, завершение или разрешение на коммит не разрешают сборку.
  Лёгкая evaluation без realization допустима; дорогая требует согласования.
  Не запускать полную матрицу ради одного хоста.
- В итогах различать выполненные и невыполненные проверки и указывать применение:
  NixOS — `sudo nixos-rebuild switch --flake .#<host>`, HM —
  `home-manager switch --flake .#samov-<host>`; документация не требует activation.
  Server deploy — только после чтения его инструкции и сверки live target.
- Disko — только явно согласованный destructive install, не обслуживание уже
  установленного Lenovo. Перед разметкой заново сверять диск и `REPLACE_ME`.
  Не переносить Acer swapfile/resume_offset в Lenovo со swap-разделом.
- Перед server deploy читать `SERVER_AI_INSTRUCTIONS.md` и сверять SSH target,
  disk, WAN, IPv4 endpoint и IPv6 VPN ULA; при несовпадении остановиться.
  Private keys/passwords не помещать в Git или Nix inputs/store; локальный путь
  settings не фиксировать в `flake.lock`.
- Сохранять работающие VPN/audio/power-policy и принятые fixes. Не добавлять
  задержки, restart/rebind hooks, подавление логов или новые knobs без основания
  и согласования. Не будить спящий NVIDIA периодическим `nvidia-smi`.
  Остаточные сообщения не считать ни исправленными, ни безвредными без проверки.
- Перед изменением/удалением backport читать его registry entry и removal contract.
  Конфликт патча или новая версия не доказывают upstream fix; regression-сценарии
  сохранять после удаления. Не восстанавливать удалённые Kitty/BlueZ backports.
- Neovim конфиг и server Lazy/Mason/parsers управляются вручную, не подключать
  `~/.config/nvim` через HM без отдельного запроса. Не читать секреты из Fish
  `local-env.fish` при обычном аудите и не делать этот файл HM-managed.

## Документация по задаче

| Задача                                            | Сначала читать                                                                                                                                                         |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Lenovo: обслуживание, install/recovery            | [Гайд](hosts/laptop/README.md), [приёмка](docs/laptop-audit/lenovo-checklist.md); для ошибок — [boot audit](hosts/laptop/boot-errors.md)                               |
| GPU, RTD3, Hibernate; Bluetooth PM                | [Graphics audit](docs/laptop-audit/graphics.md), [Bluetooth contracts](hosts/laptop/bluetooth-pm.md)                                                                   |
| Hotkeys, resize, command keys, Lenovo Waybar      | [HM leaf](home/linux/laptop/README.md), [command keys](home/linux/laptop/command-keys/README.md), [Waybar](home/linux/laptop/waybar/README.md)                         |
| OpenCode: plugins, patches, commands, skills, Mac | [README](home/apps/opencode/README.md), [проверки и accounting](home/apps/opencode/BENCHMARK.md), [Mac](home/apps/opencode/macos/README.md)                            |
| Обновления и backports                            | [Registry и contracts](docs/backports/README.md), [update/apply справочник](docs/agent-context/reference.md#обновление-flake-и-конфигураций)                           |
| Server / Disko / VPN                              | [Server instructions](SERVER_AI_INSTRUCTIONS.md), [Disko](hosts/disko/README.md), [Amnezia](pkgs/amnezia-vpn/README.md), [installer VPN](pkgs/installer-vpn/README.md) |
| Desktop: темы, portals, звук, Yazi, GC, Minecraft | [Тематическая карта](docs/agent-context/README.md#desktop-и-приложения)                                                                                                |

## Форматирование

Только изменённые файлы, CLI проекта, без массового reformat или модельного
форматирования. Если нужного CLI/версии нет — сообщить, не устанавливать и не
подменять. Версии ниже — снимок редакторских инструментов, не отдельный pin.

| Файлы                                     | Команда / правила                                                             |
| ----------------------------------------- | ----------------------------------------------------------------------------- |
| Nix                                       | `nix fmt -- path/to/file.nix` — nixfmt из `flake.lock`                        |
| TS/JS/MJS, JSON/JSONC, CSS, Markdown      | `prettier --write path/to/file` — `.prettierrc.json`, `.prettierignore`       |
| Python                                    | `ruff format path/to/file.py` — `pyproject.toml`; lint fixes отдельно         |
| Shell                                     | `beautysh path/to/file.sh` из корня — `pyproject.toml`                        |
| Lua                                       | LuaLS в редакторе, `.editorconfig`; без соответствующего CLI сохранять layout |
| C/C++, Rust, raw `.conf`, patches, прочее | Сохранять layout; generated locks не форматировать                            |

Редакторский снимок: Prettier 3.9.5, Ruff 0.17.2, Beautysh 6.4.3;
полные оговорки — в [справочнике](docs/agent-context/reference.md#форматирование-этого-репозитория).
Beautysh уже выдаёт `indent/outdent mismatch` на `hosts/server/preflight.sh`:
не менять скрипт ради formatter и не скрывать ошибку.
