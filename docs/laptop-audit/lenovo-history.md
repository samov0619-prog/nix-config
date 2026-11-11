# Lenovo: история подготовки и первых проверок, 10–12.11.2026

Это сохранённая история решений и промежуточных состояний, не текущая инструкция
установки и не список обязательных действий на уже установленном ноутбуке.
Актуальны [гайд](../../hosts/laptop/README.md) и [текущая приёмка](lenovo-checklist.md).
Фразы «ещё не установлен», прежняя RTD3 policy и старые открытые пункты ниже
относятся к соответствующим этапам. Не выполнять команды отсюда вместо гайда.

[Каталог аудита](README.md) · [Решения](feedback.md)

Lenovo уже установлен; NixOS и standalone HM применены пользователем. Актуальные
результаты и открытые ошибки — в [boot-errors.md](../../hosts/laptop/boot-errors.md).
На 11.11 пользователь подтвердил возврат сессии после Hibernate, автоподключение
Amnezia после перезагрузки и быстрое восстановление VPN после Hibernate. В свежей
загрузке GUI/helper совпадают; предыдущий shutdown не воспроизвёл PipeWire SIGSEGV.
Пользователь также подтвердил удаление установочных хвостов. Это не полная приёмка
железа, DNS/split routing/kill-switch или автоматической защиты батареи.

После уточнения live 7.3.3 против установленной 7.3.1 пользователь остановил
прежний switch plan. Теперь отдельно подготовлено stable-ядро **7.3.4** из
`nixpkgs-kernel`, без обновления остальных input nodes/NVIDIA/firmware/Mesa.
Два Bluetooth PM-backport остаются нужны и проходят source contracts на 7.3.4;
совпадение NVIDIA open-module headers/compiler проверено по декларациям.
Пользователь затем успешно собрал NixOS; review фактического `result` подтвердил
7.3.4, оба текущих патча и matching vermagic NVIDIA/Bluetooth-модулей. Код/lock
после сборки не менялись. Пользователь применил конфигурацию и перезагрузился:
running/current/booted — 7.3.4, NVIDIA 615.78.08 загружен, Bluetooth-драйвер привязан.
В новой загрузке GP1/ISH/WirePlumber ошибки сохраняются. Один Hibernate после
обновления вернул сессию, но reprobe/GP1/SPD5118/panel/ISH повторились. Пользователь
сообщает о первоначальной неудаче подключения наушников; позже наблюдаются connected
и running A2DP/aptX. Пользователь затем подтвердил слышимый звук после ручных
переподключений/удалений/добавлений; разбор наушников и Bluetooth tuning явно отложен.
Это не подтверждение автоматического переподключения.
Пользователь затем проверил `glxinfo -B`: обычный запуск использует Intel PTL /
Mesa 26.1.8, `nvidia-offload` — RTX 5060 / NVIDIA 615.78.08; direct rendering есть,
`llvmpipe` нет. Это OpenGL/XWayland smoke, не полная приёмка GPU. Затем `vkcube`
с `--wsi wayland --c 600` через offload выбрал NVIDIA; визуальный результат ещё
не подтверждён. Read-only RTD3 snapshot: GPU `control=on`, active и
`Disabled by default`, тогда как NVIDIA audio уже auto/suspended. Пользователь
одобрил подготовку finegrained: Lenovo NixOS теперь явно задаёт RTD3 0x02 и штатные
udev auto/on rules, не меняя Hibernate/VRAM/S0ix. Узкие merged/baseline checks
прошли. Пользователь затем применил/reboot: параметр действительно 2, GPU auto,
но active/D0 и `Runtime D3 status: Not supported` — RTD3 не принят. Найден точный
upstream-кандидат NVIDIA #1507 / открытый PR #1512: Linux 7.3 kthread nullfs мешает
615.78.08 открыть PCI sysfs config. Локальный errno не измерен. Пользователь одобрил
подготовку: точный PR-backport теперь добавлен только в Lenovo open-модуль;
actual-function contract tests и проверка неизменных kernel/userspace derivations
прошли. Пользователь затем успешно собрал NixOS: result содержит новый open-модуль
с vermagic 7.3.4 и символом userspace_init_fs; ядро и NVIDIA userspace прежние.
Пользователь затем применил/reboot: boot 57375bf8... имеет matching current/booted
73nyv4l2..., загруженный srcversion совпадает с новым модулем. Proc сообщает
Enabled (fine-grained), Video Memory Off; независимый snapshot подтверждает
suspended/D3cold и рост suspended-time. Idle RTD3 теперь подтверждён на этой загрузке.
Повторный native Wayland vkcube выбрал RTX 5060 и вернулся в shell; после active →
suspending независимый snapshot подтвердил suspended/D3cold, runtime usage 0.
Возврат в idle после этого запуска подтверждён, точная задержка не измерена.
Пользователь явно подтвердил видимый cube и автозакрытие: один цикл native Wayland
offload wake/render/выход/возврат в idle принят. Затем он подтвердил весь отдельный
Hibernate-сценарий: восстановление сессии/VPN, cube и возврат RTD3 в sleep. Один
Hibernate/offload/idle цикл с новым модулем принят по пользовательскому наблюдению;
последующий read-only snapshot подтверждает D3cold/runtime usage 0 с тем же модулем.
Это не независимое agent UI/PM/VPN наблюдение; повторные циклы, sustained load и
измерение автономности остаются отдельными проверками.
Никаких rebind hooks, driver reload или новых power-настроек.
Подробности и следующий согласуемый шаг — в конце [graphics audit](graphics.md).
Надёжность повторных GPU/RTD3/Hibernate циклов, длительная нагрузка и надёжное
Bluetooth-восстановление ещё открыты. Пользователь затем применил HM: установленный
update-helper содержит новый backport-review hook и post-build cached contracts;
его Bash syntax проверен. Ручной checker сообщает unchanged=26 — это совпадение
fingerprints, не новая upstream/функциональная проверка. Реальный update/build
цикл через новый helper агент не запускал.
Отсутствовавший GPU-блок затем заменён принятым пользователем `custom/gpu-manual`:
клик включает измерения на 60 секунд, повторный продлевает окно; после истечения
цифры скрываются и остаётся кнопка GPU. Idle не опрашивает NVIDIA. Во время явного
измерения GPU может просыпаться; возврат ко сну и UI приняты по сообщению пользователя.
Старый shared gp.sh с nvidia-smi каждые 10 секунд не возвращён. См.
[Waybar README](../../home/linux/laptop/waybar/README.md).
Порядок update/reboot/приёмки — в
[kernel audit](graphics.md#1111-released-stable-kernel-input) и
[Bluetooth PM](../../hosts/laptop/bluetooth-pm.md). Старые userspace fixes сохраняются.

Подготовительный раздел ниже — исторический порядок до установки, не инструкция
повторно размечать уже установленную систему. Остальные пункты сохраняют проверки,
ещё не закрытые отдельными свидетельствами; успешный switch и fixtures не заменяют
приёмку. Minecraft не запускать на Acer ради аудита. Текущий приоритет пользователя:
яркость экрана → масштаб → гашение экрана при закрытии крышки → остальные функции.
Первые три пункта теперь приняты пользователем: клавиши регулируют Intel-подсветку,
масштаб 160%, панель 3200×2000/165 Гц; крышка гасит/включает только встроенный экран
без сна. Read-only review подтверждает 164.995 Гц, scale 1.6, загруженные brightness/lid
binds и отсутствие config errors. Это не приёмка внешних мониторов, всех приложений,
регулировки после resume или входа с уже закрытой крышкой. Разбор сообщений без установленного влияния
на работу приостановлен, без сокрытия логов и удаления применённых исправлений.
BIOS, наушники/tuning и fingerprint отложены; sudo неизменён. Fn+Space уже работает.

## Текущий остаток на 12.11.2026

- Пользователь принял новые hotkeys, камеру, screen sharing, видеозвонки,
  переключение тем и текущую локальную диктовку. Это пользовательская приёмка,
  не независимое agent UI-наблюдение всех сценариев.
- Пользователь применил и принял [Browse точки монтирования → Yazi](removable-media.md)
  и настройки [предупреждения 15% / Hibernate 2%](battery.md). Read-only проверка
  подтверждает active UPower, выбранный Hibernate, installed пороги 15/5/2 и MIME
  default Yazi. Фактическое low-battery действие и достаточность 2% не проверены.
- Статистика питания/температур/PPD, улучшение диктовки, fingerprint/шифрование,
  внешний монитор и длительная GPU-нагрузка отложены. Повторные resume-проверки —
  по обычному использованию, не через намеренный глубокий разряд.
- Следующий согласованный шаг — актуализация install guide:
  рабочие решения включить в основной путь, не заставляя повторять исторические
  поломки. Текущий исторический текст ниже ещё не является таким финальным гайдом.

## До установки: исторический согласованный порядок на 10.11.2026

Пользователь уже загрузил Lenovo в live NixOS с официальной stable 26.05 Minimal
x86_64 USB. Windows Home сохранять не требуется; внутренний SSD ещё не размечен.
Проходить Windows setup ради read-only inventory не требуется. Пользователь выбирает полный update
всех inputs перед установкой, а не сохранение старого Acer snapshot; на Acer
обновления откладывались из-за места. Базовые storage/login/GC решения сохраняются.

Устанавливается сразу полный подготовленный Lenovo NixOS config, затем отдельным
действием полный standalone HM, не промежуточная минимальная ОС. Это не включает
преждевременный запуск Minecraft server/backup: их preflight остаётся ниже.
Разметка выбрана через Disko и для ноутбука: он заменяет ручные partition/format/mount
шаги manual, не `nixos-install`. Полный update обновляет и Disko; review и запуск
используют одну и ту же обновлённую ревизию из `flake.lock`, не старый snapshot
и не отдельный непроверенный upstream/latest. Обычный rebuild не переразмечает диск.

1. **Live USB подготовлен.** На маленькую Generic Flash Disk 14.5 GiB напрямую,
   без Ventoy, после размонтирования записан
   `nixos-minimal-26.05.13936.ac588ef1c914-x86_64-linux.iso`:
   1746124800 bytes, 162.52 s, 10.7 MB/s, без ошибок `dd`.
   Проверка SHA-256/readback не сообщена. Kingston с данными не очищался;
   отдельный постоянный live+DATA образ отложен. Live channel не выбирает inputs
   или stateVersion установленной системы; unstable ISO заранее не требуется.
2. **Live session запущена по сообщению пользователя.** После Secure Boot block
   согласовано отключить только Secure Boot, без удаления ключей, очистки TPM,
   смены storage mode или прошивки BIOS. Сохранение Windows не требуется;
   отсутствие BitLocker/Secure Boot keys независимо не подтверждено.
   По выводу пользователя подтверждены live-ядро `7.3.3` и UEFI
   (`/sys/firmware/efi` существует). Wi-Fi подключён, пользователь вошёл с Acer
   по SSH в live `nixos`; `curl -I https://cache.nixos.org` вернул HTTP/2 200.
   Это доступ к endpoint, не проверка скачивания closures. Memtest запускался,
   но завершённый проход не сообщён: не считать RAM проверенной.
   Внутренний SSD не размечать и не монтировать на запись. Настроить сеть через
   `nmtui` при необходимости; проверить доступ к Nix binary cache без публикации
   Wi-Fi паролей. Не менять MUX, TPM или storage-controller mode ради inventory.
3. **Снять read-only hardware inventory.** Версия live ISO/ядра, UEFI, CPU/RAM,
   диски/разделы/mountpoints и стабильный путь выбранного SSD, PCI GPU/Bus IDs/driver,
   DRM connectors встроенного и нужных внешних экранов, доступные firmware/MUX modes.
   Записать наблюдения без private files, сетевых паролей и серийных номеров в docs.
   Команды выбирать после загрузки live; это не стресс-тест и не проверка NVIDIA
   offload/resume. Не считать live USB filesystems готовым hardware config установленной системы.
   Получен `lsblk`: USB Generic Flash Disk 14.5 GiB — `/dev/sda`, ISO на `/iso`;
   внутренний NVMe UMIS UPJYJ1TBMNV1Q 953.9 GiB — `/dev/nvme0n1`, без показанных
   mountpoints. Разделы: 450 MiB vfat, 16 MiB без определённой ФС, 500 GiB и
   451.5 GiB с сигнатурами BitLocker, 2 GiB ntfs. Сигнатуры не устанавливают
   состояние ключей/защиты; Windows сохранять не требуется.
   `/dev/disk/by-path/pci-0000:01:00.0-nvme-1` указывает на этот SSD; это путь
   по PCI topology, не identity накопителя. Перед разметкой снова сверить target;
   Disko теперь использует этот путь; перед стиранием повторно проверить SSD.
   Разрешения на стирание этим выводом не дано.
   DMI: `21VJ`, `ThinkBook 16 G8+ IPD`.
   Live inventory: Core Ultra 7 356H, family 6/model 204 (`0xcc`), 16 CPU,
   microcode `0x115`; `free -h`: 30 GiB RAM, swap отсутствует в live.
   Intel Panther Lake `[8086:b0a0]` на `00:02.0` использует `xe` (DRM card0);
   NVIDIA RTX 5060 Mobile `[10de:2d59]` на `02:00.0` использует `nouveau`
   (DRM card1), не выбранный для установки NVIDIA open driver.
   PRIME IDs соответствуют `PCI:0:2:0` и `PCI:2:0:0`. Пользователь выбрал
   PRIME offload: Intel для desktop, NVIDIA по явному запуску выбранных приложений.
   **Весь Steam на NVIDIA не переводить**; GPU selection не задавать глобально.
   В `graphics.nix` включены offload и штатная команда `nvidia-offload` с этими IDs.
   Для выбранной игры можно один раз задать в Steam Launch Options
   `nvidia-offload %command%`; это ручное состояние Steam, не HM-managed config.
   Декларативные per-app launchers возможны позже для явно выбранных приложений,
   сейчас обёртки для Steam/Blender или других apps автоматически не добавляются.
   После review документации выбранного NVIDIA 615 пользователь согласовал его
   штатную open-module power policy: без принудительных RTD3/S0ix/deep, старых
   suspend units и Dynamic Boost. RTD3 поддерживаемых новых notebooks и сохранение
   VRAM описаны NVIDIA как автоматические; реальную работу проверить после установки.
   Offload сам по себе не доказывает засыпание NVIDIA или надёжный resume.
   DRM: Intel `card0-eDP-1` — connected, DP-1…4 — disconnected;
   NVIDIA `card1-eDP-2` и `card1-HDMI-A-1` — disconnected. Пользователь подтвердил,
   что подключён только встроенный экран: в текущем режиме активная панель на Intel.
   Переключение MUX и внешний экран не проверены; эти данные не доказывают работу
   HDMI/USB-C с установленным NVIDIA driver.
   Wi-Fi использует `iwlwifi`, Bluetooth — `btintel_pcie`, Ethernet — `e1000e`,
   audio — `sof-audio-pci-intel-ptl`, SSD — `nvme`. Наличие drivers не доказывает
   работу Bluetooth/audio и прочих устройств. В live нет `rg`: следующие команды
   для пользователя должны обходиться базовыми утилитами без установки пакетов.
   `nixos-generate-config --show-hardware-config --no-filesystems` выдал import
   `installer/scan/not-detected.nix`, initrd available modules `xhci_pci`,
   `thunderbolt`, `nvme`, `usb_storage`, `sd_mod`, `sdhci_pci`; kernel module
   `kvm-intel`; platform `x86_64-linux`, Intel NPU enable и default microcode update.
   Initrd kernelModules/extraModulePackages пусты. Scan без storage включён в
   `hosts/laptop/hardware-configuration.nix`; NPU option существует в locked
   nixpkgs. Declaration fixtures проверяют import/modules/platform/NPU и отсутствие
   live filesystems. Это не полный merged evaluation/build или реальная проверка NPU.
4. **Завершить конфигурацию и передачу имён.** Hardware scan и PRIME offload заданы;
   Нативный NVIDIA power baseline согласован. Selected merged graphics/storage и
   HM activation derivation evaluation прошли на обновлённом lock. После финального
   configuration review 11.11 и согласия пользователя install guard снят:
   NixOS toplevel derivation evaluation прошла offline без IFD; все merged assertions
   истинны. Builds и живые idle/resume проверки ещё впереди. Проверенный путь SSD внесён в Disko.
   В исходниках переданы `laptop`/`samov-laptop` Lenovo, Acer →
   `laptop-old`/`samov-laptop-old`: каталоги, outputs, hostname, helpers, completions,
   tests и текущие команды документации. Исторические записи не переписываются.
   [Границы и проверка rename](host-renaming.md): пользователь успешно применил
   Acer NixOS/HM под новыми именами и подтвердил работу. Static hostname стал
   `laptop-old`; старое transient имя исправлено отдельно. Это не проверка
   Lenovo, повторной загрузки или resume.
   Guard снят по результатам review, не ради обхода ошибки build; это не разрешение
   на стирание SSD или автоматический запуск установки.
5. **Пользователь выполнил `nix flake update`**, сохранив прежний tracked lock как
   исходную точку в Git. Не удалять lock: полный update достаточно явно обновляет
   зависимости согласно `flake.nix`. Команда не собирает и не активирует систему,
   но скачанные input sources тоже занимают место. Фиксированные tags/revisions и
   выбранные ветки не превращаются автоматически в latest: оставшиеся pins рассмотреть
   отдельно, не менять источники и проверенные обходы молча. После update пользователь
   передаёт diff для review, агент не обновляет lock и не выполняет Git network operations.
6. **Целевой review и сборки, не аудит каждого upstream-коммита.** Проверить input
   changes, evaluation/deprecations, package versions и совместимость локальных
   patches/overlays, особенно OpenCode, Waybar, AmneziaVPN, Blueman и графики.
   Package override не удалять только потому, что новый patch конфликтует: нужны
   evidence upstream fix и подходящие regression checks. Пользователь собирает
   конечные NixOS/HM outputs Lenovo на машине с достаточным местом; Acer и полную
   host matrix по умолчанию не собирать. Builds, Disko, install и activation остаются
   отдельными действиями пользователя. После update прежние fixtures/acceptance
   сохраняют историческую ценность, но не гарантируют совместимость новых packages.
   **До основных downloads согласовать место для Nix store.** Live writable store
   находится в RAM: ранее около 14 GiB свободно при лимите 16 GiB, без swap.
   Не предполагать, что туда поместятся обе полные closures или их сборки.
   На Acer полный обновлённый HM не собирать. Сначала выбрать storage-aware
   install/build порядок; если он требует предварительной разметки SSD, отдельно
   согласовать её до выполнения, не выдавать RAM-build за обязательный preflight.
   До скачивания основной closure на Lenovo можно подключить отдельный AWG 3.1
   профиль через декларативный [installer-vpn](../../pkgs/installer-vpn/README.md).
   Пользователь уже создал отдельного клиента и передал `.conf` с Acer в live;
   секретный файл остаётся вне Git/store. Helper прошёл review и локальные fixtures;
   10.11 пользователь собрал его в live Lenovo из checkout `b5ccba9` и подтвердил
   подключение, свежий handshake (14 s), публичный IPv4 VPS и LAN SSH. Вывод показал
   DNS `10.66.0.1` (AdGuard), маршруты к DNS и публичному IPv4 через `lenovo`, HTTPS
   к `cache.nixos.org` — HTTP/2 200. После `down` вернулись Wi-Fi-маршрут, DNS роутера,
   домашний внешний IPv4 и рабочий HTTPS. Это пользовательская живая приёмка helper
   на прежнем committed lock, не проверка полного обновлённого NixOS/HM, IPv6 leaks,
   всех firewall rules или установленного графического клиента.
   Это не требует установки графической Amnezia или административного SSH к VPS.
   **Доставка через Git выбрана для практики**, не копированием checkout по SSH.
   После review сохранить согласованные изменения и lock локальными коммитами;
   push выполняет пользователь. В live Lenovo проверить наличие Git, при отсутствии
   дать временный Git через `nix-shell -p git`. Публичный repo впервые клонировать
   по HTTPS без ключей и авторизации, не через Acer-specific SSH alias
   `github.com-samov0619`. На Lenovo live:

   ```fish
   git clone https://github.com/samov0619-prog/nix-config.git
   cd nix-config
   git rev-parse HEAD
   git status --short
   ```

   Сверить HEAD с доставленным reviewed commit; `git status --short` должен быть
   пустым. Не копировать private keys Acer в live: для clone они не нужны.
   После установки настроить SSH для постоянного пользователя и сменить `origin`
   в том же checkout, без повторного clone (пункт Git/SSH ниже).
   Перенести install checkout на целевой диск после mounts для сохранения
   после reboot. До этого live checkout не переживёт перезагрузку.
   Git author identity и аутентификация — отдельные вещи; clone не требует
   `user.name`/`user.email`. Shared HM включает Git/editor/merge style, но не
   identity: согласовать имя/email для Lenovo, не записывать реальные credentials
   в Nix. Повторно проверить личную настройку после перехода с live `nixos` на `samov`.
7. **Установка по официальному manual с существующим flake.** Следовать
   [Manual Installation, NixOS 26.05](https://nixos.org/manual/nixos/stable/#sec-installation-manual):
   сеть → разметка/форматирование → mounts → конфигурация → `nixos-install` → reboot.
   Его `/dev/sda`, swap 8 GB и systemd-boot — примеры, не замена согласованным
   ext4, swap 48 GiB и GRUB EFI. До destructive stage ещё нужны hardware/disk
   review, согласованный storage-aware build/install порядок и отдельное явное согласие на стирание
   проверенного SSD. Для разметки использовать проверенную декларацию Disko из
   обновлённого lock; ручной partition/format/mount второй раз не выполнять.
   Сверить `/mnt`, `/mnt/boot` и swap; получить hardware configuration на целевых
   mounts. При Disko повторный scan можно вывести командой
   `sudo nixos-generate-config --root /mnt --show-hardware-config --no-filesystems`:
   только hardware output, без перезаписи существующего flake и без повторной
   генерации управляемых Disko файловых систем. Нужные initrd/platform modules включить в flake, не копировать live
   filesystems и не дублировать storage declarations Disko с конфликтующими UUID.
   Сгенерированный пример `configuration.nix` не заменяет существующий flake.
   Перед install перепроверить конечную композицию с реальными hardware settings;
   команда `nixos-install --flake` должна указывать именно reviewed checkout и
   конечный output `laptop` после передачи имён, без старого guard и без изменения lock.
   Проверить способ входа и пароль перед reboot, затем загрузку без USB.
   Live SSH после reboot не сохранится: установленный host не включает SSH server.
   До standalone HM нет управляемого пользовательского Hyprland/UWSM config;
   при проблеме tty1 войти локально на Ctrl+Alt+F2 как `samov` с согласованным
   bootstrap-паролем, подключить сеть и применить HM под установленным пользователем.
   Задать личный пароль через `passwd`, не записывать его в flake.
   Standalone Home Manager применять отдельно. Сначала графика, устройства и
   suspend/hibernate, потом перенос основных данных. Успешная сборка не заменяет
   эти проверки. Команды на Lenovo выполняет пользователь по SSH с Acer;
   инструменты агента пока работают на Acer, собственный доступ агента не настроен.

## Сначала, до переноса данных

- [ ] **Загрузка и resume:** система повторно загружается с собственного диска;
      согласованный swap-раздел 48 GiB доступен для resume, старые Acer offset/UUID
      не перенесены. Размер swap сам по себе не доказывает работоспособность гибернации.
- [ ] **Сон и гибернация:** несколько suspend/resume и hibernate/resume от сети и
      батареи, затем с обычной рабочей нагрузкой. После возврата живы сессия,
      экран/GPU, ввод, сеть и звук; нет зависаний или потери несохранённого состояния.
- [ ] **Графика и экран:** RTX 5060 с подходящим open NVIDIA driver, Wayland,
      нужные режимы/масштаб экрана и внешний монитор, если используется; GPU-приложение
      действительно использует выбранный GPU. Acer Bus IDs и `open=false` не наследуются.
      Intel определяется с ожидаемым Xe driver, нет ошибок загрузки нужной firmware;
      проверить выбранную гибридную policy. При offload проверить dGPU runtime suspend
      в обычном idle без периодического `nvidia-smi`, также учитывая внешний экран.
- [ ] **Устройства и управление:** Wi-Fi, Bluetooth, динамики/микрофон, клавиатура,
      touchpad/жесты, яркость и нужные клавиши работают; Acer xremap не включён.
      Через привычный nmcli/nmtui подключиться к своей Wi-Fi сети; проверить
      автоподключение после reboot/resume и авторизацию при изменении system profile.
      Обе клавиши яркости регулируют встроенную панель без sudo; минимальный уровень
      остаётся пригодным для работы, после suspend/resume регулировка сохраняется.
      Blueman собран с `POLKIT=True`; агент Hyprland запускается с сессией и
      показывает нужные графические запросы. [Policy и безопасная проверка](polkit.md).
      Нужные выход/микрофон выбираются в pwvucontrol; звук остаётся рабочим после
      сна. Используемые наушники и DAW backend проверить отдельно без слепого tuning.
      Крышка и кнопки питания соответствуют выбранной policy, а не случайным defaults.
      Play/Pause управляет единственным MPRIS-плеером с другого workspace;
      отдельно проверить Chrome/YouTube и MPV. [Границы и приёмка](media-keys.md).
- [ ] **Питание и температура:** обычный idle и рабочая нагрузка на AC/батарее без
      необъяснимого перегрева, зависаний или throttling. Не копировать Acer
      performance/thermald вслепую; параметры менять по результатам, не ради эксперимента.
      PPD показывает доступные профили; значок Waybar отражает текущий профиль,
      ЛКМ/ПКМ переключают вперёд/назад без sudo, смена через другой клиент тоже видна.
      Hover правильно называет обе цели, включая переход через край списка;
      при отказе переключения текущий режим не отображается как успешно изменённый.

## Затем, с подготовленным окружением

- [ ] **Git/SSH после установки:** в установленной системе под `samov`, не в live
      под `nixos`, настроить доступ к GitHub. Создать отдельный SSH-ключ Lenovo
      (либо осознанно перенести существующий безопасным способом), добавить только
      публичную часть в GitHub. Приватный ключ остаётся вне Git и Nix store;
      SSH aliases/options и публичные `authorized_keys` можно декларировать отдельно,
      но они не заменяют приватный ключ для доступа к GitHub.
      Проверить SSH-аутентификацию и поменять URL в сохранённом checkout:

      ```fish
      ssh -T git@github.com
      git remote set-url origin git@github.com:samov0619-prog/nix-config.git
      git remote get-url origin
      ```

      Перед подтверждением нового host key сверить fingerprint с официальной
      документацией GitHub. Ожидается приветствие нужного GitHub account с сообщением
      об отсутствии shell access; успешный `ssh -T` GitHub завершает с кодом 1.
      При выбранном SSH alias использовать его вместо `github.com` и в проверке,
      и в URL. Повторный clone не нужен; смена URL сама не делает fetch/push.
      HTTPS допустимо оставить для чтения до готовности SSH. Отдельно проверить
      Git author name/email: SSH-аутентификация их не задаёт. Nix activation для
      ключа, его регистрации в GitHub и смены remote не требуется.
- [ ] **Повседневный workflow:** Hyprland/UWSM, раскладки, терминал, Neovim/direnv,
      браузеры и нужные приложения работают. HTTP/HTTPS открываются в Chrome;
      Firefox доступен вторым.
      Диалог выбора файла открывается/отменяется; отдельно, когда понадобится,
      проверить демонстрацию пустого тестового окна. [Границы portals](portals.md).
      `xdg-open` текстового файла открывает одно Kitty/Neovim окно с обычным UID,
      без второго терминала; [границы окружения и проверка](tui-launchers.md).
      Каталоги через `xdg-open` и Browse udiskie открываются в Kitty/Yazi,
      меню накопителей иерархическое; [проверка](removable-media.md).
      В Yazi c a a создаёт тестовый ZIP, открытие архива запускает распаковку;
      c a p → Esc/пустой пароль не создаёт архив, следующий обычный вызов
      не наследует пароль.
      [Безопасная приёмка и границы](archives.md).
      При переносе профилей отдельно проверить доступ
      к сохранённым паролям; новый HM `configPath` не считать миграцией данных.
      [Порядок и границы](browsers.md). Voice-dictate использует проверенный
      backend/GPU, не старый Acer `-dev 1`; уведомления и звук проверены в живой сессии.
      «Показать файл в папке» открывает Kitty/Yazi; `file:///` и `file://localhost/`
      выбирают тот же локальный файл. [Проверка FileManager1](../../pkgs/filemanager1-common/README.md).
      Диктовка печатает без дополнительного Enter, копирование сохранено;
      после распознавания временный WAV удалён. [Проверка диктовки](voice-dictate.md).
      Сборка после правки прошла по сообщению пользователя; живая проверка диктовки
      отложена до Lenovo: микрофон старого ноутбука сейчас проверить невозможно.
      Print → Esc не открывает Swappy; выбранная область открывается, Ctrl+s
      сохраняет в Screenshots, Ctrl+c позволяет вставить снимок после закрытия
      редактора. [Проверка скриншотов](screenshots.md); Print указан в F1.
      Проверить `kitty --version`: нужен Kitty ≥ 0.47.1 с upstream Fix #10058;
      F11 меняет тему открытого OpenCode в обе стороны без переоткрытия.
      Свежая установка с прежним `flake.lock` не обновляет Kitty автоматически.
      На 0.47.0 известен сбой отправки theme notifications; локальный backport
      сознательно удалён, ограничение Acer принято до обновления. Отдельный фикс
      startup-cache OpenCode 2.1.4 сохраняется: это другая подтверждённая ошибка.
      Проверить `gh --version`: upstream `gh 2.97.0` уже увеличил keyring timeout
      с 3 до 60 секунд. При наличии fix локальный patch не нужен; проверить первый
      обычный запрос с pinentry и warm retry. Acer reproduction уже записано,
      повторять его до обновления не требуется. [Диагноз и upstream fix](gh-keyring.md).
      Дисковый блок Waybar показывает I/O busy и свободно/всего для ФС домашнего
      каталога; tooltip — чтение/запись. После первого интервала нет ложного `0%`
      при недоступных счётчиках; блок помещается и читается в обеих темах.
      Старый `FREE` в Yazi отсутствует, навигация/preview и оконный контекст сохранены.
      Mason-инструменты запускаются с выбранными Python/Node; старые venv не считать
      переносимыми — проверить новую установку, а не только наличие Neovim binary.
      Выбранный VPN-режим работает, после отключения возвращается обычная сеть.
      Имя Zynthian Raspberry Pi в `*.local` разрешается, привычное подключение работает.
      Выбранный MTP workflow (пока запасной on-demand jmtpfs) переносит тестовый файл
      и корректно unmount без USB debugging. Автоматику проверить, если будет добавлена;
      udiskie не считать MTP browser. Обычный USB-носитель
      доступен через udiskie/tray и безопасно отключается после завершения записи.
      При обычной нагрузке оценить давление на RAM/swap без zram; не включать его
      только из-за низкой free RAM. Проверить weekly GC timer и policy 10/10 поколений
      без принудительной очистки истории ради теста; оценить свободное место после updates.
      Автологин на tty1 происходит один раз за загрузку и запускает UWSM;
      после logout требуется обычный вход. `sudo -k; sudo -v` запрашивает пароль
      пользователя. Hyprlock и fingerprint пока отсутствуют; гашение экрана Super+F12
      не считать блокировкой сессии. Улучшения входа разбирать отдельно на живом Lenovo.
- [ ] **Backup preflight до первого запуска сервера:** осознанно восстановлен/выбран
      локальный набор, проверены remote, доступ и квота. Первые sync/удаления проверять
      в отдельном тестовом назначении, не на исторической облачной папке; не допускать
      автоматический watcher к ней до готовности источника. Drive trash занимает квоту.
- [ ] **Minecraft/Packwiz:** после выбора heap для реальной нагрузки cold start
      target даёт serve → HTTP-ready → успешный update → Java; клиент подключается.
      Stop/restart завершают старые процессы, сохраняют мир и повторяют update;
      автозапуск остаётся выключенным, пока явно не понадобится. [Порядок](../../home/modules/minecraft/server/README.md#проверки-lifecycle-без-minecraft).
- [ ] **Backup и восстановление:** новый завершённый FTB ZIP отправляется целиком,
      ротация и полный sync дают ожидаемый набор, удаление использует Drive trash.
      Восстановить выбранный архив в отдельный каталог и проверить мир; оценить квоту
      с корзиной, не только пять видимых архивов. Проверка не должна затрагивать рабочий мир.

Отмечать пункт только после наблюдаемого результата; при сбое записать кратко симптом
и версию конфигурации без секретов/идентификаторов оборудования. Выбраны ext4, отсутствие
шифрования, swap-раздел 48 GiB, начальная работа без zram и weekly GC с 10/10 поколениями.
Начальный вход согласован как на Acer: автологин и парольный sudo, без Hyprlock;
fingerprint и улучшения аутентификации отложены до живой настройки.
Новые обязательные проверки добавлять сюда по итогам
аудита, не разносить в несколько конкурирующих списков.
