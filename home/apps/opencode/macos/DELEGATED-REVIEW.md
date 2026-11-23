# Делегированное ревью

`/delegated-review [scope]` остаётся в текущей сессии и запускает отдельный
read-only `review` только по явному запросу. Обычное «поревьюй» остаётся в текущем
потоке. Отдельная роль не закрепляет модель и наследует модель родителя.

Source of truth — `commands/delegated-review.md`, `review-analysis.md` и
`review-system.md` личного слоя. Они задают scope defaults, fingerprint,
requirements sources, factual handoff, bounded recovery и запрет рекурсивной
делегации. Недоступный reviewer/policy не заменяется молча другим агентом.
Review не разрешает правки, сборки, установку или коммит.

Корпоративный Common требует внешние требования именно выбранной задачи через
доступные XTracker/Wiki/GitLab источники. Нехватка доступа — ограничение покрытия,
а не доказанная ошибка кода. Новые Git keys Samov — `FBDC-<number>`.

Definitions находятся в personal `opencode.jsonc`, тексты подставляются без YAML
через `{file:...}`; Common discovery symlinks не нужны. Проверка регистрации и
реального model/agent поведения на Mac 2.4.0 остаётся частью `../INSTALL.md`.
