# Перенос нового Common/personal на корпоративный Mac

Это **подготовленный пакет для 2.4.0, не завершённая приёмка**. Старые seed/R3,
исходный ZIP и Dasha EXAMPLE ONLY не заменялись. Пакет не содержит установщика,
binary, credentials, DB, node_modules или `cli.json`.

1. Сохраните приватный снимок текущих config/data/state и сведения о binary по
   U5-процедуре из пакета (`UPGRADE-240.md`). Закройте клиенты и остановите
   нужный сервис; не используйте `api` до завершения копирования. Для Mac уточните
   фактический channel и XDG/env: это не обязательно домашний `prod`.
2. В staging сравните пакет с **актуальными** `opencode/` и `opencode-local/`.
   Сверьте тип каждого затрагиваемого пути: обычный файл, directory, symlink и
   его target. Если появились новые командные/личные изменения после `trf`,
   остановитесь и согласуйте merge; не заменяйте каталоги целиком.
3. После review перенесите только согласованный diff. Сохраните живой mutable
   `opencode/cli.json`, внешний `@safwan-o/opencode-voice`, env, service settings,
   authorizations и стандартные звуки. Не переносите старый seed voice-port.
   Уберите только проверенные прежние Common discovery entries:
   `agents/review.md`, `commands/delegated-review.md`,
   `commands/delegated-review-chrome.md`, `skills/discussion-map/SKILL.md`;
   в personal уберите только дублирующую `commands/problem-brief.md`.
   Не удаляйте цели симлинков и чужие роли. Сохраняйте старые копии в backup.
4. Передайте server-процессу `OPENCODE_CONFIG` на новый personal JSONC и прежнее
   MCP/provider окружение. Для Fish при стандартном пути:
   `set -gx OPENCODE_CONFIG "$HOME/.config/opencode-local/opencode.jsonc"`.
   `OPENCODE_CONFIG_DIR` не направляйте на personal. Настройка нового терминала
   не меняет окружение уже работающего сервера; новое окружение применяется в
   согласованном окне обслуживания. Nix/HM на корпоративном Mac не применяется.
5. Сначала проверьте Common без personal в изолированном профиле: native роли,
   одна `/problem-brief`, отсутствие личных команд/reviewer/discussion-map.
   С personal проверьте четыре команды, аргументы, read-only reviewer, наследование
   модели, current-session task/browser workflows и ручной `@discussion-map`.
6. Отдельно проверьте семь MCP, их enabled/disabled состояния, разрешённые tools,
   Copilot/proxy и реальные обращения к XTracker/Wiki. Не включайте отключённые
   серверы автоматически. Браузер — через существующий `Chrome MCP`, без нового
   Playwright. Платные запросы и доступ к корпоративным данным согласуйте отдельно.
7. На Mac проверьте voice/microphone/focus/insertion, permissions/Always UI,
   Git-защиту без выполнения сетевых операций, mutable CLI и стандартные звуки.
   Linux source/mock checks не заменяют эти проверки. При проблеме остановите
   запись данных и восстановите согласованный снимок, не только JSONC.

До выполнения этой приёмки полный rollout не считается готовым.
