# Установка конфигурации OpenCode на Mac

Это **подготовленный пакет для 2.4.0, не завершённая приёмка**. Старые seed/R3,
исходный ZIP и Dasha EXAMPLE ONLY не заменялись. Пакет не содержит установщика,
binary, credentials, DB, node_modules или `cli.json`.

Для новой установки: `opencode/README.md` сохраняет исходную инструкцию
из `trf.zip` — V2, clone, env для Fish/Zsh, сервис, приоритеты конфигов, resolve,
структуру и checklist skills. `opencode-local/README.md` объясняет добавление
agents/commands без симлинков. Это пути в экспортированном пакете.
Ниже — перенос существующей конфигурации, не требование
повторить уже выполненный backup или миграцию.

1. Сохраните приватный снимок текущих config/data/state и сведения о binary по
   U5-процедуре из пакета (`UPGRADE-240.md`). Закройте клиенты и остановите
   нужный сервис; не используйте `api` до завершения копирования. Для Mac уточните
   фактический channel и XDG/env: это не обязательно домашний `prod`.
2. В staging сравните пакет с **актуальными** `opencode/` и `opencode-local/`.
   Сверьте тип каждого затрагиваемого пути: обычный файл, directory, symlink и
   его target. Если появились новые командные/личные изменения после `trf`,
   остановитесь и согласуйте merge; не заменяйте каталоги целиком.
3. После review перенесите только согласованный diff. Сохраните живой mutable
   `opencode/cli.json`, env, service settings,
   authorizations и стандартные звуки. Не переносите старый seed voice-port.
   Voice-plugin у пользователя отсутствует; установка не требуется. Если он
   установлен отдельно в другом окружении, не заменяйте его этим пакетом.
   Уберите только проверенные прежние Common discovery entries:
   `agents/review.md`, `commands/delegated-review.md`,
   `commands/delegated-review-chrome.md`, `skills/discussion-map/SKILL.md`.
   `/problem-brief` и его README должны остаться только в personal; команду
   регистрирует personal JSONC. Поверх уже применённого R3 подготовлен R4
   (`opencode-mac-update-2026-11-23-r4.patch`): он учитывает абсолютный target
   Common brief `/Users/user/.config/opencode-local/commands/problem-brief.md`.
   R3 ошибочно оставлял brief в Common; R4 его не откатывает, а исправляет разделение.
   Порядок check/apply и SHA256 — в текущем разделе Mac README.
   Не удаляйте цели симлинков и чужие роли. Сохраняйте старые копии в backup.
   Три Common review/delegated entries на Mac — симлинки, а не обычные файлы
   из ZIP. Патч обязан учитывать mode 120000 и текущие буквальные targets:
   на проверяемом Mac это абсолютные `/Users/user/.config/opencode-local/...`,
   не относительные targets исторического R3 README.
   При `wrong type` остановитесь: `--check` ничего не меняет, `--reject` не нужен.
4. Передайте server-процессу `OPENCODE_CONFIG` на новый personal JSONC и прежнее
   MCP/provider окружение. Для Fish при стандартном пути:
   `set -gx OPENCODE_CONFIG "$HOME/.config/opencode-local/opencode.jsonc"`.
   `OPENCODE_CONFIG_DIR` не направляйте на personal. Настройка нового терминала
   не меняет окружение уже работающего сервера; новое окружение применяется в
   согласованном окне обслуживания. Nix/HM для этого Mac-конфига не применяется.
5. Сначала проверьте Common без personal в изолированном профиле: native роли,
   отсутствие личных команд, включая `/problem-brief`, reviewer и discussion-map.
   С personal проверьте пять команд, аргументы, read-only reviewer, наследование
   модели, current-session task/browser workflows и ручной `@discussion-map`.
6. Отдельно проверьте семь MCP, их enabled/disabled состояния, разрешённые tools,
   Copilot/proxy и реальные обращения к XTracker/Wiki. Не включайте отключённые
   серверы автоматически. Браузер — через существующий `Chrome MCP`, без нового
   Playwright. Платные запросы и доступ к закрытым данным согласуйте отдельно.
7. На Mac проверьте permissions/Always UI,
   Git-защиту без выполнения сетевых операций, mutable CLI и стандартные звуки.
   Voice/microphone/focus/insertion проверяется только при отдельной установке
   voice-plugin; у текущего пользователя его нет, этот пункт не требуется.
   Linux source/mock checks не заменяют эти проверки. При проблеме остановите
   запись данных и восстановите согласованный снимок, не только JSONC.

До выполнения этой приёмки полный rollout не считается готовым.
