# Пассивный аудит Chrome-MCP evidence

`/delegated-review-chrome [run/evidence]` просит отдельный read-only `review`
оценить, подтверждают ли сохранённые Chrome-MCP evidence заявленные результаты.
Это не новое browser-тестирование: браузер не открывается, действия не повторяются,
live-продукт не меняется. Модель роли наследуется от родителя.

Source of truth — `commands/delegated-review-chrome.md`: export/privacy boundary,
fingerprint, минимальный factual handoff, interventions и ограничения покрытия.
Секреты и лишняя переписка в пакет reviewer не попадают; недоступность механизма
не обходится самодельным экспортом или обычным code-review child.

Для живой проверки используйте отдельную current-session команду
`/browser-verification` через существующий `Chrome MCP`. Она не даёт права
автоматически запускать последующий независимый audit. Source/mock checks
не заменяют real browser/model acceptance на целевом Mac.
