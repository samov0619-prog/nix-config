# Lenovo draft: laptop-next

Temporary outputs: `nixosConfigurations.laptop-next` and
`homeConfigurations.samov-laptop-next`. Acer still owns `laptop`/`samov-laptop`;
none of its configuration or other existing profiles changes in this step.

## Already represented in configuration

- NixOS/HM stateVersion 26.05; standalone HM stays separate from NixOS activation.
- Hyprland/UWSM, familiar Dwindle controls, Russian/English layouts, three-finger
  workspace gesture, audio/Bluetooth/UDisks2 and the existing VPN clients.
- PPD and a native Waybar profile icon: left click selects the next available
  profile, right click the previous. A
  [Lenovo-only Waybar extension](../../home/linux/laptop-next/waybar/README.md)
  names both destinations in the tooltip using the actual available profile list.
  Its algorithm/patch checks passed; the full binary/UI remain unbuilt and untested.
- Open NVIDIA kernel modules for RTX 5060, not Acer's proprietary/legacy override.
  This does not yet choose a driver branch, PRIME mode or PCI Bus IDs.
  The [graphics source audit](../../docs/laptop-audit/graphics.md) found baseline
  support in the locked kernel/Mesa/NVIDIA stack, not proof of live compatibility.
- Existing workstation CLI/devtools (including shared Python/Node prerequisites
  for Mason), OpenCode, browsers, Blender and Minecraft applications. Global Go
  is preserved as in the current workstation composition; cleanup is separate.
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

Source-only check (does not build NixOS or Home Manager):

```fish
nix eval --impure --json --offline --option allow-import-from-derivation false --file hosts/laptop-next/test-draft.nix
```

The check exercises real module declarations with fixture packages, not merged
NixOS/HM configuration, hardware, graphics or UI integration. Real checks remain
in the [single Lenovo checklist](../../docs/laptop-audit/lenovo-checklist.md).
Builds and activation are left to the user after the draft blockers are resolved;
do not attempt either output as an installation-ready configuration now.

For this draft, declaration fixtures, Nix syntax, formatter checks and source
composition comparisons passed. Existing output module lists were preserved;
only the Lenovo NixOS overlay and the new HM output were added in `flake.nix`.
No full NixOS/HM evaluation, build, activation or live UI validation was run.
