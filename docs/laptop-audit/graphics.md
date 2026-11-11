# Lenovo: основа графики до аппаратной проверки

[Каталог](README.md) · [Решения](feedback.md) · Срез **09.11.2026**.

Цель — проверить наличие поддержки **Core Ultra 7 356H / Panther Lake + RTX 5060
Laptop**, а не подобрать PCI Bus IDs или объявить ThinkBook проверенным без запуска.
CPU подтверждён пользователем по BIOS; фактические GPU IDs и разводка дисплеев
на момент исходного среза ещё не были сняты; последующий live inventory приведён
ниже. Windows setup для этой проверки не требуется. Старые таблицы — исторические;
review фактического полного input update от 10.11 и финальный результат 11.11
приведены в конце. Упоминания сохранённого guard ниже описывают прежние этапы.

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

Первоначально пользователь выбрал ядро, NVIDIA, Mesa 64/32-bit и firmware из
unstable. После installed ABI failure согласована **Mesa-only коррекция**:
Mesa обеих архитектур из stable host package set, остальные компоненты по-прежнему
из unstable, без lock update (подробности и границы проверки в конце этого файла).
Остальные источники системы остаются прежними. [Модуль](../../hosts/laptop/graphics.nix)
выбирает `linuxPackages_latest` и `config.boot.kernelPackages.nvidiaPackages.latest`:
драйвер собирается для выбранного ядра, а не для default kernel другой ветки.
Для Mesa явно выбраны обе архитектуры из того же stable snapshot, что userspace,
включая Steam support. Для dlopened graphics drivers важна libc вызывающих
приложений, а не только согласованность двух архитектур Mesa друг с другом.

`flake.nix` передаёт отдельный `pkgsGraphics` с `allowUnfree = true` только Lenovo.
Это требуется для evaluation NVIDIA; обычный shared `pkgsUnstable` и другие hosts
не меняются. Локальный NixOS overlay заменяет **только** `linux-firmware`:
`enableRedistributableFirmware` и остальные firmware definitions сохранены,
второй конфликтующий пакет не добавляется. HM package sets не переопределяются.

Исторический снимок первоначального решения, до полного input update и Mesa fix:

| Пакет                       | Первоначально выбранный unstable |
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

## 10.11: начальный review фактического полного input update

Пользователь обновил inputs; на этапе начального review новый `flake.lock` ещё не
был закоммичен и доставлен на Lenovo. Узкая offline evaluation package attributes
без builds/IFD подтвердила:

| Компонент       | Версия обновлённого lock |
| --------------- | ----------------------- |
| Kernel latest   | 7.3.1                   |
| NVIDIA latest   | 615.78.08               |
| Mesa            | 26.2.6                  |
| linux-firmware  | 20261019                |
| Stable Hyprland | 0.55.4                  |
| Stable Waybar   | 0.15.0                  |
| Stable Blueman  | 2.4.6                   |
| Stable Kitty    | 0.49.1                  |
| Stable gh       | 2.103.3                 |
| Stable Node     | 26.13.0                 |

Root stable: `ac588ef1c914865dad517b337ea0eb9694a4021c`;
unstable: `4fe25e12eb9f4c744966dd3de5a05246cf098601`.
Kitty новее требуемой 0.47.1, но live F11 остаётся в checklist.
Unstable Amnezia всё ещё `5.0.3.0`: оснований автоматически убирать рабочий локальный
`5.0.1.5` override нет. OpenCode по-прежнему pinned на `v2.1.4`; обновление остальных
inputs не меняет эту upstream-версию и не доказывает совместимость patches.

`hosts/laptop/test-draft.nix` прошёл на обновлённых inputs. Selected merged
`test-graphics.nix` сначала был остановлен по таймаутам 20 и 90 s. После bounded
диагностики и восстановления кешированных sources повторная проверка завершилась
успешно в прежнем лимите 90 s: обе Mesa, NVIDIA/open derivation, native power policy,
единственный linux-firmware, остальные firmware inputs и изоляция хостов проверены.
Это evaluation, не сборки или установленные graphics/resume. Полные configuration
evaluation/builds ещё не завершены; guard сохранён.

### Уточнение power-management contracts именно NVIDIA 615

Сверена документация выбранного релиза:
[suspend/hibernate](https://us.download.nvidia.com/XFree86/Linux-x86_64/615.78.08/README/powermanagement.html)
и [RTD3](https://us.download.nvidia.com/XFree86/Linux-x86_64/615.78.08/README/dynamicpowermanagement.html).

- Для поддерживаемых Ampere+ notebook configurations driver default `0x03`
  означает fine-grained RTD3; runtime PM GPU function 0 также включается по умолчанию.
  Blackwell относится к более новым поколениям, но поддержку ACPI и реальный idle
  конкретного Lenovo этим не доказываем. `finegrained = false` в NixOS означает
  отсутствие явного `0x02`/дополнительных правил, а не принудительное отключение RTD3.
- NVIDIA описывает автоматическое сохранение видеопамяти при suspend/hibernate
  для open modules. Раздел старых systemd `/proc` hooks адресован прежде всего
  proprietary modules и соответствующему способу сохранения; не переносить его
  автоматически на выбранный open driver. Сохранение может расходовать RAM/tmpfs;
  при проблемах нужны проверка фактического backing store и свободного места,
  не слепой выбор `/tmp` или `/run`.
- Обновлённый stable NixOS module по-прежнему добавляет
  `NVreg_UseKernelSuspendNotifiers=1` и `NVreg_PreserveVideoMemoryAllocations=1`
  только при явном `powerManagement.enable`. Отсутствие этих явных параметров
  само по себе не устанавливает внутренние defaults драйвера.

Пользователь согласовал baseline: начать со штатного поведения 615/open без
принудительных RTD3/S0ix/deep, дополнительных suspend units и Dynamic Boost.
Комментарии и declaration checks фиксируют отсутствие этих overrides; это не
изменение внутренних defaults драйвера и не проверка resume. Обновлённый merged
`test-graphics.nix` впоследствии завершился успешно, отдельно от fixtures.
Согласованные ignore lid/power/suspend/hibernate keys и PPD не пересматриваются.
Проверки idle, offload, suspend/hibernate и внешних экранов остаются в одном
Lenovo checklist; до их выполнения нельзя обещать автономность или надёжный сон.

### Узкие compatibility checks после согласования baseline

- Обновлённый `test-draft.nix` прошёл, включая отсутствие дополнительных GPU
  power overrides. Новый `test-disko.nix` прошёл через настоящий config generator
  locked Disko с небольшими option fixtures: ext4 `/`, vfat `/boot`, один
  unencrypted swap 48 GiB и тот же `disk-main-swap` для resume. Скрипты Disko не
  собирались и не запускались; это не проверка фактических разделов или загрузки.
- Source derivations Waybar `0.15.0`, Blueman `2.4.6` и Yazi compress `0.6`
  совпадают до/после update. Маленький production Waybar cycle-helper unit test
  прошёл; повторный patch dry-run по точному store source пропущен, поскольку тот
  не realized. Прежняя проверка patch не заменяет сборку с новыми dependencies.
- Lock entries OpenCode и его собственного nixpkgs не изменились. Hermes module
  по-прежнему не импортирован; xremap не включён на Lenovo. Полный runtime/PTY
  OpenCode не запускался; обновившиеся shared runtime libraries этим не проверены.
- Derivations обновлённого Freesm, локальной Amnezia `5.0.1.5` и выбранные package
  attributes Blueman evaluated без builds/IFD. У Blueman сохраняются Polkit input,
  `--enable-polkit` и install-check. Это package-level checks, не полный merged
  NixOS/HM evaluation и не доказательство успешной компиляции/живого UI.

После отдельного разрешения выполнены последовательные evaluation до 90 s:

- NixOS assertions: единственный отказ — намеренный Lenovo install guard; других
  failed assertions нет. Это не полное evaluation `system.build.toplevel.drvPath`.
- Selected merged graphics: успешно после описанной выше диагностики.
- Дополнительная узкая merged-проверка native NVIDIA settings и storage/resume
  также прошла: ext4/vfat, один unencrypted swap, правильный resume target.
- Lenovo HM `activationPackage.drvPath`: два запуска остановлены по timeout 90 s;
  короткая debug-диагностика показала восстановление
  собственного nixpkgs input OpenCode из локального Git-кеша после GC; затем этот
  source полностью появился в store. Последующая диагностика показывает дальнейшее
  evaluation package graph, но не устанавливает единственную причину полной задержки.
  После отдельного разрешения повторный offline запуск с запрещённым IFD и лимитом
  **180 s завершился успешно**, вернув Home Manager generation `.drv`.
  Штатный OpenCode quota reminder остался предупреждением, не ошибкой.
  Это завершённая evaluation, не скачивание/сборка closure, activation или live UI.

На этом этапе следующим gate были финальный install review и согласованное снятие
install guard; их результат приведён ниже.
Nix builds не запускались; дальнейшие ресурсоёмкие проверки требуют отдельного
разрешения. Prettier недоступен: Markdown layout сохранялся,
другой formatter не подставлялся. Nix-файлы обработаны nixfmt 1.3.1.

### 11.11: финальный configuration review и снятие guard

Проверены конкретная NixOS/HM композиция Lenovo, EFI GRUB, Disko ext4/48 GiB swap
и resume target, bootstrap login/sudo, native NVIDIA power policy и отсутствие
неподготовленного Minecraft instance/backup. По согласованию с пользователем удалён
только намеренный failing install assertion; graphics/runtime policy не менялась.
Fixtures теперь требуют отсутствия guard, а merged graphics test — истинности всех
NixOS assertions вместо прежнего ожидаемого отказа. Он также явно проверяет отсутствие
принудительного `NVreg_EnableS0ixPowerManagement`.

После изменения повторно прошли `test-draft.nix`, `test-disko.nix` и
`test-graphics.nix`. NixOS `system.build.toplevel.drvPath` evaluation завершилась
offline с запрещённым IFD в лимите 90 s, без сборок. Ранее завершённая полная HM
activation derivation evaluation остаётся применимой: HM sources/lock не менялись.

Это готовность конфигурации по evaluation, не успешно собранная или установленная
система. До основных downloads нужно согласовать store/build порядок для Lenovo:
live writable store находится в RAM и не считается достаточным для обеих closures.
До Disko нужны доставка reviewed commit, повторная сверка SSD и отдельное согласие
на стирание. После reboot понадобится локальный вход: live SSH не переносится,
SSH server в target выключен, standalone HM применяется отдельно.

### 11.11: installed Mesa/userspace ABI failure и согласованная коррекция

Пользователь сообщил об успешных NixOS installation, SSD boot и полной standalone
HM activation. Первый графический вход через UWSM вернулся к tty login. В
предоставленном журнале Hyprland 0.55.4 сначала виден Mesa loader failure:
stable `libc.so.6` из glibc 2.42 не предоставляет `GLIBC_2.43`, требуемую
unstable Mesa 26.2.6 (`libgallium`). Затем `CBackend::create() failed` и abort
в `CCompositor::initServer`. `Couldn't waitpid` — последствие падения, не причина.

Узкая offline evaluation без IFD подтвердила текущие версии: stable Mesa 26.1.8 /
glibc 2.42 и unstable Mesa 26.2.6 / glibc 2.44. Даже если конкретная библиотека
требует только символ 2.43, stable 2.42 уже недостаточно. Прежние declaration
fixtures успешно подтверждали выбранные inputs, но не проверяли ELF loading
драйвера в процессе stable compositor; поэтому прежняя evaluation не исключала
этот runtime конфликт. Базовая поддержка Xe3 уже есть в stable Mesa (см. выше):
unstable Mesa была выбрана ради свежести, а не доказанной нехватки hardware support.

По явному решению пользователя меняется только `hardware.graphics.package` и
`package32` на `pkgs.mesa` / `pkgs.pkgsi686Linux.mesa`. Kernel 7.3.1, NVIDIA 615/open,
firmware 20261019, PRIME/power policy, Hyprland/HM package sets и flake.lock не меняются.
Нет глобального LD_LIBRARY_PATH, подмены glibc, wrapper-а нового loader или
перехода всего userspace на unstable. Другие хосты не затрагиваются.

`test-draft.nix` сохраняет разные stable/unstable Mesa sentinels и требует stable
выбор. Новый узкий `test-mesa.nix` проверяет реальные merged package drvPaths для
64/32-bit и совпадение их build libc drvPaths с host userspace той же архитектуры;
он повторно используется полным `test-graphics.nix`. Это регрессия деклараций,
не проверка ELF loader, полного транзитивного ABI или реального GPU.
Оба узких теста прошли offline без IFD: Mesa 26.1.8 и glibc 2.42 обеих архитектур.
Nix-файлы отформатированы nixfmt 1.3.1; `git diff --check` прошёл. Полный merged
graphics/NVIDIA check в этом исправлении не перезапускался: ранее требовал
дорогой evaluation. Builds/activation/live startup не выполнялись агентом.
Markdown formatter Prettier недоступен; другой formatter не подставлялся.

Пользователь применяет только NixOS `laptop` после Git review/delivery:

```fish
cd /etc/nixos
sudo nixos-rebuild switch --flake .#laptop --no-update-lock-file
```

HM switch для Mesa fix не требуется. После успешного switch повторить свежий
Hyprland login и проверить реальное аппаратное ускорение/offload; не считать их
успешными по одному отсутствию прежнего символа в конфиге. Если потребуется
отдельная build-only проверка, минимальный output —
`nix build --no-update-lock-file --out-link result-mesa .#nixosConfigurations.laptop.config.system.build.toplevel`.
Не выполнять эти builds на Acer и не обновлять lock ради доставки.

В тех же supplied logs есть `Invalid dispatcher: spaces:*` и отдельно failed
`pass-secret-service`. Они остаются отдельными вопросами после разблокирования
graphics startup; Mesa-only изменение их не исправляет и не заявляет desktop
полностью принятым. Нативная Amnezia, cleanup bootstrap/profile, перенос checkout
и финальные пользовательские гайды ещё не завершены.

## 11.11: released stable kernel input

The user recalled choosing 7.3.3 rather than LTS on the live USB and stopped the
earlier Bluetooth switch plan. Rechecking the actual locked package sets explains
the mismatch: stable `linuxPackages_latest` is 7.3.3, while the selected unstable
snapshot's is 7.3.1. The installed/booted system and all five retained system
generations were still 7.3.1. `unstable` did not mean a newer kernel here.

Kernel.org reports released stable 7.3.4; neither published channel had promoted
it at inspection time. With user approval, `nixpkgs-kernel` follows Nixpkgs
**master** only to obtain `linux_latest`, explicitly not `linux_testing`/RC.
The new lock node pins `20771b995ab1cef82179579fb05847ca21cfb7f0`, selecting
7.3.4. No existing lock node changed. This input is passed only to Lenovo.

`pkgsGraphics.linuxPackagesFor pkgsKernel.linux_latest` instantiates the existing
unstable external-module recipes against the new kernel. It retains NVIDIA
615.78.08 and firmware 20261019 rather than adopting master NVIDIA/userspace.
The module package set inherits the kernel's compiler; both isolated imports
allow unfree evaluation because the inherited kernel stdenv's license policy
also checks the existing NVIDIA recipe. This is not a global package-set change.

Different kernel/userspace versions are supported through the Linux userspace
ABI; identical Nixpkgs versions are not a requirement. Out-of-tree modules are the
important exception: their headers/build directory/compiler must match the chosen
kernel. Selected merged declarations confirm NVIDIA open-module `SYSSRC` and
`SYSOUT` reference the **patched** 7.3.4 kernel and the stdenv derivations match
(GCC 16.2.0). The module derivation evaluates. This declaration check does not establish
compilation, loadability, real GPU behavior, suspend/Hibernate or freedom from
regressions; the subsequent built-result review below adds separate artifact evidence.

Mesa remains stable 26.1.8, preserving the previous userspace ABI correction.
No other host receives the new input through specialArgs. Previous PipeWire,
BlueZ, portal and shared Amnezia fixes are userspace fixes, not local kernel
patches; a new kernel is not evidence that they are obsolete. The two recent
[Bluetooth PM backports](../../hosts/laptop/bluetooth-pm.md) are still absent in
7.3.4. Their unchanged patches apply with zero fuzz/offset and all twelve
baseline/patched source-contract scenarios pass on the 7.3.4 stable-tag files.
GP1 mailbox handling, SPD5118/panel/ISH and real Bluetooth acceptance remain open.

### Updates and checks

The input follows a branch in `flake.nix`, not a permanently hardcoded revision;
`flake.lock` records the reviewed revision until explicitly updated. It will not
silently jump during a normal rebuild. There is no unattended updater. Nixpkgs
packaging can lag kernel.org, so future updates still require version review.

- `nix flake update` includes the new input along with every other input.
- `nix flake update nixpkgs-kernel` updates only the kernel input.
- The managed `nix-flake-update-verify` helper and Fish completions now accept
  `nixpkgs-kernel`. Its `--input all` already covers it. Updating only
  `nixpkgs-unstable` does **not** update this separate kernel pin.
- After applying the HM helper change, the existing opt-in update/build workflow
  is `nix-flake-update-verify --hosts laptop --input nixpkgs-kernel`. It builds
  both Lenovo outputs by the helper's existing policy; it does not switch or reboot.
  Before HM application, the direct `nix flake update nixpkgs-kernel` works already.
- Review `BTINTEL PM CLEANUP` on each kernel update. Test future unpatched source
  with `--check-upstream` before explicitly removing backports; keep scenarios.

Completed: kernel/NVIDIA/version/compiler declarations, actual open-module header
paths, preserved existing input nodes, declaration fixtures, Bluetooth contracts,
and three generated-updater mock tests (new input/all/no-update) plus Bash syntax.
The mock updater never performs a real build/update or Git operation. Full
graphics/assertion fixture evaluation was not separately rerun, and the agent
ran no kernel/NVIDIA/system/HM builds or live acceptance. Ruff/Prettier are
unavailable; no fallback formatter.

The user subsequently completed the Lenovo NixOS build. Source/configuration
review found no known application blockers and required no code or lock changes.
The existing `result` resolves to
`/nix/store/gn2f71lbm17cr7mk1wyqyz3clqmjzcdr-nixos-system-laptop-26.05.20261108.ac588ef`.
Its boot spec selects kernel/initrd 7.3.4; kernel output matches the current
configuration's evaluated output. Actual kernel derivation attributes include
both PM patches, byte-identical to the repository files. Its merged module tree
contains NVIDIA open 615.78.08 and `btintel_pcie`; `modinfo` reports matching
`7.3.4 SMP preempt mod_unload` on NVIDIA core/DRM and Bluetooth. This is built
artifact/metadata evidence, not real module loading or live GPU/Bluetooth/Hibernate
acceptance. At that review, running/current system were still 7.3.1. No rebuild or activation was
performed by the agent; only documentation was corrected after the user's build.

The user subsequently applied/rebooted. Boot `3d979c37f8d44f169933195991de40e3`
confirms running/current/booted 7.3.4 from that reviewed system, NVIDIA 615.78.08
loaded and Intel Bluetooth bound to `btintel_pcie`; there are no failed system/user
units. Startup still has xe's VBT WARN and NVIDIA DP-0 EDID warnings. One subsequent
manual Hibernate returns but repeats Bluetooth reprobe/GP1, SPD5118, panel and ISH
errors; initial headphone connection trouble remains unclassified. Real GPU/offload
and reliable Bluetooth reconnection are not established by module loading or a
later active A2DP/aptX snapshot. See [the boot audit](../../hosts/laptop/boot-errors.md) for the
successful private journal export, persistent errors and exact coverage.

### User verification and application

1. Review `git diff` and build only Lenovo NixOS (already completed/reviewed above):
   `nixos-rebuild build --flake .#laptop`. Allow for the local patched-kernel and
   NVIDIA module build cost/free disk space. Keep the known-good generation.
2. After a successful build and review, apply:
    `sudo nixos-rebuild switch --flake .#laptop`, then reboot. No driver reload or
    Hibernate is needed merely to install the configuration. Application/reboot
    are now completed; the remaining steps are functional acceptance.
3. After reboot require `uname -r` to report `7.3.4`, then verify Hyprland,
   `nvidia-offload`/GPU function and real Bluetooth function before a manual
   Hibernate cycle. Record entry/exit times and inspect the kernel journal;
   check session/VPN restoration without restarting the working tunnel.
4. Optionally apply `home-manager switch --flake .#samov-laptop` to install the
   updated verifier/completions. HM does not install this kernel; NixOS alone
   handles the kernel change. Documentation requires no activation.

No agent-run build, activation, reboot, driver reload or live Hibernate occurred.

## 11.11: user OpenGL/XWayland offload smoke

After accepting screen brightness, 160% scale, 165 Hz and ordinary lid close/open,
the user ran the pinned stable `mesa-demos` tool without changing configuration:

```fish
nix shell --inputs-from . nixpkgs#mesa-demos --command glxinfo -B
nix shell --inputs-from . nixpkgs#mesa-demos --command nvidia-offload glxinfo -B
```

The supplied outputs report:

- Ordinary launch: `direct rendering: Yes`, `Accelerated: yes`,
  `OpenGL renderer string: Mesa Intel(R) Graphics (PTL)`, Mesa 26.1.8, OpenGL 4.6.
- Explicit offload: `direct rendering: Yes`,
  `OpenGL renderer string: NVIDIA GeForce RTX 5060 Laptop GPU/PCIe/SSE2`,
  `OpenGL core profile version string: 4.6.0 NVIDIA 615.78.08`.

Neither output uses `llvmpipe`. This establishes real hardware-backed GL context
creation and Intel/NVIDIA selection through GLX/XWayland, not a rendering stress
test, Vulkan/native Wayland presentation, post-resume graphics or idle RTD3.
No driver, environment policy, package selection or lock was changed. No Nix
activation is required for this evidence-only update.

The user then ran the next bounded scenario:

```fish
nix shell --inputs-from . nixpkgs#vulkan-tools --command nvidia-offload vkcube --wsi wayland --c 600
```

The supplied output reports
`Selected GPU 1: NVIDIA GeForce RTX 5060 Laptop GPU, type: DiscreteGpu` and returns
to the shell without a supplied error. The pinned stable Vulkan-Tools 1.4.341.0
source supports these Wayland/frame-count options. GPU selection is observed;
visible cube rendering/automatic closure still await the user's explicit report.
This is not a stress or post-resume test. Plain Vulkan applications can prefer a
discrete GPU themselves; their default GPU choice must not be assumed to be Intel.

### Passive RTD3 inspection after the Vulkan command

No GPU workload, `nvidia-smi`, device reset or power-policy write was run by the
agent. One read-only snapshot finds:

- PCI `0000:02:00.0`: NVIDIA driver bound, `power/control=on`,
  `runtime_status=active`, `runtime_usage=2`, suspended time 0.
- PCI `0000:02:00.1`: snd_hda_intel, `power/control=auto`,
  `runtime_status=suspended`, `runtime_usage=0`.
- `/proc/driver/nvidia/params`: `DynamicPowerManagement: 3`,
  `PreserveVideoMemoryAllocations: 2`, `EnableS0ixPowerManagement: 0`.
- GPU `power`: `Runtime D3 status: Disabled by default`, video memory active,
  video-memory self-refresh/off hardware support reported as supported.

Thus the earlier expectation that this host would automatically enable RTD3 has
not materialized. This does not identify why NVIDIA's default policy disables it,
measure battery drain, or prove that no process also holds the GPU.
[NVIDIA's exact 615.78.08 README](https://download.nvidia.com/XFree86/Linux-x86_64/615.78.08/README/dynamicpowermanagement.html)
documents default 0x03 as fine-grained only on supported Ampere-or-later notebooks,
and explicit 0x02 as fine-grained control. Pinned NixOS's
`hardware.nvidia.powerManagement.finegrained` sets 0x02 plus bind/unbind udev rules
for GPU `power/control=auto/on`; on kernel 7.3.4 it does not add the old pre-5.5
audio/USB removal workarounds. This is separate from system suspend/VRAM policy.

The user subsequently approved preparing the Lenovo-only opt-in, without build,
application or reboot. `hosts/laptop/graphics.nix` now sets
`hardware.nvidia.powerManagement.finegrained = true`. This explicitly supersedes
the earlier native-default RTD3 baseline, not the agreed native suspend/VRAM policy.
No kernel/driver/Mesa/firmware selection, lock, other host or HM module changes.
Do not live-write sysfs, reload the driver, change S0ix/sleep handling or add a GPU
restart hook. The setting is prepared, not yet built/applied or hardware-accepted.

### Focused RTD3 declaration regression

```fish
nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/test-nvidia-runtime-pm.nix
nix eval --offline --json --file hosts/laptop/test-draft.nix
```

Both pass. The new selected merged check compares the real Lenovo configuration
with the same configuration extended to force the old `finegrained = false`:

- Require parameter `0x02` and exactly the four native GPU bind/unbind control rules.
- Require no NVIDIA audio/USB removal rules on the selected kernel.
- Require all other module parameters and suspend-policy options to match the
  native-default baseline, with no legacy nvidia-suspend/hibernate/resume units,
  explicit VRAM-preservation override, suspend-notifier override or S0ix override.

The fixture and existing full graphics check now expect the user-approved RTD3
policy instead of forbidding the setting. This expectation changes because of the
explicit user decision and measured disabled default, not to hide a failed test.
The broader `test-graphics.nix` was updated but not rerun; its earlier kernel,
NVIDIA, firmware and Mesa coverage is separate from these narrow current checks.
Changed Nix files pass pinned nixfmt 1.5.0; diff whitespace passes. Prettier remains
unavailable. These checks do not build a system, access hardware, measure idle
power or establish RTD3/Hibernate stability.

### User build, application and acceptance

1. Review the diff; build only Lenovo NixOS:
   `nixos-rebuild build --flake .#laptop`. Leave the current known-good generation.
2. After successful review/build, apply
   `sudo nixos-rebuild switch --flake .#laptop`, save work and reboot with
   `sudo reboot`. Do not unload/reload NVIDIA in the working graphical session.
   No Home Manager application is required for this NixOS-only change.
3. With GPU apps closed and no external display driving NVIDIA, inspect without
   running `nvidia-smi` or polling GPU utilities:

   ```fish
   cat /proc/driver/nvidia/gpus/0000:02:00.0/power
   cat /sys/bus/pci/devices/0000:02:00.0/power/control
   cat /sys/bus/pci/devices/0000:02:00.0/power/runtime_status
   ```

   Expect RTD3 enabled/fine-grained, control `auto`, and eventual `suspended` when
   idle. An active snapshot alone does not identify the blocker; inspect before
   adding more settings. Neither driver support nor `auto` alone proves D3 entry.
4. Repeat the short NVIDIA Wayland cube; verify visible rendering, then close it
   and allow the GPU to idle before taking another sysfs snapshot. Confirm return
   to suspend without disrupting Intel's desktop or the working VPN/audio.
5. Before accepting the new policy, separately repeat a user-run Hibernate cycle
   and check session/display/audio/VPN plus offload wake/return-to-idle after it.
   Do not call runtime PM reliable from one successful declaration or idle sample.

For rollback if the new policy causes regression: remove only this finegrained
opt-in, rebuild/apply the reviewed NixOS configuration and reboot, or use the
retained known-good boot generation. Do not change driver/kernel pins as part of
this runtime-PM experiment. No agent-run build, activation, reboot or live power
change occurred.

### Applied RTD3 opt-in: unsupported result and Linux 7.3 driver regression

The user subsequently built/applied and rebooted. Read-only inspection of boot
`89e38bd1-cbbf-4bf3-a789-085ed0e5701f` confirms running kernel 7.3.4 and matching
current/booted system `hxldrcjja7wb08bq1n5319r4dhb0nk6j`. NVIDIA 615.78.08 is loaded;
`DynamicPowerManagement: 2`, native VRAM value 2 and S0ix value 0 confirm the intended
parameter change without the unrelated overrides. GPU control is `auto`, but its
status remains `active`/D0, suspended time 0, and the user-supplied proc report says
`Runtime D3 status: Not supported`. NVIDIA audio is auto/suspended (D3hot).
This is a failed RTD3 acceptance, not evidence that the configuration was unapplied.

Exact driver source clarifies an important limitation of the previous diagnosis:
`RmGetDynamicPowerManagementStatus()` reports `Disabled by default` for internal
mode NEVER with parameter 3, but `Not supported` with parameter 2. The first wording
can mask a support-check failure; it did not prove that explicit 0x02 would suffice.
The ordinary change to 0x02 has exposed the refusal, not proven new hardware damage
or an immutable lack of RTD3 on this GPU model.

There is now a concrete matching upstream report:
[NVIDIA issue #1507](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1507),
confirmed by other machines including a Blackwell Lenovo. NVIDIA acknowledged it
with internal bug 7039712. Linux 7.3 starts kthreads in an empty nullfs root; the
615.78.08 probe worker uses `filp_open()` on an absolute `/sys/.../config` path.
Failure leaves `sysfs_config_file` NULL, making `nv_dynamic_power_available()` false
and disabling RTD3. The exact source chain matches the selected versions. The
local upstream PCI port `0000:00:06.2` is ACPI `\_SB_.PC00.RP11` and exposes a
`power_resources_D3hot` link; absence of all platform power resources is not
established. No live probe trace, measured local open errno or ACPI-method
evaluation was performed, so this is a strong source-supported candidate, not a
measured Lenovo root cause.

[PR #1512](https://github.com/NVIDIA/open-gpu-kernel-modules/pull/1512) is open and
unmerged at inspection, head `369378dc1552ae46f7f95a598a085c0025e464b3`. It uses
`scoped_with_init_fs()` for the config open when the GPL-exported kernel helper is
available, adds conftests and avoids the extra probe kthread for non-async probing.
It is a proposed driver fix, not a released or locally validated repair.
Exact 615.78.08 sources, selected 7.3.4 source, PR snapshot/diff and SHA256SUMS are
retained at `/tmp/opencode/nvidia-rtd3-615.78.08/` for bounded follow-up review.

No further power setting, rebind hook, module unload/reload, firmware change,
kernel downgrade or tracing was enabled. The finegrained option remains applied
as approved; it is not accepted as effective. The user subsequently approved
preparing the Lenovo-only open-module backport with tests, without building or
applying it, and requested a comprehensive automatically checked fix inventory.

### Prepared PR #1512 backport and removal inventory

`hosts/laptop/nvidia-init-root.patch` is byte-identical to the saved PR diff at
head `369378dc1552ae46f7f95a598a085c0025e464b3`, SHA256
`a6b25746cbaa9193e8aebd39debe93190e1ca111d9549650ca1a0871e9e0ccd0`.
It applies to selected 615.78.08 source with zero fuzz and zero offset.
`graphics.nix` replaces only the package's `open` member, appending to existing
module patches; the userspace derivation is retained, not overridden.

`test_nvidia_init_root.py` compiles the actual config-open/probe functions with
contract stubs. Eight baseline and eight patched compile variants cover helper
export availability, async/non-async probe and seq-read validation guards. Cases
cover nullfs-root failure/recovery, process-root fallback, scope restoration after
successful/failed opens, invalid sysfs/seq/kernfs handles and close ownership,
registration/later probe, allocation/thread failure fallback, single probe-body
execution and return propagation. Kbuild conftest declarations and the guarded
header include are checked. This is a **mock filesystem and worker contract**,
not native kernel headers, real kthreads/nullfs, module compilation or hardware
RTD3/Hibernate coverage. Alternate source layouts may require harness review;
a failed harness never proves a fix is needed.

Merged `test-nvidia-backport.nix` checks delivery through `boot.extraModulePackages`,
preservation of existing patches and unchanged kernel/userspace/module parameters/
sleep policy, with no patch on Acer/desktop. Evaluation retains kernel output
`/nix/store/gf6c6ilz4nkma7xrzv6iisafnack99ky-linux-7.3.4` and userspace output
`/nix/store/fb16gwfjkwk14bj50yych38km3j0by53-nvidia-x11-615.78.08`.
Only the NVIDIA open-module derivation changes. Missing/garbage-collected build
dependencies can still require realizing an existing derivation: inspect a build
dry-run rather than promising no kernel work under every store/cache condition.
No build/dry-run/activation was run here. Declaration and merged runtime-PM tests
also pass; broader `test-graphics.nix` was not rerun. Pinned nixfmt was used;
Prettier/Ruff were unavailable, not substituted or installed.

[The central inventory](../backports/README.md) covers all 18 active patch files,
inline companions and temporary selections. The updated HM helper validates
coverage/fingerprints before builds, then probes offline cached sources and runs
available small unpatched contracts after successful builds. Direct script use
needs no activation. No automatic fix removal, review acceptance, periodic timer
or upstream network polling. Initial fingerprints are inventory state, not fresh
functional acceptance of all retained fixes.

User verification/application, from the repository root:

1. Inspect tracked and new files. Git-backed `.#` excludes untracked files:
   after review, stage at least `git add hosts/laptop/nvidia-init-root.patch`
   before the **module-only** dry-run below. At the preparation checkpoint the
   agent had not staged/committed changes; those evaluation checks used the
   working-tree path flake. The user later authorized a final local commit.
   `nix build --dry-run .#nixosConfigurations.laptop.config.hardware.nvidia.package.open`.
   A new NVIDIA module is expected, not a new kernel derivation. If a kernel build
   appears, stop and inspect missing outputs/dependencies before starting it.
2. Build: `nix build .#nixosConfigurations.laptop.config.system.build.toplevel`.
   The agent has **not** performed this. Leave the running driver alone.
3. After personal review: `sudo nixos-rebuild switch --flake .#laptop`, then reboot.
   Confirm current/booted system and unchanged kernel 7.3.4/driver 615.78.08.
4. Without repeated `nvidia-smi` polling, inspect
   `cat /proc/driver/nvidia/gpus/0000:02:00.0/power` and
   `cat /sys/bus/pci/devices/0000:02:00.0/power/runtime_status`.
   Expect `Enabled (fine-grained)` and eventual idle `suspended` with increasing
   `power/runtime_suspended_time`. Open clients/workloads can hold D0; that alone
   is not a reason to add power knobs.
5. Accept visible native Wayland offload, return to idle, then manual Hibernate/
   resume with Intel desktop, NVIDIA offload, audio and VPN still working. One
   successful cycle is not reliability proof.
6. Separately apply HM with `home-manager switch --flake .#samov-laptop` for the
   updated automatic review hook. No HM change is needed to deliver NVIDIA.

Rollback: remove only the `package.open` backport override (restore
`hardware.nvidia.package` to the original latest package), build/review/apply and
reboot, or use the previous NixOS generation. Retain finegrained selection,
Bluetooth/audio fixes and regression scenarios unless separately approved. No
live NVIDIA unload/rebind. On updates run `test_nvidia_init_root.py SOURCE
--check-upstream` on unmodified source before explicitly removing the fix;
conflicts, versions or a closed PR are not proof. Retain the harness after removal
and accept real RTD3/offload/resume again.

### User-built result: static module review, not yet applied

The user staged the new patch, ran the module-only dry-run (only
`ghilz5iivqz0dl5v8qjsj6y6pskb9pzr-nvidia-open-615.78.08-7.3.4.drv` was listed),
then successfully built the Lenovo NixOS output. The Bluetooth PM cleanup warning
is the retained update/removal reminder, not a build error or evidence that either
Bluetooth fix is obsolete.

Read-only review of `result` finds system
`/nix/store/73nyv4l2vma23wl69n22a75gbkxnjp69-nixos-system-laptop-26.05.20261108.ac588ef`.
Its kernel is the exact existing `gf6c6ilz...-linux-7.3.4/bzImage`. All four NVIDIA
module paths resolve to the new
`/nix/store/7ib7jzzkv7048q5wdwdzll1zn9hw5ll5-nvidia-open-615.78.08-7.3.4`;
their module version is 615.78.08 and vermagic is `7.3.4 SMP preempt mod_unload`.
The system closure contains this open-module output, not the old one. NVIDIA
userspace/lib32/bin/firmware outputs are identical to the currently active system.
The generated modprobe configuration is also identical, including RTD3 `0x02`.

The built module derivation's environment differs from the unpatched module only
in `out` and `patches`; builder and arguments match. Its sole added patch has the
recorded SHA256 and matches the working-tree bytes. Static inspection of the
actual decompressed `nvidia.ko` finds undefined symbol `userspace_init_fs`, showing
that the guarded init-root branch compiled into this binary, not only the harness.
No module was loaded/unloaded/rebound and no GPU workload or sysfs write was run.

Current and booted system still point to `hxldrcjja...`, not this built result.
The user has now verified native compilation, not module loading, RTD3 support,
idle suspension, offload wake or Hibernate. Next: personal review, NixOS switch
and reboot, then proc/runtime-PM checks and the functional sequence above. The
agent performed no package build or activation; standalone HM remains separate.

### Applied backport: observed idle RTD3 / D3cold success

The user subsequently applied/rebooted. Boot
`57375bf8-6b91-4e42-8bec-912e71bdd4eb` has matching current/booted system
`73nyv4l2vma23wl69n22a75gbkxnjp69`, kernel 7.3.4 and loaded NVIDIA 615.78.08.
Loaded module srcversion `B7B4C26B1C05FB1F7DBAB43` matches the reviewed built
`7ib7jzzk.../nvidia.ko.xz`. Parameters remain RTD3 2, VRAM preservation 2 and
S0ix 0; PCI GPU control is `auto`.

The user's proc report now says `Runtime D3 status: Enabled (fine-grained)` and
`Video Memory: Off`; PCI runtime status is `suspended`, with suspended time 78875.
A subsequent independent read-only snapshot finds `suspended`, actual PCI power
state **D3cold** and suspended time 99805 (the millisecond counter increased).
No workload, nvidia-smi polling, module operation or power-policy write was run
by the agent. This establishes the first installed-boot idle RTD3 success after
the scoped backport, not only correct configuration or a mock contract.

The original failing open errno is still unmeasured; this result strongly
supports the matching upstream regression/fix without pretending a pre-patch
live trace exists. Native Wayland offload wake, visible rendering/auto-close,
return to idle and Hibernate/resume on this patched module remain unverified,
as do repeated cycles and battery-life/load measurements. Next: repeat the pinned
stable native Wayland vkcube command above, confirm NVIDIA selection and visible
auto-closing cube, then inspect runtime status after it returns to idle. Only
after that proceed to the manual Hibernate/offload/idle sequence. No new setting
or application is required for these checks; standalone HM helper activation is
still a separate operation.

### First patched offload run: return to D3cold observed

The user repeated the pinned stable native Wayland vkcube command with `--c 600`.
It selected `NVIDIA GeForce RTX 5060 Laptop GPU` and returned to the shell without
supplied errors. Subsequent user runtime-status reads showed `active` three times,
then `suspending`. A later single independent read-only snapshot confirms
`suspended`, runtime usage 0 and PCI **D3cold**, with GPU control still `auto` and
suspended time 235225 ms. Thus the device did return to runtime sleep after this
offload invocation; the intermediate `suspending` was not a persistent failure.
Exact transition latency was not measured, and cumulative active time is not a
measurement of the post-cube delay.

No workload, repeated GPU polling, hook, module operation or policy change was
introduced by the agent. The user then explicitly confirmed that the cube was
visible and closed automatically. Combined with NVIDIA selection and the later
independent D3cold snapshot, this accepts one native Wayland offload wake/render/
exit/return-to-idle cycle on the patched module. It is user UI acceptance, not
independent agent visual inspection. Hibernate/resume with this module, repeated
cycles and sustained load remain separate checks. Next is a user-run manual
Hibernate, restored session/VPN check, then the same offload and idle checks;
save work first and do not unload/rebind the driver or restart the working VPN.

### User acceptance: one patched Hibernate/offload/idle cycle

The user explicitly confirmed all steps of the subsequent manual Hibernate test:
session restoration, automatic Amnezia recovery, visible native Wayland NVIDIA
cube with automatic closure, and the expected enabled RTD3/return to runtime
sleep. This accepts one such cycle, based on the user's functional observations;
the agent did not independently watch the UI, execute Hibernate, inspect VPN
egress or capture the exact cycle timestamps/kernel PM trace.

A later single read-only snapshot still finds boot `57375bf8...`, matching
current/booted system `73nyv4l2...`, kernel 7.3.4 and the same patched NVIDIA
615.78.08 srcversion. GPU control is auto, runtime status suspended, runtime usage
0 and PCI state D3cold; suspended time is now 505617 ms. This corroborates the
current idle state, not independent observation of the entire Hibernate sequence.
No further graphics/power workaround is indicated by this successful scenario.
Repeated cycles, sustained workload, broader graphics behavior and battery-life
measurements remain outside this acceptance; deferred Bluetooth/firmware/error
investigations are not silently closed.

The installed `~/.nix-profile/bin/nix-flake-update-verify` still lacks the new
`backport-review.py` hook at this checkpoint. Standalone HM must be applied
separately to install that hook; until then use the checkout checker directly.
Audit/registry text updates require no activation. No agent build, activation,
driver operation or new policy change was performed.

The user subsequently applied standalone HM and ran the checkout checker, which
reported `unchanged=26` with its explicit non-verification disclaimer. Read-only
inspection now resolves the installed update-helper to
`/nix/store/qbm2l45zd2pngc5fpqh5irpbhs42i5lb-nix-flake-update-verify/bin/nix-flake-update-verify`.
It contains the checkout checker invocation and post-build
`review_backports --cached --contracts`; installed Bash syntax also passes.
Thus the automatic review hook is installed, no longer only prepared in source.
The agent did not run the updater or any real input-update/build cycle to test
the hook end-to-end. The Home Manager news notice is informational, not an error.

### Final review and separate Waybar follow-up

The user requested final review and a local commit after the installed acceptance.
The 22 checker tests, four generated-updater/mock tests, eight baseline/eight
patched NVIDIA compile variants, three selected Nix declaration/merged checks,
registry coverage/fingerprints and pinned nixfmt check pass again. Builds and live
functional acceptance are reused from the user's preceding tests, not rerun by
the agent. Prettier/Ruff remain unavailable. Non-patch whitespace checks pass;
the exact upstream patch intentionally retains two single-space blank context
lines required by unified-diff syntax, without changing its recorded bytes.

The user's missing Waybar GPU section is explained by the installed and repository
Lenovo config: `modules-center` intentionally omits `custom/gpu`, with a comment
deferring periodic nvidia-smi until runtime PM was established. Acer/desktop still
use the shared `gp.sh` nvidia-smi polling helper every ten seconds. This is not a
panel disappearance caused by the RTD3 patch. No Waybar source or live config was
changed in this batch. A separate follow-up should design an indicator that does
not wake the suspended NVIDIA device; do not simply restore the old polling path.
