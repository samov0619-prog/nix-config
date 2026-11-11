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
