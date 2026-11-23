# OpenCode Common — корпоративная база V2

База сохраняет штатные агенты, командные providers/models, permissions/policies,
семь MCP и `/problem-brief`. Она не подключает личные роли, routing, Goals,
Fish, review policies или discussion-map Samov. Личное дополнение необязательно.

## Состав и ограничения

- `AGENTS.md` — переносимые инженерные правила и корпоративные contracts.
  Для текущих требований используется XTracker; старый `MCP-KAITEN` сохранён.
- `opencode.jsonc`, package manifests, `git-offline`, permissions/permission-stats
  и `scripts/task-report.py` сохранены из предоставленного актуального `trf`.
  Git-защита — командная: её изменения требуют согласования с командой.
  Shell-hook не является sandbox для произвольного кода.
- MCP: `MCP-WIKI`, `MCP-KAITEN`, `MCP-XTRACKER`, `MCP-GITLAB`, `Chrome MCP`,
  `MCP-HUB`, `Figma-Framelink`. Их transports, enabled flags и переменные окружения
  не изменены. Наличие настройки не подтверждает соединение или авторизацию.
- Общие skills: `git-regression-rollback`, `task-summary-log`,
  `code-patterns-skill-generator`. Лог создаётся только по запросу; rollback skill
  сам по себе не разрешает Git-мутации. Checklist публикации skills сохранён.
- `cli.json` намеренно отсутствует: это mutable пользовательский файл. Сохраните
  существующий `@safwan-o/opencode-voice`, UI/volume/paste/sidebar и стандартные
  звуки OpenCode. Домашние звуки, voice-port старого seed и attention patches
  в этот пакет не входят.

## Личное дополнение

`OPENCODE_CONFIG` подключает соседний JSONC; он не меняет global root. Не задавайте
`OPENCODE_CONFIG_DIR` на `opencode-local`. В personal JSONC роли/команды описаны
явно, Markdown подключается через `{file:...}`, skills — явным путём.
Командная база не ссылается на personal-файлы и работает без них.

Обычные изменения config/skills/plugins подхватываются штатно; `/reload` — принудительное
обновление. Изменение окружения уже работающего server-процесса — отдельная операция
обслуживания, не причина перезапускать сервис при каждом изменении Markdown.
Не публикуйте resolved config, заголовки авторизации и private service files.

Приёмка и порядок переноса — в `../INSTALL.md`. Архивные инструкции
`opencode-local/update-2026-11-16/` не являются инструкцией новой установки.
