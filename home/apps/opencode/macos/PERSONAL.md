# Личное дополнение Samov

Подключается через `OPENCODE_CONFIG` к `opencode.jsonc` этой папки. Nix на Mac
не нужен. При нестандартном XDG-пути экспортируйте пакет с соответствующим
`personalDirectory`; не копируйте личную папку в global root.

- Goals, Fish, общение, review workflow и новые Git keys `FBDC-<number>` — личные.
- `review` и `research` не закрепляют provider/model и наследуют модель родителя.
- `/delegated-review`, `/delegated-review-chrome`, `/task-analysis`,
  `/browser-verification` работают через явные JSONC definitions; последние две —
  в текущей сессии, без отдельного агента. Пассивный Chrome audit не запускает браузер.
- `discussion-map` вызывается вручную через `@discussion-map`, не рекламируется
  модели для автоматического вызова. `/problem-brief` принадлежит Common.
- Decision Support, `decision-check`, домашний todo/routing, корпоративные секреты
  и настройки CLI сюда не экспортируются.

`task-analysis.README.md` и `browser-verification.README.md` описывают новые команды.
Исторические acceptance artifacts `update-2026-11-16/` сохранены без изменений;
новая конфигурация не делает их автоматически прошедшими на 2.4.0.
