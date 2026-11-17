# R3: командный выбор источника, личный review-workflow

**Статус: `not-verified-in-wilde`.** Сохранено до пользовательской обкатки.
Лёгкие source/fixture-проверки пройдены; живая модельная, Mac/native и MCP-приёмка
ещё не выполнена. Сам факт применения R2 или создания коммита её не заменяет.

Текущий артефакт: `~/Downloads/opencode-mac-update-2026-11-16-r3.patch`.
Это **инкрементальный Git-патч поверх применённого R2**. Пользователь сообщил,
что R2 применён; откатывать его или повторять R1/R2 не нужно.
Инструкция и краткое объяснение — [`INSTALL.md`](INSTALL.md).

## Ровно три доработки

1. Учёт ТЗ: независимый выбор и проверка источника в командном AGENTS.
2. Качество рассуждений: полная проверка гипотез/контрдоказательств вместо выдачи
   предположения за установленный blocker; личные правила анализа ревью.
3. Проверка более простого подхода перед переусложнением; личные Goals and Approach.

Роль `review` одна. `review-analysis.md` содержит общие критерии для обычного ревью
и этой роли; `review-system.md` добавляет ограничения отдельного read-only reviewer.
Два policy-файла не означают двух агентов. Delegated review — существующий способ
запуска роли, Chrome audit — существующий workflow, не четвёртая доработка.

## Разделение слоёв

| Слой | Содержание |
| --- | --- |
| `opencode/AGENTS.md` | Только новый **Requirements Sources**: поиск источника задачи/ТЗ, связь с target, применимость, ревизия, доступ и scoped exceptions |
| `opencode-local/AGENTS-personal.md` | Личные review-workflows и Goals and Approach; уже подключён существующим personal JSONC |
| `opencode-local/review-analysis.md`, `review-system.md` | Личные policies анализа и delegated read-only выполнения |
| `opencode-local/commands/delegated-review*.md`, `agents/review.md` | Личные templates и reviewer; прямое чтение личных policy-путей |
| Три прежних симлинка в `opencode/commands/` и `opencode/agents/` | Только native discovery; сохраняются без пересоздания |

В новом командном разделе нет имён личных файлов/команд, routing/recovery,
Chrome-аудита или зависимости от личного reviewer. Он должен работать с любым
личным setup, включая отсутствие наших workflows. Остальные командные разделы
сохраняют побайтную исходную базу. Личный файл сохраняет базу вне двух additions:
Goals and Approach и Review Workflows. Goals не изменены относительно R2.

R3 удаляет только два ошибочно добавленных R2 командных policy-симлинка:
`opencode/review-analysis.md` и `opencode/review-system.md`. Сами policies остаются
обычными файлами на Mac в `opencode-local`. Сам reviewer и до R3 был физически
в personal: ошибка состояла в его policy-путях и общем AGENTS, а не в симлинках
как механизме. Одновременное размещение агента и policy не требуется OpenCode.

## Исходники и перенос

Это **source overlay**, не папка для копирования на Mac. Personal analysis/wrapper
и Chrome-template здесь связаны с общими исходниками Nix-репозитория; при экспорте
они материализованы в обычные личные файлы. Code-review-template — обычный Mac
source: отличается от общей команды только прямым путём к личному analysis.
Домашние policy-пути, Nix settings и поведение R3 не меняет.

Командные discovery-ссылки:

| Путь в `opencode/` | Цель |
| --- | --- |
| `commands/delegated-review.md` | `../../opencode-local/commands/delegated-review.md` |
| `commands/delegated-review-chrome.md` | `../../opencode-local/commands/delegated-review-chrome.md` |
| `agents/review.md` | `../../opencode-local/agents/review.md` |

JSON/CLI config, providers/MCP, plugins, аудио, auth, `.git`, permissions,
`OPENCODE_CONFIG` и `/problem-brief` не меняются. Личные файлы и discovery-ссылки
не включать автоматически в будущий командный коммит: из наших additions туда
относится только независимый **Requirements Sources**.

Исходная база содержания: `/home/samov/Downloads/trf.zip`, SHA256
`efce1363dcbd510497649457f285f9df9c0fc011ec23eeb68b91eacc53376b4a`.
База **патча R3** — эта база с тремя живыми discovery-ссылками и применённым R2,
SHA256 R2 `093cc0e44fc527c472980063270b8a3d6937a0c98f2b9ee55024bab2b1f981b3`.
ZIP и старый `macos/opencode/` seed не изменены.

## Проверки и продолжение

`tests/test_review_requirements.mjs` проверяет source-only командный AGENTS,
личные пути, сохранность reviewer frontmatter, links и отличие Mac-template
только policy-location. `tests/test_goal_approach.mjs` проверяет неизменные Goals
и исходную personal-базу вне additions. Это guards, не тесты поведения модели.
Сценарии source/model acceptance —
[`../../tests/fixtures/review-requirements/EVALUATION.md`](../../tests/fixtures/review-requirements/EVALUATION.md).

Проверки инкрементального apply/reverse, ограничения и SHA256 —
[`../../BENCHMARK.md`](../../BENCHMARK.md). Prettier недоступен; замена не установлена.
Model/MCP-приёмка и native discovery на Mac остаются невыполненными. После review
пользователь применяет R3 по INSTALL и выполняет `/reload`; агент ничего не применяет.
