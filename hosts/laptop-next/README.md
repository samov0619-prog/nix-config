# Lenovo draft: laptop-next

Temporary outputs: `nixosConfigurations.laptop-next` and
`homeConfigurations.samov-laptop-next`. Acer still owns `laptop`/`samov-laptop`.
Lenovo-specific settings stay isolated; explicitly shared changes such as the
nomacs viewer below also apply to existing Linux GUI profiles.

## Already represented in configuration

- NixOS/HM stateVersion 26.05; standalone HM stays separate from NixOS activation.
- Hyprland/UWSM, familiar Dwindle controls, Russian/English layouts, three-finger
  workspace gesture, audio/Bluetooth/UDisks2 and the existing VPN clients.
- Shared workstation [Avahi/mDNS](../../docs/laptop-audit/mdns.md) resolves LAN
  devices such as the Zynthian Raspberry Pi via `*.local`, without publishing the
  workstation's own services. Acer/desktop and both workstation drafts opt in;
  VPS/installer do not. Actual Pi connectivity remains a live check.
- PPD and a native Waybar profile icon: left click selects the next available
  profile, right click the previous. A
  [Lenovo-only Waybar extension](../../home/linux/laptop-next/waybar/README.md)
  names both destinations in the tooltip using the actual available profile list.
  Its algorithm/patch checks passed; the full binary/UI remain unbuilt and untested.
- [Lenovo-only graphics module](graphics.nix): unstable `linuxPackages_latest`,
  NVIDIA `latest` from that kernel's package set with open modules, Mesa 64/32-bit
  and linux-firmware. No testing kernel, NVIDIA beta/bleeding_edge or manually
  pinned version. An isolated unfree-enabled package import is passed only to
  Lenovo; only its NixOS firmware input is overlaid, leaving other firmware and
  existing hosts intact. The rest of NixOS/HM remains on its existing sources.
  Current lock selects kernel **7.2.11**, NVIDIA **615.78.08**, Mesa **26.2.5** and
  firmware **20260916**, not today's upstream head. Input updates plus later
  NixOS activation advance the stack; there is no background updater. PRIME mode,
  Bus IDs, GPU power policy and live compatibility remain unverified. See the
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
  `latest` follows the locked stable input: currently **26.4.0**, not today's
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

## Still blocked, not installation instructions

The user chose **ext4 with no disk encryption** for Lenovo, with a separate
**48 GiB swap partition**, also unencrypted.
This matches the existing scaffold; no partition operation has been performed.
Later encryption remains possible, with backup/reinstallation as the predictable
route, not a promised one-click conversion. Fingerprint login/`sudo` is a separate
requested investigation: sensor support, PAM integration and password fallback
remain unreviewed. No fingerprint authentication, passwordless `sudo`, TPM unlock
or Secure Boot configuration is enabled. Autologin is a separate explicit choice
described above, not an implication of using unencrypted storage.

The system has an explicit failing assertion until target hardware/PRIME settings
and target disk are reviewed. Remove it only after resolving those items. The
disk is still `REPLACE_ME`. Storage, initial memory/GC and bootstrap login choices
are settled, not permission to install or proof of hardware/boot compatibility.

Do not apply this HM profile on Acer: it manages the same user paths with Lenovo's
configuration. No switch is needed for the current machine. Do not install or run
Disko from this draft.

Source-only checks (do not build NixOS or Home Manager):

```fish
nix eval --impure --json --offline --option allow-import-from-derivation false --file hosts/laptop-next/test-draft.nix
nix eval --impure --json --offline --option allow-import-from-derivation false --file hosts/laptop-next/test-graphics.nix
```

The first check exercises real module declarations with fixture packages. The
second evaluates selected merged NixOS graphics attributes and open-module
derivations, including one updated linux-firmware input, preserved other firmware
and unchanged Acer/desktop firmware selection. Neither builds a driver, checks
all configuration attributes/assertions or validates hardware/UI. Real checks remain
in the [single Lenovo checklist](../../docs/laptop-audit/lenovo-checklist.md).
Builds and activation are left to the user after the draft blockers are resolved;
do not attempt either output as an installation-ready configuration now.

The user plans a full input update before the first Lenovo installation, not an
installation frozen to Acer's old lock. Keep the tracked lock as the baseline and
use `nix flake update`, not deletion; fixed refs still need separate consideration.
Windows initial setup is not completed. First prepare a NixOS Live USB: the ISO
choice remains open, with the user leaning toward minimal for a lightweight
console-only environment; graphical is optional, not required for manual installation.
The user prefers USB 3.x for speed; Gen 1 is enough, USB 2.0 also works, 8 GB or
larger recommended. Collect read-only hardware
inventory, resolve the host/disk/graphics blockers and coordinated rename, then let
the user update. Review local integration/patch compatibility and build the final
Lenovo outputs, not every upstream commit or every host. The ordered preparation
and live acceptance stay in the [single checklist](../../docs/laptop-audit/lenovo-checklist.md).
No USB write, firmware change, lock update, build or installation is authorized
merely by this plan; keep the guard until the actual blockers are reviewed.

For this draft, declaration fixtures, Nix syntax, formatter checks and source
composition comparisons passed. Existing outputs' module lists were preserved;
Lenovo has its own HM output, NixOS overlay and isolated graphics package argument.
No full configuration evaluation, build, activation or live UI validation was run;
only selected merged graphics and HM viewer attributes were evaluated. The viewer
checks confirm stable nomacs/Yazi/MIME and preserved Swappy on Acer, desktop and
Lenovo; server and Mac do not gain an image viewer.
