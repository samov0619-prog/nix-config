# Локальные имена устройств: Avahi/mDNS

[Каталог](README.md) · [Решения](feedback.md)

Пользователь подтвердил нужный сценарий: подключение к Raspberry Pi с Zynthian OS
по локальному имени. Avahi сохраняется; настройка вынесена в общий
[hosts/profiles/mdns.nix](../../hosts/profiles/mdns.nix).

Flake явно подключает его к `laptop-old`, `desktop`, `laptop`, `desktop-next`.
Для Acer и Lenovo это сохранение прежнего поведения; для обоих desktop outputs —
добавление. VPS и installer не импортируют модуль, Home Manager и Mac не меняются.

- `enable = true`: штатная системная служба Avahi.
- `nssmdns4 = true`: приложения могут разрешать IPv4-имена `*.local` через NSS.
- `openFirewall = true`: штатный модуль NixOS открывает UDP 5353 для mDNS.
- `publish.enable = false`: обнаруживаем другие устройства, не публикуем собственные
  адреса/службы. Это прежний default, теперь явно записанный.
- `services.resolved.settings.Resolve.MulticastDNS = false`: единственный mDNS
  stack — Avahi. На установленном Lenovo одновременно отвечали Avahi и resolved,
  и Avahi предупреждал о ненадёжном обнаружении. Обычный DNS и VPN DNS через
  resolved сохраняются; включение самой службы этот модуль не меняет.
- Штатные `wideArea = false`, `reflector = false` и запрет point-to-point интерфейсов
  сохраняются. Отдельного relay, списка устройств или статических IP нет.

mDNS обычно работает внутри одного локального сегмента. Изоляция клиентов Wi-Fi,
разные VLAN или отсутствие объявления имени со стороны Pi могут мешать; эта
настройка не обещает обнаружение через VPN или интернет. Она также не включает
на Raspberry Pi SSH, web UI или другие службы.

## Проверка и применение

Выборочная offline evaluation без сборок:

```fish
nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/profiles/tests/test-mdns.nix
```

Проверены merged Avahi/NSS/firewall/autostart attributes и отключение второго
mDNS stack в resolved для четырёх workstation
outputs и реальные flake module lists, исключающие server/installer. Это не полная
сборка и не проверка связи с Raspberry Pi. Службы/сеть агентом не менялись.

1. После review применить на соответствующей машине NixOS:
   `sudo nixos-rebuild switch --flake .#laptop` (на Acer — `.#laptop-old`, desktop — `.#desktop`).
   Отдельный HM switch для этого изменения не нужен. `*-next` пока не применять.
2. В одной сети с включённым Pi проверить `systemctl is-active avahi-daemon.service`
   и `getent ahostsv4 zynthian.local`, подставив реальное имя устройства.
   Ожидаются `active` и IPv4-адрес Pi.
3. Открыть привычный адрес Zynthian и проверить доступ. Разрешение имени отдельно
   не доказывает работу web UI/SSH; при проблеме сначала проверить то же подключение
   по известному IP, не отключая firewall целиком.
4. После перезагрузки `resolvectl mdns` должен показывать глобальное `no`,
   а `journalctl -b -u avahi-daemon --no-pager` — не содержать предупреждения
   `Detected another ... mDNS stack`. Проверить обычный HTTPS и доступ через
   привычный VPN. На Lenovo после пользовательского применения/перезагрузки
   подтверждены global/link `no`, активный Avahi и отсутствие duplicate-stack
   warning. LAN-discovery и обычный/VPN DNS/HTTPS отдельно ещё не проверены.
