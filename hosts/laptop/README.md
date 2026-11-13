# Lenovo: установка и обслуживание

ThinkBook 16 G8+ IPD (21VJ), Core Ultra 7 356H / Intel Panther Lake + RTX 5060 Laptop.
**Lenovo уже установлен и используется.** Раздел установки нужен только для
осознанной переустановки или воспроизведения на проверенном таком же оборудовании.
Ничего из разрушительных шагов не нужно выполнять для обычного обновления.

| Назначение | NixOS | Standalone Home Manager |
| --- | --- | --- |
| Lenovo | `laptop` | `samov-laptop` |
| Старый Acer | `laptop-old` | `samov-laptop-old` |

Композицию задаёт [flake.nix](../../flake.nix). **Не применять Lenovo outputs на Acer.**
Наличие файла не означает его включение: проверять imports и `modules` array.

- Этот файл — основной путь установки и повседневного применения.
- [Текущая приёмка](../../docs/laptop-audit/lenovo-checklist.md) — что уже принято,
  что наблюдать в обычной работе и что сознательно отложено.
- [История подготовки](../../docs/laptop-audit/lenovo-history.md) и
  [boot audit](boot-errors.md) — расследования и точные границы свидетельств,
  не обязательная последовательность поломок для новой установки.

## Что устанавливается сразу

- NixOS и HM stateVersion **26.05**; они применяются раздельно. Не повышать
  stateVersion как способ обновить пакеты.
- UEFI/GRUB EFI removable, GPT: ESP 512 MiB, **48 GiB swap**, остальное ext4.
  Root и swap без шифрования; resume идёт в swap-раздел, без Acer swapfile/offset.
- [Графика](graphics.nix): released `linux_latest` из отдельного `nixpkgs-kernel`,
  matching NVIDIA latest/open из unstable recipes, unstable linux-firmware.
  **Mesa 64/32-bit остаётся stable вместе с userspace/glibc**: unstable Mesa
  нельзя подставлять отдельно в stable Hyprland. PRIME: Intel `PCI:0:2:0`, NVIDIA
  `PCI:2:0:0`; приложения выбираются через `nvidia-offload`, не весь Steam/session.
- Lenovo finegrained RTD3 и backport для NVIDIA config-open; Bluetooth PM,
  PipeWire teardown, BlueZ/core portal и Amnezia readiness corrections уже входят
  в конфигурацию. Не нужно сначала ставить старый сломанный вариант.
  [Реестр fixes и условия удаления](../../docs/backports/README.md) сохраняют
  regression harnesses; конфликт patch сам по себе не доказывает upstream fix.
- PPD без TLP/auto-cpufreq/унаследованного thermald. Начально без zram;
  включение требует наблюдаемого давления на память, а не просто used swap.
  [Защита батареи](../../docs/laptop-audit/battery.md): Waybar 15%/2%, штатный
  UPower Hibernate на 2%, с native delay/fallback и без гарантии достаточности резерва.
- Hyprland/UWSM: eDP-2 3200×2000/165 Гц, scale 1.6 (2000×1250 logical),
  яркость через `intel_backlight`, крышка гасит только встроенную панель без сна.
  Внешние экраны имеют fallback, но ещё не приняты. Гашение — не блокировка сессии.
- [Hotkeys](../../home/linux/laptop/README.md): F8 touchpad, F9 ⭐ todo,
  Fn+F1 help, Fn+F11 theme, F10 screenshot. Нет Acer xremap или Smart Connect patch.
- [Waybar](../../home/linux/laptop/waybar/README.md): PPD cycle/tooltip,
  disk status и GPU sampling только по клику на 60 секунд, без idle NVIDIA polling.
- Shared GTK/Qt themes, portals Hyprland + GTK, графический polkit agent, UDisks2 /
  udiskie и [Browse в Kitty/Yazi](../../docs/laptop-audit/removable-media.md),
  включая отдельный MIME `inode/mount-point`. Не нужен launcher workaround.
- Браузеры, OpenCode, Neovim binary, devtools, Blender и Minecraft-клиентские
  приложения. Minecraft instance/server/backup watcher **не активированы**;
  личные профили, миры, Neovim/Lazy/Mason и секреты не возникают от HM switch.
- Weekly GC через общий системный service: **10 NixOS + 10 HM generations**.
  Это не гарантированный запас места; дополнительного user GC timer нет.
- Согласованный bootstrap: один autologin tty1 за boot, парольный sudo,
  без Hyprlock/fprintd/TPM unlock. Начальный пароль `samov` — публичный `changeme`;
  после входа заменить через `passwd`. `users.mutableUsers=true` сохраняет замену.
  Автологин и отсутствие шифрования — осознанные ограничения безопасности.

## Новая установка: 10 шагов

Команды ниже выполняет пользователь **на Lenovo**, не агент и не Acer. Примеры
написаны для Fish; официальный Minimal ISO может сначала открыть Bash. Не запускать
всю страницу одним скриптом: остановки перед стиранием и reboot обязательны.

### 1. Подготовить live USB и доступ к консоли

Взять официальный NixOS Minimal **x86_64 Linux** ISO, проверить checksum по его
странице загрузки. Запись образа стирает выбранную флешку: её identity проверяется
отдельно от внутреннего SSD; носитель с данными для этого не использовать.

Загрузиться в UEFI. Если этот ISO блокируется Secure Boot, согласовать только его
отключение; не удалять ключи, не очищать TPM, не менять storage/MUX mode и не
прошивать BIOS ради установки. Для существующей Lenovo-конфигурации Windows не
сохраняется; на другой установке это нужно решить до стирания.

Подключить питание и сеть через `nmtui`. Проверить:

```fish
test -d /sys/firmware/efi
uname -r
curl --fail --head --max-time 20 https://cache.nixos.org
```

Live kernel не обязан совпадать с устанавливаемым. Local console должна оставаться
доступной. SSH в live — только удобство, не обязательное условие и не доступ после reboot.

### 2. Получить Git checkout без переноса приватных ключей

Если Git/Fish отсутствуют, временно открыть их в live:

```fish
nix-shell -p git fish --run fish
```

Дальше — под обычным live-пользователем, обычно `nixos`:

```fish
git clone https://github.com/samov0619-prog/nix-config.git
cd nix-config
git rev-parse HEAD
git status --short
```

Push/clone и прочие Git network operations выполняет пользователь. Сверить HEAD
с выбранным reviewed commit; исходный checkout должен быть чистым. Публичный HTTPS
не требует SSH-ключа или Acer-specific alias. Git author identity не нужна для clone.

### 3. Зафиксировать inputs и проверить целевой конфиг

Устанавливать выбранный reviewed commit с его `flake.lock`. **Не делать полный
update автоматически только потому, что это новая установка.** Если выбран новый
набор inputs, обновление, patch review и целевые проверки завершить до Disko и
использовать один и тот же итоговый lock для разметки, NixOS и HM.

Сверить [hardware scan](hardware-configuration.nix), PCI IDs и разметку с реальным
железом. При отличиях остановиться и адаптировать конфигурацию, не подставлять
шаблон `desktop-next` или старый Acer. Выбранные лёгкие проверки из корня:

```fish
nix --extra-experimental-features 'nix-command flakes' eval --impure --json --option allow-import-from-derivation false --file hosts/laptop/tests/test-draft.nix
nix --extra-experimental-features 'nix-command flakes' eval --impure --json --option allow-import-from-derivation false --file hosts/laptop/tests/test-disko.nix
```

Это fixtures, не полная аппаратная или build-проверка. Старый deliberate install
guard снят после review; отсутствие guard не является разрешением стереть диск.

### 4. При необходимости подключить installer VPN

Если нужен AWG 3.1 до больших загрузок, использовать
[installer-vpn](../../pkgs/installer-vpn/README.md) с **отдельным peer** и native
`.conf`, вне checkout/store, mode 600. Не запускать один peer одновременно на Acer
и Lenovo. Пример имени профиля — `$HOME/lenovo.conf`:

```fish
nix --extra-experimental-features 'nix-command flakes' run --no-update-lock-file .#installer-vpn -- up "$HOME/lenovo.conf"
nix --extra-experimental-features 'nix-command flakes' run --no-update-lock-file .#installer-vpn -- status "$HOME/lenovo.conf"
ip -4 route get 1.1.1.1
curl --fail --head --max-time 20 https://cache.nixos.org
```

Нужны свежий handshake, ожидаемый route/DNS и рабочий HTTPS. Если установка идёт
по LAN SSH, проверить второе подключение; локальная консоль остаётся страховкой.
Bootstrap самого helper тоже требует downloads и места до появления VPN.
Если VPN не нужен, пропустить шаг. Это не настройка VPS и не установка GUI-клиента.

### 5. Проверить SSD и выбрать порядок хранения

```fish
lsblk -o NAME,SIZE,MODEL,TRAN,FSTYPE,MOUNTPOINTS
readlink -f /dev/disk/by-path/pci-0000:01:00.0-nvme-1
findmnt /nix/store
df -h /nix/store /tmp
```

В [disko.nix](disko.nix) выбран UMIS NVMe 1 TB по PCI topology path. Это **не серийная
identity**: каждый раз сверять модель, ёмкость, mounts и USB против внутреннего SSD.
Сохранить нужные данные и отдельно подтвердить стирание именно этого диска.

Live writable store может быть RAM-backed: при первой установке свободно было
около 14 GiB. **Не собирать обе полные closures в live RAM и не делать полный HM
build на тесном Acer как обязательный preflight.** Здесь выбран порядок:
небольшой bootstrap → согласованная разметка/mount → NixOS install в целевой store
→ reboot → HM на установленном SSD. Для предварительного полного build нужен
отдельно проверенный store с достаточным местом.

Штатный `nixos-install` из NixOS 26.05 использует `--store /mnt` для system build
и временный каталог на целевой ФС по умолчанию. Это проверено по
`nixpkgs/pkgs/by-name/ni/nixos-install/nixos-install.sh`, не новым install-прогоном.
Bootstrap inputs/evaluation всё ещё требуют live-места; если задан внешний TMPDIR,
проверить его размещение. Не добавлять bind-mount/workaround без конкретной нужды.

### 6. Только после отдельного согласия: Disko

**Следующая команда полностью стирает выбранный SSD. Не запускать на работающем
установленном Lenovo, Acer, флешке с данными или непроверенном диске.**

Из reviewed checkout в live, с повторной проверкой шага 5:

```fish
sudo nix --extra-experimental-features 'nix-command flakes' run --inputs-from . --no-update-lock-file disko -- --mode destroy,format,mount ./hosts/laptop/disko.nix
findmnt /mnt
findmnt /mnt/boot
swapon --show
df -h /mnt
```

`--inputs-from .` выбирает Disko этого lock, не независимый latest. Ожидаются
целевой ext4 root, ESP на `/mnt/boot` и 48 GiB swap. При несовпадении остановиться.
Не выполнять затем ещё раз ручные partition/format/mount из примера manual.
В запросе Disko `Type 'yes' to continue, anything else to abort:` ещё раз сверить
список устройств и только затем ввести ровно `yes`; не обходить подтверждение.
Если swap создан, но не активен, после проверки его identity включить существующий
раздел через `sudo swapon /dev/disk/by-partlabel/disk-main-swap` и повторить
`swapon --show`. Это не повторная разметка и не `mkswap`.

### 7. Сохранить checkout и установить NixOS

До reboot checkout должен оказаться на целевом диске. Ниже предполагается, что
`/mnt/etc/nixos` ещё **не существует**; если существует, сначала разобраться,
не сливать/перезаписывать его вслепую. Копируется только reviewed репозиторий,
не приватный VPN-профиль и не секреты live-пользователя:

```fish
sudo install -d /mnt/etc
sudo cp -a "$PWD" /mnt/etc/nixos
cd /mnt/etc/nixos
git rev-parse HEAD
git status --short
```

При необходимости показать hardware scan без файловых систем:

```fish
sudo nixos-generate-config --root /mnt --show-hardware-config --no-filesystems
```

Сверить его с конфигом; не перезаписывать flake сгенерированным `configuration.nix`
и не дублировать Disko filesystem/swap UUID. Любые изменения scan сначала review.
После сверки mounts, HEAD, lock и способа входа:

```fish
sudo nixos-install --no-update-lock-file --flake .#laptop
```

Это реальная сборка/установка на целевой диск, не evaluation. Проверить успешный
выход и установку загрузчика. Штатный installer может запросить root password;
это не меняет согласованный bootstrap пользователя `samov`.

До reboot проверить system profile и загрузчик:

```fish
readlink -f /mnt/nix/var/nix/profiles/system
sudo ls -lh /mnt/boot/EFI/BOOT/BOOTX64.EFI /mnt/boot/grub/grub.cfg
```

ESP с `umask=0077` требует sudo; Permission denied без него не доказывает поломку.
Если для первого HM после boot понадобится VPN, заранее сохранить helper closure,
GC root и private профиль по [bootstrap-инструкции](../../pkgs/installer-vpn/README.md#optional-retain-bootstrap-across-installed-boot).
Live tunnel и RAM store сами через reboot не переносятся. Без этой необходимости
копирование helper пропустить; установленному Lenovo оно не нужно.

### 8. Первый установленный boot: консоль, сеть, личный пароль

После успешной установки завершить live VPN через `down` с тем же профилем, если
он использовался, и перезагрузиться с SSD без USB. На этом месте live SSH/tunnel
не переносятся; установленный host **не включает SSH server**.

До standalone HM управляемого Hyprland/UWSM config ещё нет. Если tty1 не даёт
рабочего desktop, перейти на Ctrl+Alt+F2 и войти **как `samov`**, не live `nixos`.
Использовать согласованный bootstrap, затем:

```fish
passwd
nmtui
```

Подключить сеть и проверить cache HTTPS заново: live Wi-Fi credentials не считаются
перенесёнными. Не записывать новый пароль в Nix/Git. Для работы из пользовательского
checkout скопировать сохранённый репозиторий, если `$HOME/nix-config` ещё отсутствует:

```fish
cp -R /etc/nixos "$HOME/nix-config"
cd "$HOME/nix-config"
git rev-parse HEAD
git status --short
```

Повторный clone не нужен. Проверить owner/permissions при использовании другого
способа переноса; не обходить dubious ownership глобальным `safe.directory=*`.

### 9. Отдельно применить Home Manager

В установленной системе, под **`samov` без sudo**, из того же reviewed checkout:

```fish
nix run --inputs-from . --no-update-lock-file home-manager -- switch --flake .#samov-laptop
```

Это bootstrap CLI из зафиксированного input `home-manager`, не случайный registry
latest. HM установит также собственную команду `home-manager` для дальнейших switch.
Сборка теперь использует SSD установленной системы. Конфликты существующих личных
файлов сначала разобрать/сохранить, не удалять их ради activation.

После успешного HM войти в свежую graphical session. Не диагностировать отсутствие
desktop как неисправность GPU, пока этот отдельный шаг не выполнен. Использовать
согласованный графический Amnezia client; live `.conf` не является его импортированным
профилем автоматически и не должен лежать в checkout.

### 10. Приёмка и перенос личного окружения

Пройти [текущий checklist](../../docs/laptop-audit/lenovo-checklist.md), сохраняя
различие между declarations, реальным UI и непроверенными нагрузками. Изменения
яркости/режима, RTD3, hotkeys, MIME и UPower уже входят в текущую установку;
исторические обходы повторять не нужно.

После обычного успешного входа проверить Git identity и подготовить личный SSH-ключ
Lenovo, если нужен push. Регистрировать в GitHub только public key; fingerprint
сервера сверять с официальной документацией перед доверием. В установленной системе
пользователь может выполнить:

```fish
git config user.name
git config user.email
ssh -T git@github.com
git remote set-url origin git@github.com:samov0619-prog/nix-config.git
git remote get-url origin
```

GitHub приветствует нужный account и сообщает об отсутствии shell; успешная
аутентификация обычно завершает `ssh -T` кодом 1. Для личного alias использовать
его и в SSH, и в URL. HTTPS допустимо оставить для чтения; смена URL не делает fetch.

Перенос browser profiles/passwords, Neovim/Lazy/Mason, локальных проектов и секретов
проверяется отдельно. [Fish local-env](../../docs/laptop-audit/fish-local-env.md) —
unmanaged личный файл, не Nix input. Minecraft server/backup не включать до отдельного
data/remote/restore preflight. Не запускать GC ради проверки сразу после установки.

## Обычные изменения на уже установленном Lenovo

Работать из пользовательского checkout. Review/build/application выполняет пользователь;
NixOS и HM не заменяют друг друга:

```fish
# Только системные изменения: hosts/, system services, kernel/driver.
sudo nixos-rebuild switch --flake .#laptop

# Только пользовательские изменения: home/, hotkeys, Waybar, MIME, приложения HM.
home-manager switch --flake .#samov-laptop
```

Для документации activation не требуется. Если менялись обе группы — применить обе.
После kernel/NVIDIA change нужен reboot для загрузки нового модуля: успешный switch
не означает, что уже работает новый kernel/driver. Проверить `uname -r`,
`readlink -f /run/current-system` и `/run/booted-system`; не выгружать рабочий драйвер
и не дёргать rebind ради ускорения проверки.

Целевое обновление input и проверку без switch пользователь запускает так:

```fish
nix-flake-update-verify --hosts laptop --input nixpkgs
```

Для ядра отдельно выбрать `--input nixpkgs-kernel`, для проверки текущего lock —
`--no-update`. Helper **делает builds**, не activation; не запускать `--hosts all`
ради Lenovo. Прямой `nix flake update` обходит backport hook; после него нужен
review по [реестру](../../docs/backports/README.md), не автоматическое удаление fixes.

Включение finegrained само по себе не доказывает RTD3: проверять пассивные sysfs/proc
свидетельства и отдельный offload/idle цикл по [graphics audit](../../docs/laptop-audit/graphics.md).
Не возвращать постоянный `nvidia-smi` polling. Установленные улучшения аудио/VPN,
сна и безопасности не менять ради оставшихся сообщений журнала без измеренного дефекта.

Этот гайд сверен с текущими declarations и сохранённой приёмкой. Нового install,
build, destructive command или firmware action при его обновлении агент не выполнял.
