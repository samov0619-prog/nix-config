# Server Configuration Instructions

## Goals

- Run AmneziaWG 3.1, AdGuard Home, and NaiveProxy without Docker.
- Use a current AmneziaVPN release with AmneziaWG 3.1 support and Karing for
  NaiveProxy.
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
- `pkgs/amneziawg-3.1/` pins the matched AWG 3.1.20260812 kernel module and
  tools. Both are server-only overrides because `wg-quick` needs the module
  from `boot.kernelPackages` and the matching `awg` userspace tools.
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
- `home/linux/server/default.nix` supplies server diagnostics and the
  Tree-sitter parser build toolchain. It deliberately does not install language
  runtimes or deploy a Neovim configuration.
- `flake.nix` imports the reusable Minecraft server module on every Linux
  host. Only desktop and laptop additionally import `home/apps/minecraft`.

## AmneziaWG 3.1

- The server pins the mutually released AWG 3.1.20260812 kernel module and
  userspace tools. Do not update only one: the kernel protocol engine and
  `awg` parser must support the same field set.
- Fresh bootstrap creates the AWG3.1 Header Protection profile: equal
  `S1`-`S4 = 32`, `H1`-`H4 = 1`-`4`, a freshly generated shared
  `HeaderProtectionKey`, `RandomTrailers = on`, and `DisableCookies = on`.
  Every generated client copies those exact interface fields.
- Legacy AWG2 `Jc`/`Jmin`/`Jmax`, two-slot `S1`/`S2`, and randomized
  `H1`-`H4` are preserved only as comments in `vpn.nix`; they are not active
  or emitted into profiles.
- No AWG profile has been issued for this fresh VPS. Generate profiles only
  after the first boot verifies `wg-quick-awg0` is active. Clients must use a
  current AmneziaVPN build that supports AWG3.1 fields.

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

- `awg-add-client` emits the canonical full-tunnel route
  `AllowedIPs = 0.0.0.0/0, ::/0`. This is intentional: AmneziaVPN implements
  split tunneling on the client; an AmneziaWG server transports packets and
  cannot identify a desktop or mobile application after encryption.
- Android's imported-profile UI recognizes client-owned site/IP split tunneling
  only with that exact full-tunnel route. Do not add service or LAN subnets to
  this client `AllowedIPs` line: Amnezia will treat it as profile-defined
  server routing and disable client site/IP split controls.
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

### AmneziaVPN Client DNS

1. Open the connection settings, disable **Use AmneziaDNS**, then open **DNS
   servers**.
2. Set **Primary DNS** to `10.66.0.1`. Leave secondary DNS empty unless a
   deliberate fallback is required: a public fallback can bypass AdGuard when
   the VPN DNS is unreachable.
3. Save, disconnect, and reconnect the profile. On Linux, `resolvectl status`
   must show `10.66.0.1` on `amn0`; test with `resolvectl query example.com`.

## Server Neovim

- Home Manager installs only `neovim-unwrapped`. The Neovim repository, its
  `server-build` branch, Lazy plugins, Tree-sitter parsers, and any Mason state
  are manual user state under `~/.config/nvim` and `~/.local/share/nvim`.
- Keep the server on the lightweight `server-build` branch. Do not add the
  repository as a flake input or deploy it through `xdg.configFile`: plugin and
  language-server installation is intentionally outside the Nix store.
- After Home Manager activation on a fresh VPS, clone that branch manually and
  then initialize Lazy and any manually managed editor state as needed:

  ```bash
  git clone --branch server-build https://github.com/samov0619-prog/nvim ~/.config/nvim
  nvim
  ```
- Tree-sitter parser builds require `gcc`, `tree-sitter`, `curl`, and `tar`.
  They do not require Node, JDK, Go, Python, or GNU Make. The server Home
  Manager profile includes the required parser tools explicitly.

## Configuration Branches

Every branch is selected in `hosts/server/settings.nix` or by an explicitly
nullable setting. The NixOS evaluation does not probe a live VPS: run the
preflight checklist first, record verified facts, then select a branch.

| Choice | Select when | Effect | Trade-off |
| --- | --- | --- | --- |
| `network.ipv4.mode = "static"` | The provider gave a fixed IPv4 address, prefix, and gateway. | Declares the address and route exactly. | Most predictable, but a provider network change requires a config update. |
| `network.ipv4.mode = "dhcp"` | The provider explicitly supports DHCP on the target NIC. | Lets DHCP set IPv4 address, route, and DNS. | Portable across changing leases, but unsuitable for an unverified static VPS setup. |
| `network.ipv6 = null` | No global IPv6 address and default route are present. | Server forwards IPv4 only; client profiles route `::/0` into AWG. | Prevents IPv6 bypass and keeps Android split controls available, but IPv6 destinations cannot work until VPS IPv6 exists. |
| `network.ipv6 = { ...; egress = "nat66"; }` | The VPS has a global WAN IPv6 but no provider-routed client prefix. | Clients use private ULA IPv6; server translates it to its WAN IPv6. | Works with a single WAN address, but NAT66 obscures client IPv6 addresses and is less direct. |
| `network.ipv6 = { ...; egress = "routed"; }` | The provider routes `vpnNetwork` to this VPS. | Clients use that routed prefix without translation. | Preserves end-to-end IPv6, but requires a provider-confirmed route; selecting it without one breaks IPv6 egress. |
| `swapMiB = 2048` | VPS RAM is small or local parser/build tasks can peak above RAM. | Creates a 2 GiB `/swapfile` on ext4 root. | Slower than RAM when used, but prevents OOM; consumes 2 GiB disk capacity. |
| `swapMiB = null` | RAM is ample and no memory-heavy local work is expected. | Creates no disk swap. | Leaves all headroom to `/nix/store`, but a large compiler process can be OOM-killed. |
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

- The current server forwards IPv4 only. Generated profiles nevertheless route
  `::/0` through AWG to prevent an IPv6 privacy bypass and to preserve Android
  client split controls. Until the VPS has IPv6 egress, IPv6 destinations will
  fail or clients will fall back to IPv4.
- Do not expect IPv6 connectivity until the VPS has a routed IPv6 prefix and
  the server has IPv6 forwarding, firewall, DNS, and egress configured.
- Before implementing IPv6, record the provider allocation on the VPS with
  `ip -6 -br address` and `ip -6 route`. The design must assign an AWG ULA
  subnet, route or NAT66 it through the provider prefix, expose AdGuard on its
  IPv6 AWG address, and then make the existing `::/0` client route functional.

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
  replace all client profiles; they need IPv6 addresses. A future migration
  helper must update both the persistent AWG config and live peers before it
  can safely automate that transition.

## Operations And Recovery

- Back up and restore-test mutable server state off-host: `/var/lib/amneziawg`,
  `/srv/vpn-download/files`, `/var/lib/private/AdGuardHome`, and, when enabled,
  `/var/lib/naiveproxy`. Those paths contain credentials or settings that are
  intentionally outside Git and the Nix store.
- `awg-add-client` and `naive-add-client` currently create credentials only.
  There is no supported list, revocation, or expiry helper yet; add that
  lifecycle before issuing profiles to multiple people.
- The server runs daily GC and keeps two generations. `nix-gc-env` cleans
  system/root profiles, while `samov-profile-gc` cleans the Home Manager and
  user Nix profiles before the store GC. Updates are deliberately manual:
  evaluate locally, deploy through the SSH alias, check `wg-quick-awg0`,
  AdGuard, and SSH, then retain an off-host backup before relying on a
  rollback.
- `home/core-set` is the small common CLI base. Development packages are
  explicit flake modules: `nix-authoring.nix`, `go.nix`, `node.nix`,
  `python.nix`, `devenv.nix`, `native-build.nix`, `treesitter.nix`, and
  `devtools/github.nix`. Desktop, laptop, and mac import all of them; server
  imports only `native-build.nix` and `treesitter.nix`.

## Minecraft

- The reusable server module contains the Packwiz, Fabric, and backup-sync
  implementation. It remains inactive while `minecraft.server` is null.
- `home/apps/minecraft` supplies the current paths, memory, Packwiz, JDK, and
  FreesmLauncher.
- To enable Minecraft on the server, add `./home/apps/minecraft` to its module
  list in `flake.nix`; no host flags are used.

## VPS Installation

### Temporary Debian Or Rescue SSH

1. Use the provider-issued root password only to add the workstation public key
   to the temporary Debian or rescue host. From the workstation:

   ```bash
   ssh-copy-id -i ~/.ssh/id_ed25519_samov0619.s.rutest.pub -p 22 root@<rescue-host>
   ssh -i ~/.ssh/id_ed25519_samov0619.s.rutest \
     -o IdentitiesOnly=yes -o PreferredAuthentications=publickey \
     -p 22 root@<rescue-host> true
   ```

   Replace the key path when another public key is intended. If the provider
   blocks root password SSH, add that public key through its console or rescue
   panel instead. The verification intentionally prompts for the private-key
   passphrase. Use `ssh-add ~/.ssh/id_ed25519_samov0619.s.rutest` before adding
   `BatchMode=yes` to a non-interactive check.
2. Keep separate SSH aliases instead of changing one alias between temporary
   Debian and installed NixOS:

   ```sshconfig
   Host vps-bootstrap
     HostName <server-ip>
     User root
     Port 22
     IdentityFile ~/.ssh/id_ed25519_samov0619.s.rutest
     IdentitiesOnly yes

   Host vps-new
     HostName <server-ip>
     User samov
     Port 17431
     IdentityFile ~/.ssh/id_ed25519_samov0619.s.rutest
     IdentitiesOnly yes
   ```

   Use `root@vps-bootstrap` for `nixos-anywhere`; use `samov@vps-new` after
   the NixOS reboot. An explicit `-i` command is independent of SSH config and
   is the right key-installation verification when several keys exist.
3. Keep the temporary SSH service on its provider default port, usually 22.
   Do not disable password login or change the port before installation: the
   installer needs this temporary root connection and the disk will be erased.
   Keep the original password or console session open until NixOS accepts the
   `samov` key on port 17431.
4. The installed NixOS configuration performs the permanent SSH hardening:
   `samov` key access on port 17431, no password or keyboard-interactive login,
   and root login only by key. The Debian password is not copied into NixOS.

### Preflight Checklist

1. On the temporary Debian or rescue host, run the read-only inventory from
   the workstation checkout:

   ```bash
   ssh vps-bootstrap 'sh -s' < hosts/server/preflight.sh
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
5. Verify a second key-based root SSH connection before any destructive
   command. Keep the first rescue shell open until the installed system accepts
   the `samov` login.

1. Set all provider-specific values in `hosts/server/settings.nix`. The probe
   can identify candidates but cannot safely automate this step across
   providers. Example for
   the installed VPS: `<disk>`, `<NIC>`, `<IPv4>/<prefix>`, and `<gateway>`.
   These values are examples, not defaults for a different VPS.
2. Validate the exact committed workstation checkout before destructive
   deployment:

   ```bash
   git status --short
   git pull --ff-only
   nix flake check --no-build
   nix build .#nixosConfigurations.server.config.system.build.toplevel --no-link
   ```

   `git status --short` must be empty. Skip `git pull --ff-only` when the
   checkout is already the intended revision. `nix flake check` evaluates every
   host; `nix build` evaluates and builds the exact server closure locally, so
   deployment transfers an already verified result instead of building on the
   small VPS disk.

3. From this repository on another machine, install with:

   ```bash
   nix run github:nix-community/nixos-anywhere -- \
     --flake .#server root@vps-bootstrap
   ```

   This erases `settings.nix.diskDevice`. Do not interrupt after Disko begins.

4. After the final reboot, log in as `samov` using its SSH key. SSH listens on
   port `17431`; password and keyboard-interactive authentication are disabled.
   `samov` has declarative passwordless sudo to support remote deployments.
5. The initial NixOS closure contains no Git or Home Manager command. Bootstrap
   the standalone Home Manager profile from the VPS with:

   ```bash
   nix-shell -p git --run 'git clone <url> ~/nix-config'
   cd ~/nix-config
   nix run github:nix-community/home-manager/release-26.05 -- \
     switch --flake .#samov-server
   ```

   Do not add OpenCode or Aider to the server profile just to bootstrap it.

6. Access initial AdGuard setup only through:

   ```bash
   ssh -N -L 8008:127.0.0.1:8008 samov@vps-new
   ```

   Keep this terminal open, then open `http://127.0.0.1:8008` on the
   workstation. The AdGuard UI is bound only to VPS localhost and has no public
   firewall rule; `-L` forwards the workstation port securely over SSH. Stop
   the tunnel with `Ctrl+C` after setup.

7. Create and retrieve AWG profiles only after `wg-quick-awg0` is active:

   ```bash
   ssh samov@vps-new 'sudo awg-add-client <name>'
   sftp vpn-download@vps-new
   ```

   `awg-add-client` prints an ANSI/UTF-8 QR in the SSH terminal and writes
   `/srv/vpn-download/files/<name>.conf` plus `<name>.txt`. The restricted SFTP
   account starts in `/files`, so retrieve either with `get <name>.conf` or
   `get <name>.txt`, not with a `files/` prefix. Import the `.conf` into
   AmneziaVPN or scan the terminal QR. The profile contains a client private
   key: do not commit, share in chat, or retain an unnecessary downloaded copy.

   `naive-add-client <name>` is available only after `domain` and `acmeEmail`
   enable Caddy/NaiveProxy. It creates `<name>-naive.json` in the same SFTP
   directory for Karing/sing-box import.

8. Revoke a lost or retired AWG profile by name:

   ```bash
   ssh samov@vps-new 'sudo awg-remove-client <name>'
   ```

   This removes the peer from the live AWG interface and persistent config,
   then deletes its `.conf` and QR from SFTP. The name is the exact argument
   previously passed to `awg-add-client`; the operation is serialized with
   profile creation to prevent address-allocation races.

9. List active client records and their aggregate traffic without revealing
   public keys, endpoints, or destinations:

   ```bash
   ssh samov@vps-new 'sudo awg-list-clients'
   ```

   `DOWNLOAD_GIB` is bytes sent from the VPS to the client; `UPLOAD_GIB` is
   bytes received by the VPS. These are AWG interface counters, not billing
   data: they reset whenever `awg0` restarts and do not identify visited sites.

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
