# Server Configuration Instructions

## Goals

- Run AmneziaWG 2.0, AdGuard Home, and NaiveProxy without Docker.
- Use AmneziaVPN 4.8.21+ for AmneziaWG and Karing for NaiveProxy.
- Keep VPN credentials and generated profiles outside Git and the Nix store.
- Publish client profiles through a single-key, SFTP-only account.
- Select every host feature exclusively through module imports in `flake.nix`.

## Service Layout

- `hosts/server/default.nix` imports the hardware, VPN, AdGuard, Caddy, and
  SFTP modules and owns the host-wide firewall, static WAN network, SSH, Nix,
  boot settings, and the `samov` sudo policy.
- `hosts/server/hardware.nix` loads `virtio_pci` and `virtio_net` in the
  initrd. Keep both for VirtIO-based VPSes: the WAN interface must exist before
  the normal system can configure its address.
- `hosts/server/settings.nix` contains all provider-specific network values:
  disk, public endpoint, WAN interface, address, prefix, gateway, DNS, and
  optional proxy/SFTP values. Do not hardcode these in `default.nix`.
- `hosts/server/vpn.nix` owns forwarding, NAT, and the AmneziaWG interface.
- `hosts/server/adguard.nix` declares AdGuard filters based on
  `adguardhome-backup-2026-07-20-231323.tar.gz`. Do not import its old Docker
  upstream, administrator hash, statistics, or query log.
- `hosts/server/proxy.nix` runs Caddy with the NaiveProxy `forwardproxy`
  plugin and ACME TLS.
- `hosts/server/sftp.nix` exposes `/srv/vpn-download/files` through a
  chrooted, SFTP-only account with exactly one configured SSH key.
- `home/core-set` provides the shared shell and CLI foundation, including Fish,
  Atuin, Zoxide, Yazi, Git, and development tools.
- `home/apps/opencode` and `home/apps/aider` are optional desktop/laptop apps.
  They are intentionally excluded from `samov-server`: OpenCode's Node build
  and Aider's full dependency set consume unnecessary VPS disk space.
- `home/linux/server/default.nix` supplies the server development environment.
- `flake.nix` imports the reusable Minecraft server module on every Linux
  host. Only desktop and laptop additionally import `home/apps/minecraft`.

## Secrets And Profiles

- Keep runtime state under `/var/lib/amneziawg` and `/var/lib/naiveproxy`.
- Do not commit private WireGuard keys, NaiveProxy passwords, or generated
  profiles.
- Generate AmneziaWG profiles as `.conf` files for AmneziaVPN.
- Generate Karing/sing-box JSON for NaiveProxy.
- Publish copies only to `/srv/vpn-download/files`; the SFTP user cannot get a
  shell, forward ports, or access any other path.
- The SFTP key is an operator credential, not a per-client delivery mechanism:
  it can read every generated profile in that directory. Remove downloaded
  profiles promptly or introduce separate credentials and directories before
  sharing access with anyone else.

## Client Routing And DNS

- `awg-add-client` emits a full IPv4 tunnel (`AllowedIPs = 0.0.0.0/0`). This
  is intentional: AmneziaVPN implements split tunneling on the client; an
  AmneziaWG server transports packets and cannot identify a desktop or mobile
  application after encryption.
- The supported split-tunneling matrix is maintained in the
  [AmneziaVPN documentation](https://docs.amnezia.org/documentation/instructions/vpn-split-tunneling):
  Android supports IP and app allow/bypass lists; Windows supports both IP
  modes and app bypass; Linux, macOS, and iOS support only both IP modes.
  Use client settings rather than editing the generated server profile.
- Amnezia IP rules are IPv4-only. Domain entries are resolved once to IPv4
  addresses and are not refreshed automatically. Do not add a subnet containing
  the configured `publicEndpoint` to a client split list or the VPN handshake
  can be routed outside the tunnel.
- DNS for AWG clients is AdGuard Home at `10.66.0.1`. Keep AmneziaDNS disabled
  and set `10.66.0.1` as the connection's custom primary DNS server in
  AmneziaVPN. On Linux, confirm `resolvectl status` shows that address on
  `amn0`, then test with `resolvectl query example.com`.

## Configuration Branches

Every branch is selected in `hosts/server/settings.nix` or by an explicitly
nullable setting. The NixOS evaluation does not probe a live VPS: run the
preflight checklist first, record verified facts, then select a branch.

| Choice | Select when | Effect | Trade-off |
| --- | --- | --- | --- |
| `network.ipv4.mode = "static"` | The provider gave a fixed IPv4 address, prefix, and gateway. | Declares the address and route exactly. | Most predictable, but a provider network change requires a config update. |
| `network.ipv4.mode = "dhcp"` | The provider explicitly supports DHCP on the target NIC. | Lets DHCP set IPv4 address, route, and DNS. | Portable across changing leases, but unsuitable for an unverified static VPS setup. |
| `network.ipv6 = null` | No global IPv6 address and default route are present. | Server and generated profiles remain IPv4-only. | Safest when IPv6 is unavailable, but dual-stack clients can bypass the VPN over IPv6. |
| `network.ipv6 = { ...; egress = "nat66"; }` | The VPS has a global WAN IPv6 but no provider-routed client prefix. | Clients use private ULA IPv6; server translates it to its WAN IPv6. | Works with a single WAN address, but NAT66 obscures client IPv6 addresses and is less direct. |
| `network.ipv6 = { ...; egress = "routed"; }` | The provider routes `vpnNetwork` to this VPS. | Clients use that routed prefix without translation. | Preserves end-to-end IPv6, but requires a provider-confirmed route; selecting it without one breaks IPv6 egress. |
| `publicEndpoint = null` | AWG must be intentionally absent. | Disables AWG interface, NAT, client generator, and UDP listener. | Reduces attack surface, but no VPN or AWG DNS access exists. |
| `publicEndpoint = "<IPv4>"` | The VPS has a reachable public IPv4 endpoint. | Enables AWG, NAT, and `awg-add-client`. | Requires provider firewall and NixOS UDP port access. |
| `domain = null` or `acmeEmail = null` | NaiveProxy is not ready. | Leaves Caddy, ACME, TCP 80/443, and `naive-add-client` disabled. | Safe default; no NaiveProxy connection is available. |
| Both `domain` and `acmeEmail` set | DNS A/AAAA records already point at the VPS and an ACME email is available. | Enables Caddy and NaiveProxy with ACME TLS. | Public HTTP/HTTPS exposure; certificate issuance and profile connection need validation. |
| `sftpAuthorizedKey = null` | SFTP delivery is intentionally not configured. | The SFTP account has no login key. | No profile download access until a key is added. |
| `sftpAuthorizedKey = "ssh-..."` | One trusted operator must download generated profiles. | Enables that key for the restricted SFTP account. | This principal can read every profile in the shared directory, not only its own. |

The Disko layout is deliberately not a branch: it creates both BIOS and EFI
boot partitions, so it is portable across those firmware modes. `diskDevice`
is always a manual confirmation because choosing it automatically can erase the
wrong disk.

## IPv6 Policy

- The current server and generated profiles are IPv4-only. A dual-stack client
  can therefore reach IPv6 destinations outside this VPN. This is a privacy
  gap for a full-tunnel connection, not an Amnezia IP-split feature.
- Do not add `::/0` to profiles until the VPS has a routed IPv6 prefix and the
  server has IPv6 forwarding, firewall, DNS, and egress configured. Without an
  IPv6 uplink it would blackhole IPv6 rather than provide IPv6 VPN access.
- Before implementing IPv6, record the provider allocation on the VPS with
  `ip -6 -br address` and `ip -6 route`. The design must assign an AWG ULA
  subnet, route or NAT66 it through the provider prefix, expose AdGuard on its
  IPv6 AWG address, and then add IPv6 client addresses and `::/0` to new
  profiles.

### Dual-Stack Settings

- `settings.nix` selects networking explicitly. Keep `network.ipv6 = null` for
  an IPv4-only provider. After preflight confirms a global address and route,
  replace it with a verified static allocation:

  ```nix
  network.ipv6 = {
    wanAddress = "2001:db8:100::2";
    wanPrefixLength = 64;
    gateway = "fe80::1";
    vpnNetwork = "fd42:1234:5678:1";
    vpnPrefixLength = 64;
    egress = "nat66";
  };
  ```

  `vpnNetwork` is a `/64` without the trailing `::` or CIDR suffix. Use
  `egress = "nat66"` when the provider supplies only WAN IPv6; use
  `egress = "routed"` only when the provider routes `vpnNetwork` to this VPS.
  Static IPv6 is deliberately explicit because DHCPv6 and router-advertisement
  provider setups need their own tested branch.
- Existing AWG runtime state is mutable and never rewritten automatically.
  When changing an installed server from IPv4-only to dual-stack, reissue and
  replace all client profiles; they need IPv6 addresses and `::/0`. A future
  migration helper must update both the persistent AWG config and live peers
  before it can safely automate that transition.

## Operations And Recovery

- Back up and restore-test mutable server state off-host: `/var/lib/amneziawg`,
  `/srv/vpn-download/files`, `/var/lib/private/AdGuardHome`, and, when enabled,
  `/var/lib/naiveproxy`. Those paths contain credentials or settings that are
  intentionally outside Git and the Nix store.
- `awg-add-client` and `naive-add-client` currently create credentials only.
  There is no supported list, revocation, or expiry helper yet; add that
  lifecycle before issuing profiles to multiple people.
- The server retains five NixOS generations for up to 14 days. Updates are
  deliberately manual: evaluate locally, deploy through the SSH alias, check
  `wg-quick-awg0`, AdGuard, and SSH, then retain an off-host backup before
  relying on a rollback.

## Minecraft

- The reusable server module contains the Packwiz, Fabric, and backup-sync
  implementation. It remains inactive while `minecraft.server` is null.
- `home/apps/minecraft` supplies the current paths, memory, Packwiz, JDK, and
  FreesmLauncher.
- To enable Minecraft on the server, add `./home/apps/minecraft` to its module
  list in `flake.nix`; no host flags are used.

## VPS Installation

### Preflight Checklist

1. Boot the provider rescue system and run the read-only inventory from the
   workstation checkout:

   ```bash
   ssh root@<rescue-host> 'sh -s' < hosts/server/preflight.sh
   ```

   The installed server also provides the same `server-preflight` command.
   It reports disks, NICs, IPv4, and IPv6 but deliberately never writes
   `settings.nix` or selects a target disk.
2. Confirm the installation disk manually from the `Block devices` section.
   Never infer it from its name: `/dev/vda`, `/dev/sda`, and NVMe names vary by
   provider and rescue image.
3. Record the NIC, public IPv4 address/prefix, default IPv4 gateway, and DNS
   from the IPv4 sections. Confirm them with the provider control panel when
   the rescue configuration is DHCP or NAT-based.
4. Record global IPv6 addresses, routed prefixes, and the default IPv6 route.
   Link-local `fe80::/64` alone is not usable for an IPv6 VPN egress. Leave
   IPv6 disabled in the server configuration when no routed allocation exists.
5. Verify a second rescue SSH connection with the intended key before any
   destructive command. Keep the first rescue shell open until the installed
   system accepts the `samov` login.

1. Set all provider-specific values in `hosts/server/settings.nix`. The probe
   can identify candidates but cannot safely automate this step across
   providers. Example for
   the installed VPS: `/dev/vda`, `ens3`, `94.103.3.166/24`, and gateway
   `94.103.3.1`. These values are examples, not defaults for a different VPS.
2. Build and validate locally before destructive deployment:

   ```bash
   nix build .#nixosConfigurations.server.config.system.build.toplevel --no-link
   nix flake check --no-build 'path:.'
   ```

3. From this repository on another machine, install with:

   ```bash
   nix run github:nix-community/nixos-anywhere -- \
     --flake .#server root@<rescue-host>
   ```

   This erases `settings.nix.diskDevice`. Do not interrupt after Disko begins.

4. After the final reboot, log in as `samov` using its SSH key. SSH listens on
   port `17431`; password and keyboard-interactive authentication are disabled.
   `samov` has declarative passwordless sudo to support remote deployments.
5. Apply the standalone Home Manager profile from an up-to-date checkout:

   ```bash
   home-manager switch --flake .#samov-server
   ```

   The server's initial NixOS closure contains no Git or Home Manager command.
   Bootstrap them with `nix-shell -p git --run 'git clone <url> ~/nix-config'`
   and `nix run github:nix-community/home-manager/release-26.05 -- ...`.
   Do not add OpenCode or Aider to the server profile just to bootstrap it.

6. Access initial AdGuard setup only through:

   ```bash
   ssh -p 17431 -L 8008:127.0.0.1:8008 samov@<server>
   ```

7. Generate profiles with the installed AWG and Naive client helper commands,
   then download them through SFTP.

## Remote Updates And Recovery

- Deploy a server configuration from the workstation with:

  ```bash
  nixos-rebuild switch --flake .#server --target-host samov@<server-ssh-alias> --sudo
  ```

- This remote NixOS deployment builds on the workstation, transfers the
  closure over SSH, and activates it through `samov`'s declarative
  passwordless sudo. It avoids using VPS disk space for a system build.
- Configure `<server-ssh-alias>` in `~/.ssh/config` with the server hostname,
  port `17431`, the `samov` user, and its matching identity file. Do not pass
  `host:port` to `--target-host`: `nix-copy-closure` does not use that port.
- For Home Manager, update the VPS checkout and run the activation on the VPS:

  ```bash
  cd ~/nix-config
  git pull
  nix run github:nix-community/home-manager/release-26.05 -- \
    switch --flake .#samov-server
  ```

- New `samov` SSH sessions use Fish. Home Manager supplies the Fish
  integration for Atuin and Zoxide, so `z <directory>` is available after its
  activation. Reconnect after changing the login shell or Home Manager profile.

- A healthy post-reboot check is:

  ```bash
  ssh -p 17431 samov@<server> \
    'ip -br address; ip route; lsmod | grep -E "virtio_(pci|net)"; systemctl is-active sshd'
  ```

- Expected state for a VirtIO VPS: the configured WAN interface is `UP` with
  its static address, its configured gateway is the default route, both VirtIO
  modules are loaded, and `sshd` is `active`.
- If a new provider uses another NIC driver or network layout, update
  `hardware.nix` and `settings.nix` before installing. Do not use DHCP as an
  unverified fallback for the static target configuration.
- The provider VNC/GRUB console is an out-of-band recovery path, not a normal
  administration method. Do not persist ad-hoc commands, temporary SSH daemons,
  or modified `/etc/sudoers`; represent permanent behavior in Nix instead.

## Validation

- Run `nix flake check` and evaluate both server configurations before deploy.
- Confirm `wg-quick-awg0`, `adguardhome`, and `sshd` are healthy. Confirm
  `caddy` only after both `domain` and `acmeEmail` are set.
- Confirm public DNS and the AdGuard UI are unreachable.
- Confirm AmneziaVPN imports and handshakes the AWG profile.
- Confirm Karing imports and uses the Naive profile.
- Confirm the SFTP account cannot obtain a shell or access paths outside its
  profile directory.
