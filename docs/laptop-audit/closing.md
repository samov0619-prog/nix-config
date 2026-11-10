# Итог ограниченного source-прохода — 10.11.2026

[Каталог](README.md) · [Решения и evidence](feedback.md) · [Lenovo checklist](lenovo-checklist.md)

## Результат независимой сверки

Отдельный read-only reviewer получил цель, краткий список сделанного, ссылки
на документы и локальный ledger `laptop-audit:` commits, без переписки и private
continuation plan. Проверенная граница — `cdf40c9`; первые inventory commits —
`ea56e3c` / `a2d1767`. Он не менял файлы и не запускал тесты, Nix evaluation,
сборки, сеть, UI или hardware operations.

В просмотренном коде **новых доказанных существенных регрессий не найдено**.
Reviewer считает возможным завершить текущий ограниченный source-проход при явном
статусе known issue Tofi и пробелов покрытия. Это не полный аудит каждого пакета,
не независимое повторение всех прежних проверок и не допуск Lenovo к установке.
Исходный широкий план этим не объявляется выполненным.

## Что охвачено

- Карта imports/компонентов и выбранные эффективные декларации NixOS/HM.
- Minecraft lifecycle/readiness и guards полного backup mirror; настоящие
  Java/world/Drive/restore остаются интеграционными проверками.
- Изолированная Lenovo заготовка: storage/retention/bootstrap/graphics/PPD,
  отдельные outputs и сохранённые guards, без переноса аппаратных IDs Acer.
- Shared CLI/Mason prerequisites и unmanaged Fish environment; принятые
  приложения, темы, запуск TUI/XDG, Polkit/portals, сеть и audio baseline.
- Исправления screenshot/dictation/passmenu, media keys, FileManager1,
  Waybar disk status, Yazi archives и оставшиеся panel/menu helpers.

Это категории выполненной работы, а не обещание полного runtime-покрытия.
Конкретные fixture/evaluation/installed/user-acceptance границы — в тематических
документах и [журнале](feedback.md). Пользователь сообщил об успешном HM switch
после `cdf40c9`; rendering/update-state панели этим отдельно не подтверждён.

## Что остаётся открытым

1. **Known source issue Tofi:** `uwsm app -- $(tofi-drun)` разбивает сложные
   quoted Exec arguments. Воспроизведено на fixture; затронутого установленного
   приложения при прежней ограниченной проверке не нашли. Launcher не исправлен,
   полного desktop-entry contract нет. Это не hardware-only gap. Условие возврата:
   отдельное решение о фиксе или конкретный сбой запуска с такими аргументами.
   [Evidence](feedback.md#tofi-и-открытие-текстовых-файлов-ограниченная-проверка).
2. **Остатки исходного широкого плана:** полный per-package/upstream provenance,
   полный startup/runtime-периметр и сверка mutable state/активных поколений.
   Они не закрыты выборочными source-проверками; private/secret state намеренно
   не исследовался. Дальнейшую глубину этой работы согласовывать отдельно,
   а не продлевать текущий проход бесконечным повторением принятых решений.
3. **Установка Lenovo заблокирована:** hardware/PRIME inventory, целевой диск
   `REPLACE_ME`, окончательная graphics/power policy и согласованное переименование
   Acer → laptop-old / Lenovo → laptop остаются впереди. Failing assertion сохранён.
   Full Lenovo build и patched Waybar binary не подтверждены Acer switch.
4. **Живая приёмка:** девять крупных блоков в едином checklist остаются открытыми.
   Сон/hibernate проверять до основных данных; реальные устройства, Pi,
   перенесённые browser/editor state, Minecraft/backup/restore не заменяются fixtures.
5. **Отдельные решения:** автоматический MTP, fingerprint/PAM и возможная замена
   резервного VPN-клиента не реализуются молча. Согласованные ext4/swap48/no-zram,
   GC10/10, bootstrap и retained applications не пересматриваются без новых оснований.

## Следующая граница

1. Решить, исправлять ли known Tofi issue отдельно до аппаратного этапа или явно
   сохранять его открытым. Без нового решения в этом closing-шаге launcher не менять.
2. На самом Lenovo согласовать read-only hardware inventory, затем завершать
   host-specific настройки и передачу имён. Это не разрешение запускать inventory,
   builds, rename, Disko или installation сейчас.
3. После снятия guards пользователь проверяет/применяет конечные outputs и
   проходит существующий checklist; до этого Lenovo draft на Acer не применять.

Этот closing-шаг меняет только документацию: NixOS/HM activation не требуется.
