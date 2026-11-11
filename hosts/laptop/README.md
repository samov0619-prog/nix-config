# Lenovo installation target: laptop

Outputs: `nixosConfigurations.laptop` and `homeConfigurations.samov-laptop`.
Acer now uses `laptop-old`/`samov-laptop-old`; the user successfully applied both
outputs on Acer and confirmed operation after correcting its transient hostname.
Lenovo-specific settings stay isolated; explicitly shared changes such as the
nomacs viewer below also apply to existing Linux GUI profiles.

[Installed boot errors](boot-errors.md) records the mDNS/environment corrections,
the Lenovo-only pinned unstable BlueZ/core portal selections, checks and remaining
firmware/kernel issues. The BlueZ/portal fixes are upstream, without local backports.
The separate [audio module](audio.nix) carries an upstream PipeWire X11
shutdown-cleanup backport absent from both pinned channels. The user applied it;
one subsequent shutdown exercised repeated X11 callbacks without the old SIGSEGV.
The shared [Amnezia package](../../pkgs/amnezia-vpn/README.md) now gates connection
intent/recovery on NetworkManager readiness. The user accepted Lenovo autoconnect
after reboot and quick recovery after Hibernate; matching new GUI/helper paths
are checked. Split routing, kill-switch/leaks and other hosts remain separate.
The boot audit also records user-confirmed installer cleanup and the deliberately
deferred rare Waybar/Pulse reconnect crash. Documentation needs no activation;
the applied runtime changes are NixOS except the earlier HM environment fix.
See the boot audit for evidence, remaining errors and future apply/check steps.

## Already represented in configuration

- NixOS/HM stateVersion 26.05; standalone HM stays separate from NixOS activation.
- [Live hardware scan](hardware-configuration.nix) from ThinkBook 16 G8+ IPD
  (`21VJ`): initrd storage/USB/Thunderbolt modules, `kvm-intel`, Intel NPU and
  microcode defaults. Storage declarations remain exclusively in Disko; no live
  USB mounts are copied. Declaration fixtures cover this import and its contents,
  not installed boot, NPU functionality or complete configuration evaluation.
- Hyprland/UWSM, familiar Dwindle controls, Russian/English layouts, three-finger
  workspace gesture, audio/Bluetooth/UDisks2 and the existing VPN clients.
- Shared workstation [Avahi/mDNS](../../docs/laptop-audit/mdns.md) resolves LAN
  devices such as the Zynthian Raspberry Pi via `*.local`, without publishing the
  workstation's own services. Acer/desktop and both workstation drafts opt in;
  VPS/installer do not. Actual Pi connectivity remains a live check.
- PPD and a native Waybar profile icon: left click selects the next available
  profile, right click the previous. A
  [Lenovo-only Waybar extension](../../home/linux/laptop/waybar/README.md)
  names both destinations in the tooltip using the actual available profile list.
  Its algorithm/patch checks passed; the full binary/UI remain unbuilt and untested.
- [Lenovo-only graphics module](graphics.nix): unstable `linuxPackages_latest`,
  NVIDIA `latest` from that kernel's package set with open modules and linux-firmware.
  Stable Mesa 64/32-bit follows the stable userspace libc: mixing unstable Mesa
  with stable Hyprland caused an installed `GLIBC_2.43` loader failure.
  No testing kernel, NVIDIA beta/bleeding_edge or manually
  pinned version. An isolated unfree-enabled package import is passed only to
  Lenovo; only its NixOS firmware input is overlaid, leaving other firmware and
  existing hosts intact. The rest of NixOS/HM remains on its existing sources.
  The updated lock selects kernel **7.3.1**, NVIDIA **615.78.08**, Mesa
  **26.1.8** and firmware **20261019**, not today's upstream head. Input updates plus later
   NixOS activation advance the stack; there is no background updater. Live PCI
   inventory confirms Intel `00:02.0` and NVIDIA `02:00.0`, with the built-in panel
   active on Intel. The user selected PRIME render offload with `nvidia-offload`,
   not a global GPU selection or an NVIDIA-wrapped Steam client. Select individual
   games explicitly, e.g. `nvidia-offload %command%` in Steam Launch Options;
    those per-game settings are mutable Steam state, not managed here. The agreed
    power baseline keeps NVIDIA 615/open's native VRAM/suspend handling and default
    RTD3 on supported notebooks, without forced RTD3/S0ix/deep, legacy suspend units
    or Dynamic Boost. Actual idle, resume and installed-driver compatibility still
    need installed-system validation; configuration alone does not establish them.
   See the
  [graphics audit](../../docs/laptop-audit/graphics.md) for evidence and limits.
- Existing workstation CLI/devtools (including shared Python/Node prerequisites
  for Mason), OpenCode, browsers, Blender and Minecraft applications. Global Go
  is omitted across all HM profiles; projects supply it through devenv/direnv.
  The unimported `home/core-set/go.nix` module remains available for future opt-in.
- The shared Linux GUI set replaces Swayimg with stable nomacs on Acer, desktop
  and Lenovo, for Yazi and the image MIME types advertised by nomacs. The Swappy
  screenshot workflow stays unchanged. Unstable nomacs is not selected because it
  is an upstream Beta. No custom UI is imposed; Paint loading, native Wayland/HiDPI
  and editing saved copies still need live validation.
- [Shared Qt appearance](../../home/linux/modules/qt-theme/README.md) installs
  native qt5ct/qt6ct proxies and Adwaita styles on those same GUI profiles. F11
  updates only managed appearance keys; native directory watchers update open
  applications without a daemon or fixed style environment override. Activation
  also sets nomacs to System CSS plus the Qt6 proxy, preserving other preferences
  with a one-time backup. Close Qt apps before HM activation and start a new session
  afterward. Isolated real nomacs startup/live light-dark-light/dark reopening passed;
  Qt5, other applications and actual Wayland/F11 remain unverified.
- The shared Node module selects `pkgs.nodejs_latest` unconditionally for every
  profile that imports it: Acer, desktop, Mac and Lenovo. It provides the global
  Node/npm CLI and Mason's prerequisite, not an LTS-only major; projects pin their
  own version through devShell/direnv when needed. No Lenovo-only selector or
  second Node package is introduced; the lean server still does not import Node.
  `latest` follows the locked stable input: the updated lock selects **26.13.0**, not today's
  upstream release. Updating the input and applying HM advances it; no background
  updater, input update or project/Mason configuration change is introduced here.
- Minecraft generic server module is imported, but instance is **unset**: no world,
  update service or backup watcher is activated. Heap/data/remote preflight remain
  unresolved; do not import the current app module merely to get the launcher.
  User prefers Freesm's own client memory calculation, with manual adjustment if
  needed. Keep the previously working server `20G` heap as the starting point for
  later Lenovo tests, not an automatic reduction to 8G or a new process limit.
- Voice dictation remains available with no Acer Vulkan device override. CPU is
  the provisional fallback, not a final Lenovo backend decision.
- No xremap/uinput/input group, fixed battery name, Acer display coordinates,
  resume offset, TPM workaround, performance governor or inherited thermald.
  Periodic `nvidia-smi` polling is omitted pending dGPU idle validation.
- No zram initially. The host keeps a commented 50%/zstd starting point for later,
  not an enabled service. Revisit after sustained memory pressure in normal use:
  low `MemAvailable` together with memory PSI, disruptive swap I/O or OOMs, after
  checking application/Java heap sizes. Used swap or low free RAM alone is not
  sufficient evidence. If enabled, check swap priorities and repeat hibernation
  tests; the 48 GiB disk swap remains the resume target. No sysctl tuning is added.
- Weekly GC through the existing shared service, retaining **10 NixOS and 10
  standalone Home Manager generations**. No extra timer or cleanup service is
  introduced. This is a generation count, not a guaranteed time window or disk
  quota; review actual space after updates. Modern `nix profile` still retains
  only its current generation, independently of HM rollback history.
- Initial login deliberately matches Acer: `samov` autologin on tty1 **once per
  boot**, followed by the existing UWSM startup. Logging out does not repeatedly
  autologin. `sudo` still requires authentication with the user's password.
  The initial password is the same deliberately public bootstrap value as Acer,
  declared in the host module, not a secret. `users.mutableUsers = true` allows
  a later manual `passwd` change without activation resetting it. No Hyprlock,
  idle locking or fingerprint authentication is configured. Login/biometric
  improvements are deferred until live Lenovo testing; no extra Acer groups or
  `nix.settings.trusted-users` privileges are copied.

## Review status and remaining installation gates

The user chose **ext4 with no disk encryption** for Lenovo, with a separate
**48 GiB swap partition**, also unencrypted.
This matches the existing scaffold; no partition operation has been performed.
Later encryption remains possible, with backup/reinstallation as the predictable
route, not a promised one-click conversion. Fingerprint login/`sudo` is a separate
requested investigation: sensor support, PAM integration and password fallback
remain unreviewed. No fingerprint authentication, passwordless `sudo`, TPM unlock
or Secure Boot configuration is enabled. Autologin is a separate explicit choice
described above, not an implication of using unencrypted storage.

The deliberate failing assertion was removed after updated-input compatibility
and final configuration review on **11.11.2026**, with the user's approval.
NixOS `system.build.toplevel.drvPath` evaluation then passed offline with IFD
disabled; all merged NixOS assertions pass. Full standalone HM activation
derivation evaluation also passed before this host-only change. Neither output
has been built or installed. The GPU power baseline is agreed;
live idle/suspend/hibernate acceptance remains required after installation.
The live hardware scan and
PRIME IDs are configured; Disko points to the observed UMIS NVMe at
`/dev/disk/by-path/pci-0000:01:00.0-nvme-1`. Recheck disk identity before wiping:
this is a topology path, not a serial-number identity. Storage, initial memory/GC and bootstrap login choices
are settled, not permission to install or proof of hardware/boot compatibility.

Do not apply this HM profile on Acer: it manages the same user paths with Lenovo's
configuration. No switch is needed for the current machine. Before any destructive
step, finish the live-store capacity plan, deliver the reviewed commit, recheck
the SSD and obtain explicit permission to erase it. Guard removal is not that permission.

Source-only checks (do not build NixOS or Home Manager):

```fish
nix eval --impure --json --offline --option allow-import-from-derivation false --file hosts/laptop/test-draft.nix
nix eval --impure --json --offline --option allow-import-from-derivation false --file hosts/laptop/test-disko.nix
nix eval --impure --json --offline --option allow-import-from-derivation false --file hosts/laptop/test-graphics.nix
```

The first check exercises real module declarations with fixture packages. The
second exercises the locked Disko config generator with small option fixtures:
ext4, EFI vfat and the same unencrypted swap partition for swap/resume. It neither
realizes a Disko script nor inspects or changes a disk. The third evaluates
selected merged NixOS graphics attributes and open-module
derivations, including one updated linux-firmware input, preserved other firmware
and unchanged Acer/desktop firmware selection. Neither builds a driver, checks
all configuration attributes/assertions or validates hardware/UI. Real checks remain
in the [single Lenovo checklist](../../docs/laptop-audit/lenovo-checklist.md).
Builds and activation are left to the user on Lenovo, not on space-constrained Acer.
The live writable store was RAM-backed with roughly 14 GiB free: do not download
the main closures there without an explicit storage-aware plan. In particular,
do not assume both outputs must be built in RAM before partitioning; settle where
the installer stores/downloads/builds them before proceeding.

The user completed the full input update before the first Lenovo installation,
not an installation frozen to Acer's old lock. Deliver the updated lock and review
changes together from the reviewed local commit; the user performs Git network
operations and verifies the checkout on Lenovo before installation.
Disko is selected for this local installation too: use that same updated locked
revision for review and partitioning, not an unrelated
upstream/latest invocation. Install the complete prepared NixOS/HM configurations,
not a temporary minimal system; standalone HM still has its own activation step.
The user has booted the official stable 26.05 Minimal x86_64 ISO, written directly
to the small USB drive without Ventoy. Windows Home need not be preserved; the
internal SSD has not been repartitioned. User-supplied output confirms live kernel
7.3.3, UEFI, CPU/RAM, PCI drivers and connector status; the hardware scan is now
imported. A completed Memtest pass has not been reported.
Follow the official manual installation sequence, adapting its examples to the
reviewed flake, ext4, 48 GiB swap and GRUB EFI rather than replacing those choices.
Hardware inventory, the coordinated source rename and final configuration review
are complete. The native
power baseline is agreed; its hardware acceptance comes after installation.
Review local integration/patch compatibility and build the final
Lenovo outputs, not every upstream commit or every host. The ordered preparation
and live acceptance stay in the [single checklist](../../docs/laptop-audit/lenovo-checklist.md).
No further USB write, firmware change, lock update, build or installation is
authorized merely by guard removal or successful evaluation.

For this target, declaration fixtures, Nix syntax, formatter checks and source
composition comparisons passed. Existing outputs' module lists were preserved;
Lenovo has its own HM output, NixOS overlay and isolated graphics package argument.
NixOS toplevel and full standalone HM activation derivation evaluations passed;
no full build, activation or installed live UI validation was run. The viewer
checks confirm stable nomacs/Yazi/MIME and preserved Swappy on Acer, desktop and
Lenovo; server and Mac do not gain an image viewer.

The first boot is not a finished HM desktop: NixOS and standalone HM are separate.
Until HM is applied, the user's managed Hyprland/UWSM configuration is absent.
Use a local console (for example Ctrl+Alt+F2) and log in as `samov` with the agreed
bootstrap password if tty1 cannot start the graphical session. Connect networking
and apply HM from that installed-user session. The installed host does not enable
an SSH server; the live installer SSH access does not survive reboot. Set a personal
password with `passwd`; do not put it in Git/store. Follow the single checklist
for the exact installation and acceptance sequence, not this overview alone.
