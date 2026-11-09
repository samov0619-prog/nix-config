# Lenovo: основа графики до аппаратной проверки

[Каталог](README.md) · [Решения](feedback.md) · Срез **09.11.2026**.

Цель — проверить наличие поддержки **Core Ultra 7 356H / Panther Lake + RTX 5060
Laptop**, а не подобрать PCI Bus IDs или объявить ThinkBook проверенным без запуска.
CPU подтверждён пользователем по BIOS; фактические GPU IDs и разводка дисплеев
ещё не сняты. Windows setup для этой проверки не требуется.

## Что даёт текущий lock

Root input `nixpkgs`: `0ad6f47ea4fe188f4bc8f0380f93ae8523337c6c`.
Узкая offline evaluation package attributes, без сборок и import-from-derivation:

| Компонент                           | Версия              |
| ----------------------------------- | ------------------- |
| Default `linuxPackages.kernel`      | 6.18.38             |
| Mesa                                | 26.1.4              |
| linux-firmware                      | 20260622            |
| NVIDIA stable / production / latest | Все три — 595.71.05 |

Это доступные пакеты, не версии установленного Lenovo и не полный merged NixOS
config. Draft не переопределяет kernelPackages; NVIDIA module по умолчанию выбирает
ветку `stable` из `boot.kernelPackages.nvidiaPackages`. Выбор `latest` сейчас сам
по себе не даёт другую версию. Обновлений inputs или выбора новой ветки не было.

## Intel: Xe, не перенос i915-настроек Acer

- [Intel Xe support table](https://dgpu-docs.intel.com/overview/supported-hardware/xe-driver-gpus.html)
  относит Panther Lake к Xe3. Для Intel Graphics и Arc B370/B390 full support
  указан как Ubuntu 25.10+ / kernel 6.17. Это guidance Intel, не сертификация NixOS.
- В [upstream Linux v6.18 `xe_pci.c`](https://github.com/torvalds/linux/blob/v6.18/drivers/gpu/drm/xe/xe_pci.c)
  есть `ptl_desc`, `PLATFORM(PANTHERLAKE)` и `INTEL_PTL_IDS`; у этого descriptor
  **нет** `require_force_probe = true`. Это сверка базовой ветки 6.18, не полный
  аудит всех downstream patches 6.18.38 или итогового kernel `.config`.
- [Mesa 25.2 release notes](https://docs.mesa3d.org/relnotes/25.2.0.html) уже
  содержат `anv: Set Xe3 as supported` и включение PTL IDs без `INTEL_FORCE_PROBE`.
  Locked Mesa 26.1.4 новее этой точки; пакет включает Intel ANV и Iris.
- `hardware.enableRedistributableFirmware = true` в draft подключает в NixOS
  полный `linux-firmware`. Наличие всех нужных конкретной ревизии firmware blobs
  и успешную загрузку GuC/HuC/DMC здесь не проверяли.

Оснований заранее добавлять `xe.force_probe`, `i915.force_probe`, blacklist i915,
новое ядро или Mesa из unstable по этому проходу **не найдено**. Фактическое
связывание устройства с Xe и аппаратное ускорение остаются живой проверкой.

## NVIDIA: поддержка модели есть, режим работы ещё не выбран

[Supported chips именно 595.71.05](https://us.download.nvidia.com/XFree86/Linux-x86_64/595.71.05/README/supportedchips.html)
явно перечисляет **RTX 5060 Laptop GPU**. IDs в таблице драйвера не являются
инвентаризацией этого экземпляра и не определяют PRIME Bus IDs.
[Документация той же версии](https://us.download.nvidia.com/XFree86/Linux-x86_64/595.71.05/README/kernel_open.html)
требует open kernel modules для Blackwell и новее. Поэтому имеющийся
`hardware.nvidia.open = true` соответствует требованию; это NVIDIA driver,
**не Nouveau**, userspace от этого не становится открытым.

В [pinned NixOS NVIDIA module](https://github.com/NixOS/nixpkgs/blob/0ad6f47ea4fe188f4bc8f0380f93ae8523337c6c/nixos/modules/hardware/video/nvidia.nix)
есть важное отличие от старых suspend-рецептов: `kernelSuspendNotifier` по
умолчанию true для open + NVIDIA >=595, **но** параметр модуля для этого пути
добавляется только вместе с `powerManagement.enable = true`. Последняя опция
в draft не включена. Не считать notifier/preservation уже настроенными и не
добавлять параллельно старые suspend/resume services вслепую. RTD3/finegrained,
Dynamic Boost и работоспособность hibernate также не следуют из версии драйвера.

## Что ещё нужно решить на самом Lenovo

Предварительная рекомендация, **не выбранная policy**: если разводка дисплеев
позволяет, рабочий стол на Intel, NVIDIA по требованию для тяжёлых приложений.
Это даёт возможность выключать dGPU в idle, но результат зависит от подключённых
экранов, клиентов GPU и firmware. Постоянный desktop на NVIDIA — другой компромисс
по питанию и копированию кадров; выбирать его за пользователя пока рано.

Следующий аппаратный шаг — отдельно согласованный read-only Live USB inventory:
PCI devices/Bus IDs/драйверы, DRM connectors для встроенного и нужных внешних
экранов, доступные firmware/MUX режимы. Не переключать MUX/BIOS ради инвентаризации,
не монтировать SSD на запись и не запускать установку. Затем выбрать режим и
проверить его уже с согласованным NVIDIA stack на установленной системе.

Ни Live USB inventory, ни полный NixOS build, итоговый kernel config, загрузка
firmware, Wayland/offload/RTD3, suspend/hibernate или внешние порты в этом проходе
не проверены. Тесты остаются в [едином checklist](lenovo-checklist.md), новых
параллельных acceptance-списков нет. **Никакой Nix activation сейчас не нужна:**
изменения только документальные, install guard и disk placeholder сохранены.
