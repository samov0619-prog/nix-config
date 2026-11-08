# Питание и температуры: Acer → Lenovo

[Каталог](README.md) · [Решения](feedback.md) · [Живые проверки](lenovo-checklist.md)

Ограниченный source/runtime срез **09.11.2026**. Настройки, службы и частоты не
менялись; нагрузочные тесты, измерения расхода батареи и Lenovo не проверялись.

## Что установлено для Acer

- В [host config](../../hosts/laptop/default.nix) явно заданы governor `performance`
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

- Не наследовать Acer `performance`; пользователь выбрал PPD (`power-profiles-daemon`)
  со штатным значком Waybar только для Lenovo, с обычным `balanced` и доступными
  `power-saver`/`performance` по потребности.
  Фактические профили и backend зависят от поддержки CPU/firmware/kernel.
- Не включать одновременно PPD, TLP и auto-cpufreq: pinned NixOS явно запрещает
  сочетание PPD с двумя остальными. Это не запрет на совместную работу PPD и thermald;
  пригодность последнего проверяется отдельно по платформе и её firmware tables.
- Не добавлять undervolt, ручные fan curves, отключение turbo и автоматические
  scripts AC/battery до базовой проверки. UI и автоматическое переключение профилей
  тоже отдельные решения, простое включение daemon их не специфицирует.
- В [Lenovo draft](../../hosts/laptop-next/default.nix) PPD включён; Acer host
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
Lenovo с PPD и Waybar, без применения. [Блокеры](../../hosts/laptop-next/README.md)
не сняты: не запускать установку/activation. Acer оставлен без изменений.
