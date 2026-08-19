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

## Minecraft

- The reusable server module contains the Packwiz, Fabric, and backup-sync
  implementation. It remains inactive while `minecraft.server` is null.
- `home/apps/minecraft` supplies the current paths, memory, Packwiz, JDK, and
  FreesmLauncher.
- To enable Minecraft on the server, add `./home/apps/minecraft` to its module
  list in `flake.nix`; no host flags are used.

## VPS Installation

1. Boot the provider rescue system and confirm the disk, WAN interface, address,
   prefix, gateway, and DNS with `lsblk` and `ip route`.
2. Set all provider-specific values in `hosts/server/settings.nix`. Example for
   the installed VPS: `/dev/vda`, `ens3`, `94.103.3.166/24`, and gateway
   `94.103.3.1`. These values are examples, not defaults for a different VPS.
3. Configure rescue SSH to use the same port and key expected by the target.
   Keep its session open until the target system accepts `samov` login.
4. Build and validate locally before destructive deployment:

   ```bash
   nix build .#nixosConfigurations.server.config.system.build.toplevel --no-link
   nix flake check --no-build 'path:.'
   ```

5. From this repository on another machine, install with:

   ```bash
   nix run github:nix-community/nixos-anywhere -- \
     --flake .#server root@<rescue-host>
   ```

   This erases `settings.nix.diskDevice`. Do not interrupt after Disko begins.

6. After the final reboot, log in as `samov` using its SSH key. SSH listens on
   port `17431`; password and keyboard-interactive authentication are disabled.
   `samov` has declarative passwordless sudo to support remote deployments.
7. Apply the standalone Home Manager profile from an up-to-date checkout:

   ```bash
   home-manager switch --flake .#samov-server
   ```

   The server's initial NixOS closure contains no Git or Home Manager command.
   Bootstrap them with `nix-shell -p git --run 'git clone <url> ~/nix-config'`
   and `nix run github:nix-community/home-manager/release-26.05 -- ...`.
   Do not add OpenCode or Aider to the server profile just to bootstrap it.

8. Access initial AdGuard setup only through:

   ```bash
   ssh -p 17431 -L 8008:127.0.0.1:8008 samov@<server>
   ```

9. Generate profiles with the installed AWG and Naive client helper commands,
   then download them through SFTP.

## Remote Updates And Recovery

- Deploy a server configuration from the workstation with:

  ```bash
  nixos-rebuild switch --flake .#server --target-host samov@<server>:17431 --sudo
  ```

- This remote NixOS deployment builds on the workstation, transfers the
  closure over SSH, and activates it through `samov`'s declarative
  passwordless sudo. It avoids using VPS disk space for a system build.
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
