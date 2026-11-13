# Installer VPN: AWG 3.1 for NixOS bootstrap

`nix run .#installer-vpn` provides a temporary full tunnel on an **x86_64 Linux
NixOS live installer**, or temporarily after installed boot before standalone HM.
It does not install the graphical Amnezia client, activate
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
  [installation guide](../../hosts/laptop/README.md) for delivery.
- The helper's files must be tracked/committed before using a Git flake reference
  or cloning it elsewhere. Do not work around this by putting a secret profile
  inside a `path:` flake source.
- Use a **separate client** issued by our AWG 3.1 server. Download its native
  **`.conf`**, not `.vpn`. Never run the same peer on Acer and Lenovo concurrently.
- Keep the profile outside the checkout, for example `/home/nixos/lenovo.conf`,
  with `chmod 600 "$HOME/lenovo.conf"`. Never put it in Git, a Nix expression,
  `environment.etc`, a derivation or the store; never paste its contents into chat.
- Use a short filename beginning with a Latin letter, such as `lenovo.conf`:
  it selects interface `lenovo`. The helper rejects a numeric-only name such as `55.conf`.
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
Then continue the Lenovo installation guide and its specifically reviewed
target-store installation order. VPN setup is not authorization to erase the SSD.

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

## Native DNS adapter

`resolvconf.bash` selects the running NixOS DNS adapter, not one from the caller's
PATH. It first executes `/run/current-system/sw/bin/resolvconf` when available.
Otherwise, with native `resolvectl` and active `systemd-resolved.service`, it uses
Bash `exec -a resolvconf` to select resolvectl's compatibility CLI. Plain
`resolvectl` does not accept quick's `-a`/`-d` CLI. This reuses the running systemd
without adding another systemd version to the bootstrap closure.

With no alias and inactive/unknown resolved (or unavailable native tools), bundled
openresolv remains the fallback for live installers. Unexpected service-probe
errors fail closed; a selected adapter's failure is returned directly, never
retried through a competing DNS manager. Keep the DNS manager/system unchanged
between `up` and `down`. The helper does not stop resolved, overwrite
`/etc/resolv.conf` itself or edit NetworkManager connections.

Systemd's compatibility mode accepts `-a INTERFACE -m 0 -x` and
`-d INTERFACE -f`; the metric is ignored and `-x` selects `~.` DNS routing.
Resolved settings are link-scoped, including a partially applied update; quick's
link deletion releases them. This is not a guarantee of complete firewall/DNS
rollback or compatibility with other concurrent VPN policies.

The recovered old-laptop record reports that the `d9edc3f` helper failed on
installed Lenovo with active resolved, no `resolvconf` alias and disabled
openresolv. Its suppressed output does not establish the first failed subprocess.
The separately delivered dispatcher version was user-built and accepted there:
fresh handshake, resolved DNS `10.66.0.1`/`~.`, cache HTTPS and IPv4 route through
`lenovo`; after `down`, no interface and ordinary Wi-Fi routing/DNS/HTTPS.
This is historical user-reported acceptance, not a new build/integration test,
external-IP/IPv6-leak/firewall audit or reason to replace working graphical Amnezia.

## Optional: retain bootstrap across installed boot

Only needed if ordinary installed networking cannot download the first HM closure.
Before reboot, after successful NixOS installation, use the **same reviewed
checkout/lock** on the live machine. The following gets only the helper, not HM.
Stop on any error; do not overwrite existing roots/profile files without inspecting
them. The example assumes the private live profile is `$HOME/lenovo.conf` and the
target root is mounted at `/mnt`:

```fish
nix --extra-experimental-features 'nix-command flakes' build --no-update-lock-file --out-link "$HOME/installer-vpn-bootstrap" .#installer-vpn
set helper (readlink -f "$HOME/installer-vpn-bootstrap")
sudo nix --extra-experimental-features 'nix-command flakes' copy --no-check-sigs --to /mnt "$helper"
sudo nix --extra-experimental-features 'nix-command flakes' path-info --store /mnt --recursive "$helper"
sudo test -x "/mnt$helper/bin/installer-vpn"
sudo mkdir -p /mnt/nix/var/nix/gcroots
sudo ln -s "$helper" /mnt/nix/var/nix/gcroots/installer-vpn-bootstrap
sudo install -m 600 "$HOME/lenovo.conf" /mnt/root/lenovo.conf
```

Here `--no-check-sigs` is scoped to copying this reviewed, locally built helper
closure between local stores: local outputs may be unsigned. Do not disable
signature checking globally or use this for arbitrary downloaded store paths.
The target `path-info --store /mnt` check matters: an absolute GC-root symlink in
the live environment can resolve through the live store, not the target store.
The profile stays outside Git/store. This copy does not replace the live profile;
finish downloads and `down` the live tunnel before reboot.

After installed boot, connect ordinary Wi-Fi first and, if needed, run:

```fish
sudo /nix/var/nix/gcroots/installer-vpn-bootstrap/bin/installer-vpn up /root/lenovo.conf
sudo /nix/var/nix/gcroots/installer-vpn-bootstrap/bin/installer-vpn status /root/lenovo.conf
resolvectl status lenovo
ip -4 route get 1.1.1.1
curl --fail --head --max-time 20 https://cache.nixos.org
```

After HM downloads, disconnect with the **same helper/profile**, then verify
ordinary route/DNS/HTTPS before starting graphical Amnezia:

```fish
sudo /nix/var/nix/gcroots/installer-vpn-bootstrap/bin/installer-vpn down /root/lenovo.conf
```

Import a private user-readable copy of the profile into graphical Amnezia manually,
not via Git/store. Remove temporary roots/helper copies and duplicate profiles
only after successful teardown and acceptance of the graphical client; never
delete the only working profile first. Existing installed Lenovo needs none of
these bootstrap steps. Old store outputs do not update when sources change.

## Implementation and SSH boundary

- `../amneziawg-3.1/go.nix` is the same pinned **3.1.20260814** backend as the
  existing graphical client; `../amneziawg-3.1/tools.nix` supplies the pinned
  **3.1.20260812** CLI. Stock stable's older Go backend is not silently substituted.
- A separate copy of the pinned upstream `awg-quick` uses its documented override
  insertion point to select the userspace backend directly. Server tools and
  kernel modules are unchanged. No live kernel-module build or reboot is needed;
  the live kernel must provide ordinary `/dev/net/tun`.
- Native quick handles addresses, policy routes, firewall rules and DNS
  setup/teardown through the adapter above. It suppresses only the main default route, preserving more
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
    work and follow the installation guide before rebooting.

## Checks and current limitations

No full build, installed layout, real sudo/TUN/UDP, live DNS/firewall/SSH or actual
VPN connection is implied by the local tests. They never access a real profile.
Those fixtures are separate from the user-reported live acceptance below.

On 10 November 2026, the user built the helper on Lenovo's live installer from
checkout `b5ccba9`, using its committed pre-update lock. The user reported a
successful connection and LAN SSH access; supplied output showed a recent
handshake (14 seconds), DNS `10.66.0.1` for the VPS AdGuard, and routes to that DNS
and a public IPv4 through `lenovo`. Cache HTTPS returned HTTP/2 200, and an external
IPv4 check matched the VPS. After `down`, supplied output showed ordinary Wi-Fi
routing, the router's DNS and working HTTPS; the external IPv4 returned to the
home address. This is user acceptance of that live setup, not independent agent
network verification, an IPv6 leak/firewall audit or acceptance of the pending
updated lock, full system or graphical client. No private profile was inspected.

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
nix eval --impure --offline --json --option allow-import-from-derivation false --file pkgs/installer-vpn/tests/test-declarations.nix
python3 -B pkgs/installer-vpn/tests/test_installer_vpn.py
```

Wrapper fixtures cover private external profiles, rejection of hooks/routing
overrides, sudo argv, secret-output suppression, temporary snapshots, handshake
reporting and SSH pre/postflight/rollback. Additional actual-script tests take
the source from the exact pinned tools revision, validates its SHA-256, inserts
the production userspace override, and runs native quick with fake ip/awg/backend/
resolvconf/firewall commands. They run the production dispatcher with fake native
openresolv/resolved and bundled openresolv, checking IPv4/IPv6 routes, DNS teardown,
DNS/partial-DNS/later-route failure rollback and link deletion. Resolved's release
of link-scoped state is modelled, not a real daemon test. No real AWG handshake,
systemd D-Bus interaction or native C parser is covered.

Provide an already available pinned source (do not build the project to obtain it):

```fish
python3 -B pkgs/installer-vpn/tests/test_installer_vpn.py --quick-source /path/to/amneziawg-tools/src/wg-quick/linux.bash
```

Without `--quick-source` these extra tests are explicitly skipped. On a tools update,
review the upstream quick changes and override point before updating the test
digest. Never update it just to make an unrelated source pass.

Add `--resolvectl /run/current-system/sw/bin/resolvectl` for a read-only native
compatibility CLI check (`--help` only, no daemon/network changes). Without it
that check is explicitly skipped. Dispatcher fixtures also check argv/stdin/status
forwarding, fallback selection and no fallback after a selected adapter fails.

During recovery of the old-laptop patch on 13 November 2026, all 22 tests passed
with the pinned quick source and installed resolvectl's `--help`. Selected Nix
declarations passed offline without builds/IFD, preserving the original AWG backend
and server tools derivations. Bash syntax, nixfmt 1.5.0 and whitespace checks
passed. No build, activation, live VPN/DNS change or new installed-layout test was
run. Prettier/Ruff/Beautysh were unavailable; their file types retain existing style.

After review, the user can build only this helper on a machine with enough space:

```fish
nix build --no-update-lock-file --no-link .#installer-vpn
```

This is not a request to build on the nearly full Acer, nor a full-system build.
Adding this app/docs requires no NixOS/HM activation. The graphical client's
shared-pin extraction preserves its backend derivation; do not switch Acer just
to use the standalone installer app. All remote Git operations remain manual.
