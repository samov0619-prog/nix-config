# Installer VPN: AWG 3.1 before downloading the system

`nix run .#installer-vpn` provides a temporary full tunnel on an **x86_64 Linux
NixOS live installer**. It does not install the graphical Amnezia client, activate
NixOS/HM, partition disks or depend on a running Acer or administrative SSH access
to the VPN server. Lenovo's installation assertion and external server settings
do not gate this standalone app.

The tool, sources, dependency versions and commands live in this repository.
The private `.conf` is runtime data, not a Nix input. Connecting is necessarily an
imperative action, just like connecting Wi-Fi; its implementation is declarative
and reproducible from the reviewed checkout and lock.

## Before starting

- Boot the official Minimal ISO, connect Wi-Fi and keep the local console usable.
  This does **not** require a custom ISO or the installed system's closure.
- Obtain a reviewed Git checkout on the live machine. Push/clone are user actions;
  do not copy an Acer-only SSH alias or private key into the installer. If Git is
  absent, `nix-shell -p git` can provide it temporarily. See the
  [installation checklist](../../docs/laptop-audit/lenovo-checklist.md) for delivery.
- The helper's files must be tracked/committed before using a Git flake reference
  or cloning it elsewhere. Do not work around this by putting a secret profile
  inside a `path:` flake source.
- Use a **separate client** issued by our AWG 3.1 server. Download its native
  **`.conf`**, not `.vpn`. Never run the same peer on Acer and Lenovo concurrently.
- Keep the profile outside the checkout, for example `/home/nixos/lenovo.conf`,
  with `chmod 600 "$HOME/lenovo.conf"`. Never put it in Git, a Nix expression,
  `environment.etc`, a derivation or the store; never paste its contents into chat.
- Use a short filename such as `lenovo.conf`: it selects interface `lenovo`.
  Choose an unused name and do not edit, rename or remove the profile until `down`.
- Only the native single-peer AWG 3.1 full-tunnel export is supported: numeric
  DNS, `HeaderProtectionKey`, and `AllowedIPs = 0.0.0.0/0, ::/0`. Hooks, custom
  routing tables, SaveConfig and unknown directives are deliberately rejected.
  Do not remove AWG parameters to make an incompatible profile pass.

The first checkout/source/dependency download happens **before VPN exists**.
This may include build dependencies if matching binaries are not cached; a small
helper does not guarantee a tiny initial download. A custom ISO with the helper
prebuilt could remove that bootstrap download, but is not implemented here.
Reusing the same lock does not promise that external sources/caches will remain
available forever. There is no bootstrap promise of an entire install in two commands.

## Connect, verify, disconnect

Run these on **Lenovo live**, not Acer, from the reviewed repository root:

```fish
cd ~/nix-config
nix --extra-experimental-features 'nix-command flakes' run --no-update-lock-file .#installer-vpn -- up "$HOME/lenovo.conf"
```

Run Nix as the normal live user; the app asks for sudo only for runtime network
operations. `--no-update-lock-file` refuses a needed lock update rather than
silently choosing different inputs. `up` configures the interface, **not proof of
a working tunnel**. It does not fetch the full NixOS/HM closure.

Before any large download:

```fish
nix --extra-experimental-features 'nix-command flakes' run --no-update-lock-file .#installer-vpn -- status "$HOME/lenovo.conf"
ip -4 route get 1.1.1.1
curl --fail --head --max-time 20 https://cache.nixos.org
```

Expect a recent handshake, a public IPv4 route through `lenovo`, and successful
DNS/TLS/HTTP access to the cache. `status` reports only handshake age, not keys,
endpoints or profile contents. Exit codes: 0 for an observed handshake, 2 for no
handshake yet, 1 for a missing interface/error. An old handshake is not current
connectivity proof, and HTTP success alone does not prove the route is through VPN.
Our server's `::/0` intentionally blocks IPv6 rather than leaking it if that VPS
does not have working IPv6 egress. This is not a leak-tested kill switch or a
benchmark; a working VPN does not guarantee a higher download rate.

Check that a second SSH connection from Acer to Lenovo's LAN address still works.
Then continue the existing Lenovo checklist and the specifically reviewed builds
or installation. VPN setup is not authorization to remove the install guard or
erase the SSD.

Disconnect with the same unchanged profile and checkout:

```fish
nix --extra-experimental-features 'nix-command flakes' run --no-update-lock-file .#installer-vpn -- down "$HOME/lenovo.conf"
ip -4 route get 1.1.1.1
curl --fail --head --max-time 20 https://cache.nixos.org
```

Expect ordinary Wi-Fi routing/DNS again and no `lenovo` interface. A successful
teardown exit is not proof of DNS/firewall restoration: native quick makes parts
of that cleanup best-effort, so the checks above still matter. The helper does
not create a persistent service or auto-start entry; the live tunnel is lost on
reboot. Once NixOS/HM are installed, use the configured graphical Amnezia client;
do not also leave the installer tunnel running.

## Implementation and SSH boundary

- `../amneziawg-3.1/go.nix` is the same pinned **3.1.20260814** backend as the
  existing graphical client; `../amneziawg-3.1/tools.nix` supplies the pinned
  **3.1.20260812** CLI. Stock stable's older Go backend is not silently substituted.
- A separate copy of the pinned upstream `awg-quick` uses its documented override
  insertion point to select the userspace backend directly. Server tools and
  kernel modules are unchanged. No live kernel-module build or reboot is needed;
  the live kernel must provide ordinary `/dev/net/tun`.
- Native quick handles addresses, policy routes, firewall rules and openresolv
  DNS setup/teardown. It suppresses only the main default route, preserving more
  specific LAN routes. No NetworkManager connection or global hostname is edited.
- When invoked over SSH with `SSH_CONNECTION` present, the helper refuses `up` if
  the peer is reachable only through a default route. It checks the outgoing
  interface again after connecting and attempts `down` on an unexpected change.
  This is a focused LAN safeguard, **not a guarantee against every firewall,
  policy-rule or concurrent network change**. A lost SSH connection requires the
  local console. A shell/tmux with missing SSH metadata cannot be checked this way.
- Profiles are validated, then copied to a private temporary `/run` directory
  (0700, file 0600) for each operation, avoiding a validation/use race on the
  caller's file. The temporary copy is removed on ordinary exit. No long-lived
  profile snapshot, credential log or Nix-store copy is created.
- Unsupported hooks and credential-bearing command output are not displayed.
  Backend debug/foreground/fd overrides and shell startup hooks are not inherited.
  Errors deliberately omit upstream parser output, which can contain private keys.

## If connection fails

1. Do not send the `.conf`, `awg showconf`, `awg-quick strip`, raw verbose/debug
   logs or commands containing key values. Report the app's safe message instead.
2. Check the file is the separate client's `.conf`, outside the checkout/store,
   mode 600, unchanged and compatible with AWG 3.1; confirm `/dev/net/tun` exists.
3. Use `status` above, `ip -brief address show dev lenovo`, route checks and the
   bounded cache request. No handshake suggests endpoint/UDP/profile/server
   trouble; a handshake with failed HTTP still requires DNS/routing investigation.
4. Use `down` before retrying or editing the profile. Upstream quick attempts its
   normal rollback on a failed `up`; interruption or teardown failure can still
   leave partial state. Do not assume a generic failure message proves cleanup.
   On failure, use the local console and inspect the selected interface, rules and
   DNS before reconnecting; do not flush all routes/firewall rules or stop networking.
5. A live reboot is a last-resort reset of transient network state, **not** a fix
   for a bad profile. It also loses the RAM checkout/profile; preserve reviewed
   work and follow the installation checklist before rebooting.

## Checks and current limitations

No full build, installed layout, real sudo/TUN/UDP, live DNS/firewall/SSH or actual
VPN connection is implied by the local tests. They never access a real profile.
User acceptance on Lenovo remains required before relying on the tunnel.

On 10 November 2026, all 15 local tests passed with the pinned quick source,
including IPv4/IPv6 policy-rule removal and private-output failure fixtures.
Without that source, 14 tests passed and the actual-script test was skipped.
The selected Nix app/backend/tools derivations evaluated without builds or IFD;
the extracted backend equals the original inline client derivation, and the
server tools derivation is unchanged. Bash/Python syntax and documentation links
were checked. Changed Nix files use nixfmt 1.3.1; Prettier/Ruff/Beautysh were
unavailable, so Markdown/Python/shell were not reformatted with substitutes.

Pre-commit review also evaluated the helper derivation against the committed
pre-update nixpkgs, as well as the pending full input update. The helper can be
delivered separately from that unreviewed lock change. This is only VPN bootstrap;
the final Lenovo installation still requires review of the updated lock and must
use that same final locked revision for Disko and the installed configuration.

Lightweight declarations, with no builds/IFD:

```fish
nix eval --impure --offline --json --option allow-import-from-derivation false --file pkgs/installer-vpn/test-declarations.nix
python3 -B pkgs/installer-vpn/test_installer_vpn.py
```

Wrapper fixtures cover private external profiles, rejection of hooks/routing
overrides, sudo argv, secret-output suppression, temporary snapshots, handshake
reporting and SSH pre/postflight/rollback. An additional actual-script test takes
the source from the exact pinned tools revision, validates its SHA-256, inserts
the production userspace override, and runs native quick with fake ip/awg/backend/
resolvconf/firewall commands. It checks IPv4/IPv6 address/default-route setup,
DNS teardown and link deletion, not a real AWG handshake or native C parser.

Provide an already available pinned source (do not build the project to obtain it):

```fish
python3 -B pkgs/installer-vpn/test_installer_vpn.py --quick-source /path/to/amneziawg-tools/src/wg-quick/linux.bash
```

Without `--quick-source` this extra test is explicitly skipped. On a tools update,
review the upstream quick changes and override point before updating the test
digest. Never update it just to make an unrelated source pass.

After review, the user can build only this helper on a machine with enough space:

```fish
nix build --no-update-lock-file --no-link .#installer-vpn
```

This is not a request to build on the nearly full Acer, nor a full-system build.
Adding this app/docs requires no NixOS/HM activation. The graphical client's
shared-pin extraction preserves its backend derivation; do not switch Acer just
to use the standalone installer app. All remote Git operations remain manual.
