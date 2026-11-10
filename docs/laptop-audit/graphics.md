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

Это исходная stable-основа до последующего выбора пользователя, не версии
установленного Lenovo. Default NVIDIA module выбирает `stable`; в этом stable
snapshot переключение только на `latest` не меняет версию. Ниже описан уже
согласованный переход Lenovo на релизную графику из unstable, без обновления lock.

## Согласовано: свежие релизные пакеты только для Lenovo

Пользователь выбрал ядро, NVIDIA, Mesa 64/32-bit и firmware из unstable, остальные
источники системы остаются прежними. [Модуль](../../hosts/laptop/graphics.nix)
выбирает `linuxPackages_latest` и `config.boot.kernelPackages.nvidiaPackages.latest`:
драйвер собирается для выбранного ядра, а не для default kernel другой ветки.
Для Mesa явно выбраны обе архитектуры из одного snapshot, включая Steam support.

`flake.nix` передаёт отдельный `pkgsGraphics` с `allowUnfree = true` только Lenovo.
Это требуется для evaluation NVIDIA; обычный shared `pkgsUnstable` и другие hosts
не меняются. Локальный NixOS overlay заменяет **только** `linux-firmware`:
`enableRedistributableFirmware` и остальные firmware definitions сохранены,
второй конфликтующий пакет не добавляется. HM package sets не переопределяются.

| Пакет                       | Выбранный текущим lock unstable |
| --------------------------- | ------------------------------- |
| Kernel latest               | 7.2.11                          |
| NVIDIA latest / open module | 615.78.08                       |
| Mesa 64-bit / 32-bit        | 26.2.5 / 26.2.5                 |
| linux-firmware              | 20260916                        |

Root unstable revision: `f3a77a0c9b182bf55b71c8f22f99725f38b69a3e`.
Номера в конфиге не закреплены; при обновлении input и последующем применении
NixOS пакеты следуют выбранным aliases. Это **не** фоновый автоапдейтер и не
обновление inputs в этом шаге. NixOS modules по-прежнему из stable input, поэтому
совместимость их логики с новыми пакетами тоже требует review при обновлениях.

Перед решением сверены HTTP-исходники свежих stable
`c56a87d8e41ce69bd2af57eb35dcc117a9dfca33` и unstable
`4fe25e12eb9f4c744966dd3de5a05246cf098601`:

| Пакет          | Свежий stable | Свежий unstable |
| -------------- | ------------- | --------------- |
| Kernel latest  | 7.3.1         | 7.3.1           |
| Mesa           | 26.1.8        | 26.2.6          |
| NVIDIA latest  | 595.71.05     | 615.78.08       |
| linux-firmware | 20261019      | 20261019        |

Источники unstable: [kernel aliases](https://github.com/NixOS/nixpkgs/blob/4fe25e12eb9f4c744966dd3de5a05246cf098601/pkgs/top-level/linux-kernels.nix),
[kernel versions](https://github.com/NixOS/nixpkgs/blob/4fe25e12eb9f4c744966dd3de5a05246cf098601/pkgs/os-specific/linux/kernel/kernels-org.json),
[Mesa](https://github.com/NixOS/nixpkgs/blob/4fe25e12eb9f4c744966dd3de5a05246cf098601/pkgs/development/libraries/mesa/common.nix),
[NVIDIA](https://github.com/NixOS/nixpkgs/blob/4fe25e12eb9f4c744966dd3de5a05246cf098601/pkgs/os-specific/linux/nvidia-x11/default.nix),
[firmware](https://github.com/NixOS/nixpkgs/blob/4fe25e12eb9f4c744966dd3de5a05246cf098601/pkgs/by-name/li/linux-firmware/package.nix).
`latest` у NVIDIA выбирает старшую из production/new_feature, а beta добавляется
через отдельный `bleeding_edge`. Testing/RC kernel, beta и git snapshots не выбраны.

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

Оснований заранее добавлять `xe.force_probe`, `i915.force_probe` или blacklist i915
по этому проходу **не найдено**. Для самой базовой поддержки unstable не требовался;
новый стек выбран отдельно по пожеланию свежести. Фактическое связывание устройства
с Xe и аппаратное ускорение остаются живой проверкой.

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

## Выбранный PRIME offload и оставшиеся проверки Lenovo

Пользователь выбрал PRIME render offload: рабочий стол на Intel, NVIDIA по
требованию для выбранных приложений. **Весь Steam на NVIDIA не переводить**.
Live inventory подтвердил Intel `00:02.0` (`xe`) и NVIDIA `02:00.0` (`nouveau`);
единственный connected connector — Intel `card0-eDP-1`, пользователь использует
только встроенный экран. В `graphics.nix` заданы IDs `PCI:0:2:0`/`PCI:2:0:0`,
offload и штатная команда `nvidia-offload`, без глобальных GPU variables или
изменения Steam package. Для отдельной игры Launch Options
`nvidia-offload %command%` задаются один раз в Steam; это не декларативное управление
per-game preferences. Автоматические per-app обёртки пока не добавляются.

Offload даёт возможность не использовать NVIDIA для обычного desktop, но не
доказывает RTD3 или экономию: результат зависит от драйвера, подключённых экранов,
клиентов GPU и firmware. RTD3/finegrained и suspend/hibernate policy пока не менялись.
MUX не переключали; внешний экран и порты с NVIDIA driver остаются непроверенными.

Declaration fixtures проверяют выбор aliases/архитектур, только одну firmware
подмену, PRIME IDs/offload command и отсутствие Steam/global GPU overrides;
power-management settings пока не меняются. Отдельный
[test-graphics.nix](../../hosts/laptop/test-graphics.nix) проверяет выбранные
merged NixOS attributes, соответствие package paths unstable snapshot, evaluation
NVIDIA/open derivations, один linux-firmware input при сохранении SOF/regdb и
неизменённые Acer/desktop firmware. Это не полная evaluation всех attributes или
assertions, не реализация derivations и не проверка сборки firmware environment.

Live USB inventory получен от пользователя. Полный NixOS build, итоговый kernel
config, загрузка firmware установленной системы, Wayland/offload/RTD3 с NVIDIA,
suspend/hibernate или внешние порты не проверены.
Тесты остаются в [едином checklist](lenovo-checklist.md), новых acceptance-списков
нет. **Сейчас ничего не применять:** install guard сохранён; вместо disk placeholder
задан наблюдавшийся путь SSD, который нужно повторно сверить перед стиранием.
Graphics change в будущем требует NixOS activation только Lenovo, после аппаратной
проверки и разрешения блокеров; не применять его профиль на Acer. HM switch не
обновляет ядро и системные graphics drivers. Документация activation не требует.
