# Server Configuration Instructions

## Goals

- Run AmneziaWG 2.0, AdGuard Home, and NaiveProxy without Docker.
- Use AmneziaVPN 4.8.21+ for AmneziaWG and Karing for NaiveProxy.
- Keep VPN credentials and generated profiles outside Git and the Nix store.
- Publish client profiles through a single-key, SFTP-only account.
- Select every host feature exclusively through module imports in `flake.nix`.

## Service Layout

- `hosts/server/default.nix` imports the hardware, VPN, AdGuard, Caddy, and
  SFTP modules and owns the host-wide firewall, SSH, Nix, and boot settings.
- `hosts/server/vpn.nix` owns forwarding, NAT, and the AmneziaWG interface.
- `hosts/server/adguard.nix` declares AdGuard filters based on
  `adguardhome-backup-2026-07-20-231323.tar.gz`. Do not import its old Docker
  upstream, administrator hash, statistics, or query log.
- `hosts/server/proxy.nix` runs Caddy with the NaiveProxy `forwardproxy`
  plugin and ACME TLS.
- `hosts/server/sftp.nix` exposes `/srv/vpn-download/files` through a
  chrooted, SFTP-only account with exactly one configured SSH key.
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

1. Boot a NixOS installer and mount the target system at `/mnt`.
2. Run `nixos-generate-config --root /mnt` and commit the generated
   `hosts/server/hardware.nix`; never copy hardware configuration from another
   host.
3. Set the domain, ACME email, AWG port, WAN interface, and SFTP public key in
   `hosts/server/default.nix` before building.
4. Install with `nixos-install --flake .#server`.
5. Apply Home Manager using `home-manager switch --flake .#samov-server`.
6. Access initial AdGuard setup only through
   `ssh -L 8008:127.0.0.1:8008 samov@<server>`.
7. Generate profiles with the installed AWG and Naive client helper commands,
   then download them through SFTP.

## Validation

- Run `nix flake check` and evaluate both server configurations before deploy.
- Confirm `wg-quick-awg0`, `adguardhome`, `caddy`, and `sshd` are healthy.
- Confirm public DNS and the AdGuard UI are unreachable.
- Confirm AmneziaVPN imports and handshakes the AWG profile.
- Confirm Karing imports and uses the Naive profile.
- Confirm the SFTP account cannot obtain a shell or access paths outside its
  profile directory.
