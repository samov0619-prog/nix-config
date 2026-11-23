# R3: разделение командных и личных инструкций

`opencode-mac-update-2026-11-16-r3.patch` — **дополнительный патч поверх уже
применённого R2**, а не замена R2 и не патч поверх исходного `trf.zip`.
База R2: SHA256
`093cc0e44fc527c472980063270b8a3d6937a0c98f2b9ee55024bab2b1f981b3`.
R2 откатывать и повторно применять не нужно.

## Кратко: что было и что исправлено

R2 добавил выбор источника ТЗ, личные review-workflows, обновлённые команды/роль
и правило Goals and Approach. Ошибка разделения: общий `AGENTS.md` одновременно
описывал личный review-workflow и требовал policy через общий каталог.

После R3:

- `opencode/AGENTS.md`: только **Requirements Sources** — поиск задачи/ТЗ,
  проверка применимости/ревизии, уточнение неоднозначности и согласованное исключение.
  Никаких ссылок на personal review-файлы, команды или reviewer в новом разделе.
- `opencode-local/AGENTS-personal.md`: обычное/делегированное ревью и пассивный
  Chrome-аудит, а также сохранённые Goals and Approach и остальные личные правила.
- Analysis, delegated wrapper, команды и роль физически остаются в `opencode-local`.
  Роль и code-review-команда читают policy напрямую из `~/.config/opencode-local`.
- Две ссылки `opencode/review-analysis.md` и `opencode/review-system.md` удаляются.
  Их настоящие личные файлы **не удаляются**.
- Три существующие ссылки `opencode/commands/delegated-review*.md` и
  `opencode/agents/review.md` сохраняются. Это native discovery entrypoints:
  настоящие templates/роль уже в личном слое. Они не делают policy командной.
- JSON/CLI settings, providers/MCP, plugins, звуки, `.env`, auth, Git data,
  permissions и `/problem-brief` не меняются. Домашняя конфигурация не меняется R3.

Возможность симлинков не требует, чтобы агент и policy были в одном каталоге.
Ошибка была в выбранных инструкциях/адресах и границе слоёв, не в ограничении Git
или OpenCode. Командная политика выбора источника должна работать без личных файлов.

## Применение на Mac (Fish)

Предполагаются `~/.config/opencode`, соседний `opencode-local` и уже подключённый
через `OPENCODE_CONFIG` личный JSONC с `instructions` для `AGENTS-personal.md`.
При другом config root сначала сверить пути; R3 не меняет подключение конфигов.

1. Перенести **новый R3** на Mac и проверить без записи файлов:

   ```fish
   set update "$HOME/Downloads/Telegram Desktop/opencode-mac-update-2026-11-16-r3.patch"
   git -C ~/.config apply --stat $update
   git -C ~/.config apply --check $update
   ```

   При ошибке остановиться. Не использовать `--reject`, `--3way` или принудительное
   удаление: проверка ожидает именно состояние после R2, включая две его policy-ссылки.

2. Сохранить обе папки в приватный backup вне конфигов:

   ```fish
   set backup (mktemp -d "$HOME/opencode-before-r3.XXXXXX")
   cp -R ~/.config/opencode $backup/opencode
   cp -R ~/.config/opencode-local $backup/opencode-local
   ```

   Backup может содержать приватные данные; не публиковать и не коммитить его.

3. Применить и выполнить `/reload` в OpenCode:

   ```fish
   git -C ~/.config apply $update
   ```

   Git index/history не меняются, `ln -s` и перезапуск сервиса не нужны.

4. Проверить: общий `AGENTS.md` не упоминает `review-analysis`, `review-system`
   или `/delegated-review`; личные policy-файлы существуют; две общие policy-ссылки
   отсутствуют; три прежние ссылки команд/роли разрешаются в `opencode-local`.
   Отдельно согласовать модельную/MCP-приёмку по `acceptance/`: физические файлы
   и статические tests не доказывают соблюдение моделью.

5. При необходимости откатить **только R3**, если затронутые файлы после него
   не менялись; сначала обязательная проверка:

   ```fish
   git -C ~/.config apply --reverse --check $update
   git -C ~/.config apply --reverse $update
   ```

   При ошибке не продолжать откат; сравнить последующие правки с backup.
   Затем `/reload`. Обратный R3 возвращает R2, не исходный `trf.zip`.

Сборки, activation, установка зависимостей и коммиты агентом не выполнялись.
Живое Mac/model/MCP-поведение R3 ещё не проверено.
