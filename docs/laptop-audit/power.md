# Питание и температуры: Acer → Lenovo

[Каталог](README.md) · [Решения](feedback.md) · [Живые проверки](lenovo-checklist.md)

Ограниченный source/runtime срез **09.11.2026**. Настройки, службы и частоты не
менялись; нагрузочные тесты, измерения расхода батареи и Lenovo не проверялись.

## Что установлено для Acer

- В [host config](../../hosts/laptop-old/default.nix) явно заданы governor `performance`
  и `services.thermald.enable = true`. Обе строки появились в `f7de937`
  (`create laptop host`); отдельного обоснования в этом изменении нет.
- Read-only runtime: Intel Core i5-6200U, `intel_pstate` в active mode,
  governor и energy-performance preference — `performance`; turbo разрешён.
  `cpufreq.service` — active/exited, `thermald.service` — active/running.
  Units PPD, TLP и auto-cpufreq отсутствуют. Это точечная проверка этих служб,
  не доказательство отсутствия любого другого механизма управления питанием.
- Наличие `performance` не означает постоянную загрузку CPU или невозможность idle.
  Но это приоритет производительности, а не сбалансированная battery policy.
  В active `intel_pstate` название `powersave` тоже не означает фиксацию минимальной
  частоты: его смысл отличается от generic CPUFreq governor с тем же именем.
- Текущий срез не доказывает перегрев, потерю автономности или пользу отключения
  thermald. Acer пока оставлен без изменений, как и согласованная logind policy
  игнорирования крышки и аппаратных кнопок.

## Почему недостаточно просто удалить governor

В pinned NixOS `powerManagement.cpuFreqGovernor` по умолчанию `null`: модуль не
навязывает governor через `cpupower`. Это **не** обещание режима `balanced` или
`powersave`: остаётся выбор ядра, firmware и других включённых компонентов.
Текущая Acer-настройка создаёт oneshot `cpufreq.service`, а не battery-aware daemon.

`thermald` решает другую задачу — температурное управление, включая ограничения
мощности. В pinned NixOS без собственного config он запускается с `--adaptive` и
использует доступные firmware/DPTF данные. Работающий процесс не доказывает, что
оптимально обработаны все датчики и ограничения платформы. Не переносить его на
Lenovo только потому, что там тоже Intel; не обходить CPUID check без диагностики.

## Выбранное направление Lenovo и открытые вопросы

### CPU подтверждён, поддержка thermald проверена по исходникам

Пользователь сообщил: **«в биос записан 356h»**. Это подтверждение CPU на самом
Lenovo, а не противоречивые карточки магазинов 356H/358H. По
[спецификации Intel](https://www.intel.com/content/www/us/en/products/sku/245532/intel-core-ultra-7-processor-356h-18m-cache-up-to-4-70-ghz/specifications.html)
это **Core Ultra 7 356H, Panther Lake**. Проходить первоначальную настройку
Windows или повторно собирать те же характеристики сейчас не требуется.

В root locked stable и проверенном свежем stable из
[package-source audit](package-sources.md) thermald имеет версию **2.5.11**.
[Upstream release notes этой версии](https://github.com/intel/thermal_daemon/blob/v2.5.11/README.txt)
указывают поддержку Panther Lake начиная с **2.5.9** и исправление пути DPTF для
Panther Lake в **2.5.10**. В
[таблице поддерживаемых CPU](https://github.com/intel/thermal_daemon/blob/v2.5.11/src/thd_engine.cpp)
есть family 6 / model `0xcc` с комментарием `Panther Lake L`.
**Обновление thermald ради поддержки семейства сейчас не требуется.**

Это source evidence о поддержке семейства, не измерение CPUID или эффективности
на конкретном ThinkBook. Тот же код проверяет sensors/cooling devices/thermal
zones и содержит blocklist для некоторых Lenovo с
`thinkpad_acpi/dytc_lapmode`; наличие этого интерфейса на ThinkBook не установлено.
Не делать вывод ни о необходимости службы, ни о её запрете только по бренду.

Открытый вопрос теперь — доступность firmware/DPTF и реальная польза thermald на
данном ноутбуке, **не неизвестная модель CPU**. Рекомендация: сохранить подготовленный
PPD, thermald пока не включать; в существующую живую проверку питания входит
проверка датчиков, firmware interfaces и журналов перед решением о службе.
Это не новое пользовательское решение включить или окончательно исключить её.
Проверка Linux возможна позже с Live USB без установки и изменения SSD; никакой
SSH через BIOS или предварительная настройка Windows для неё не нужны.

### Согласованный baseline

- Не наследовать Acer `performance`; пользователь выбрал PPD (`power-profiles-daemon`)
  со штатным значком Waybar только для Lenovo, с обычным `balanced` и доступными
  `power-saver`/`performance` по потребности.
  Фактические профили и backend зависят от поддержки CPU/firmware/kernel.
- Не включать одновременно PPD, TLP и auto-cpufreq: pinned NixOS явно запрещает
  сочетание PPD с двумя остальными. Это не запрет на совместную работу PPD и thermald;
  пригодность последнего проверяется отдельно по платформе и её firmware tables.
- Не добавлять undervolt, ручные fan curves, отключение turbo и автоматические
  scripts AC/battery до базовой проверки. Ручной UI Waybar подготовлен отдельно;
  автоматическое переключение профилей AC/battery не согласовано и не реализовано.
- В [Lenovo draft](../../hosts/laptop/default.nix) PPD включён; Acer host
  не импортируется. Thermald ещё не выбран. Реальные температура, throttling, CPU/GPU idle и
  батарея проверяются в существующем коротком checklist, а не новым списком.

## Источники и границы

- Pinned nixpkgs:
  [CPU frequency](https://github.com/NixOS/nixpkgs/blob/0ad6f47ea4fe188f4bc8f0380f93ae8523337c6c/nixos/modules/tasks/cpu-freq.nix),
  [thermald](https://github.com/NixOS/nixpkgs/blob/0ad6f47ea4fe188f4bc8f0380f93ae8523337c6c/nixos/modules/services/hardware/thermald.nix),
  [PPD](https://github.com/NixOS/nixpkgs/blob/0ad6f47ea4fe188f4bc8f0380f93ae8523337c6c/nixos/modules/services/hardware/power-profiles-daemon.nix).
- Механизм governor/EPP: [Linux intel_pstate](https://docs.kernel.org/admin-guide/pm/intel_pstate.html).
- Профили/backend: [PPD 0.30 API](https://upower.pages.freedesktop.org/power-profiles-daemon/gdbus-org.freedesktop.UPower.PowerProfiles.html).

Это не полный NixOS evaluation/build и не подтверждение совместимости Lenovo.
Первый audit-шаг менял только документацию; затем создана отдельная заготовка
Lenovo с PPD и Waybar, без применения. [Блокеры](../../hosts/laptop/README.md)
не сняты: не запускать установку/activation. Acer оставлен без изменений.
