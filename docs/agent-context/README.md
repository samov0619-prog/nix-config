# Контекст по запросу

Корневой [AGENTS.md](../../AGENTS.md) содержит общие ограничения и короткую карту.
Эта страница и связанные документы не предназначены для автоматической загрузки
в каждую сессию. Выбери нужную тему; в большом файле сначала найди заголовок через
`grep`, затем прочитай соответствующий фрагмент, а не весь документ.

## Приоритет источников и обновления

- Состав хостов и фактические настройки сверять с `flake.nix` и модулями.
- Ограничения и согласованные решения читать в README компонента; результаты и
  границы проверок — в его аудитах/тестовой документации. Не превращать исторический
  статус «подготовлено» или «принято» в новое разрешение на build/activation.
- [reference.md](reference.md) — сохранённый текст прежнего корневого `AGENTS.md`.
  Он содержит в том числе устаревшие статусы и последовательные пересмотры решений.
  При расхождениях проверять датированные записи и актуальные исходники, не
  выбирать удобный исторический абзац. Пути внутри снимка — от корня репозитория.
- Новые знания записывать рядом с компонентом; сюда добавлять только новые точки
  входа. В корне оставлять лишь общие ограничения, границы хостов и короткие ссылки.
  Не подключать этот каталог глобальным instructions glob и не возвращать
  хронику в корневой файл: это снова увеличит каждый запрос.

## Результат сокращения: 2026-11-14

Корневой `AGENTS.md` сокращён с 96 545 до 7 413 символов (1 252 → 92 строки).
В двух пользовательских свежих root-сессиях с единственным сообщением `ping`
на build/Sol High сохранённый входной usage уменьшился с **31 052 до 9 704
токенов — на 68,7%**. Cache read/write и вызовов инструментов не было;
отдельные title-вызовы Luna Low в эти числа не включены.

В сохранённых снимках совпали глобальные инструкции, skill guidance, Code Mode,
дата и окружение; изменился только проектный `AGENTS.md`. Это один измеренный
before/after, не точная токенная разбивка источников и не проверка поведения
сокращённых инструкций. Прежнее тело сохранено в `reference.md` без изменений.
Отдельный автоматический аудитор и модельный A/B решено не добавлять;
`decision-support.md` в рамках этого аудита не менялся.

## Flake, хосты и обслуживание

| Тема                                           | Источник                                                                                                                                                                                                    |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Состав, overlays, структура HM                 | `flake.nix`; [прежняя архитектурная карта](reference.md#архитектура)                                                                                                                                        |
| stateVersion и compatibility gates             | Комментарий в начале `flake.nix`; [stateVersion](reference.md#stateversion), [version gates](reference.md#version-gated-настройки)                                                                          |
| Lenovo: текущая установка и обслуживание       | [Гайд](../../hosts/laptop/README.md), [приёмка](../laptop-audit/lenovo-checklist.md)                                                                                                                        |
| Lenovo: прошлые этапы и диагностика            | [История подготовки](../laptop-audit/lenovo-history.md), [boot audit](../../hosts/laptop/boot-errors.md), [graphics audit](../laptop-audit/graphics.md), [Bluetooth PM](../../hosts/laptop/bluetooth-pm.md) |
| Display, battery, mDNS, time, остальные аудиты | [Индекс laptop audit](../laptop-audit/README.md)                                                                                                                                                            |
| Update helper: inputs, host scope, failures    | `home/core-set/nix-flake-update-verify.nix`; [сохранённый контракт](reference.md#обновление-flake-и-конфигураций)                                                                                           |
| Backports и условия удаления                   | [README](../backports/README.md), [registry.json](../backports/registry.json), README пакета                                                                                                                |
| GC, generations, rollback retention            | `hosts/profiles/gc.nix`, `home/modules/profile-gc/`; [сохранённые ограничения](reference.md#nix-generations-и-gc)                                                                                           |
| Server settings, deployment и services         | [SERVER_AI_INSTRUCTIONS.md](../../SERVER_AI_INSTRUCTIONS.md); [дополнительный контекст](reference.md#server-services)                                                                                       |
| Disko, nixos-anywhere, storage                 | [Disko README](../../hosts/disko/README.md); [прежние ограничения](reference.md#disko--nixos-anywhere)                                                                                                      |
| Amnezia и installer VPN                        | [Amnezia README](../../pkgs/amnezia-vpn/README.md), [installer VPN README](../../pkgs/installer-vpn/README.md); [история](reference.md#amneziavpn-clients)                                                  |
| Apply scope и примеры команд                   | [Общие ограничения](../../AGENTS.md#обязательные-ограничения); [примеры](reference.md#область-применения-изменений) читать вместе с server/install gates                                                    |

## OpenCode

- [README](../../home/apps/opencode/README.md) — HM layout, binary patches, plugins,
  модели, theme/attention, permissions, limits/checkpoint и lifecycle.
- [BENCHMARK.md](../../home/apps/opencode/BENCHMARK.md) — accounting и проверочные
  процедуры; наличие команды не разрешает запуск дорогого runtime/PTY/build.
- [DELEGATED-REVIEW.md](../../home/apps/opencode/DELEGATED-REVIEW.md) и
  [Chrome audit](../../home/apps/opencode/DELEGATED-REVIEW-CHROME.md) — контракты,
  ограничения и прежние ошибки review prompts.
- [Mac README](../../home/apps/opencode/macos/README.md) — отдельный корпоративный
  перенос. Сохранять corporate models/proxy/MCP/permissions/voice и стандартные
  звуки; не копировать home routing/quota/custom audio или auth/`.git` в пакет.
- `home/apps/opencode/config/AGENTS.md` — **устанавливаемые домашние глобальные
  правила**, не корневой файл этого репозитория. `config/v2-settings.nix` — native
  settings; `default.nix` — установка; `package.nix` — патчи binary.
- [Прежний подробный контекст](reference.md#home-opencode) — редкие migration,
  metadata, cached-plugin и TUI детали. RLM/V1 — архив, не активные компоненты.

## Desktop и приложения

| Тема                                        | Источник                                                                                                                                                                |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Lenovo hotkeys, resize/reset, touchpad      | [HM README](../../home/linux/laptop/README.md)                                                                                                                          |
| Acer xremap и Lenovo command keys           | [Прежнее разделение хостов](reference.md#xremap-laptop-oldacer-only), [Lenovo README](../../home/linux/laptop/command-keys/README.md)                                   |
| Hyprland, portals, Polkit                   | [Контекст Hyprland](reference.md#hyprland), [portals audit](../laptop-audit/portals.md), [Polkit audit](../laptop-audit/polkit.md)                                      |
| Раскладка terminal/pinentry                 | [layout-en.md](../../home/linux/modules/hyprland/layout-en.md)                                                                                                          |
| Общий Waybar disk и Lenovo manual GPU/PPD   | [Общий модуль](../../home/linux/modules/waybar/README.md), [Lenovo](../../home/linux/laptop/waybar/README.md)                                                           |
| Notifications и батарея                     | [Модуль](../../home/linux/modules/notifications/README.md), [battery audit](../laptop-audit/battery.md)                                                                 |
| GTK/Qt/Ardour и F11                         | [GTK audit](../laptop-audit/gtk-theme.md), [Qt module](../../home/linux/modules/qt-theme/README.md), [Ardour module](../../home/linux/modules/ardour/README.md)         |
| Kitty langmap и Alacritty                   | `home/modules/kitty/`, `home/modules/alacritty/`; [Kitty](reference.md#kitty-langmap), [theme toggle](reference.md#alacritty--toggle-theme)                             |
| Системный bell и условия удаления onionbell | [Пакет](../../pkgs/onionbell/README.md), [backports](../backports/README.md)                                                                                            |
| FileManager1 и removable media              | `home/linux/modules/filemanager1-common/`, `pkgs/filemanager1-common/`; [контекст](reference.md#filemanager1-common), [media audit](../laptop-audit/removable-media.md) |
| Fish local secrets, Yazi archives, Neovim   | [Fish](../laptop-audit/fish-local-env.md), [archives](../laptop-audit/archives.md), [Neovim](reference.md#neovim)                                                       |
| Minecraft: generic module против instance   | [Модуль сервера](../../home/modules/minecraft/server/README.md), [состав и defaults](reference.md#minecraft-server)                                                     |

## Форматирование

Короткая [таблица в корне](../../AGENTS.md#форматирование), `.prettierrc.json`,
`.prettierignore`, `pyproject.toml`, `.editorconfig` и `flake.nix` задают правила.
[Сохранённые пояснения](reference.md#форматирование-этого-репозитория) описывают
nixd/nixfmt, editor versions, Beautysh caveat и отсутствие global fallback.
