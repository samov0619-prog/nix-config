# AGENTS.md — Карта репозитория для AI-сессий

## Архитектура

Flake: NixOS + standalone Home Manager, один пользователь `samov`.
NixOS и HM управляются раздельно: NixOS через `nixosConfigurations`, HM через `homeConfigurations`.
Нет нотации/скриптов применения — используй `sudo nixos-rebuild switch --flake .#<host>` и `home-manager switch --flake .#samov-<host>`.

### Flake

- Каналы: `nixpkgs` + `home-manager` = 26.05; `nixpkgs-unstable` передаётся через `specialArgs`.
- `nixpkgs-kernel` follows Nixpkgs master only for Lenovo's released `linux_latest`,
  never testing/RC. Only Lenovo receives its isolated package import; existing
  unstable module recipes are instantiated for that kernel with `linuxPackagesFor`.
- Системы: `x86_64-linux`, `aarch64-darwin`.
- Хелперы: `pkgsFor`, `pkgsUnstableFor`, `mkHM`, `mkNixos`.
- Overlays: `filemanager1-common` + `freesm` — только для desktop/laptop-old/laptop HM;
  локальный `amnezia-vpn` — только для NixOS desktop/laptop-old/laptop.
- `blueman-polkit` overlay — только NixOS laptop-old/laptop: прежний stable
  Blueman с Polkit build support и неизменёнными upstream actions/wheel rule.
  It also prepares informational native-dialog expiry (default 3s), retaining
  explicit zero timeouts and interactive requests. The user applied/accepted the
  initial 15s behavior, then requested 3s; that revision is contract-tested but
  not yet applied. No agent build/activation or full pairing UI acceptance.
  See `pkgs/blueman-polkit/README.md` and the backport registry/removal contract.
- `xremap-flake` передаётся в `extraSpecialArgs`.

### NixOS-хосты

|              | laptop-old (Acer)                                  | desktop                         | server                                 |
| ------------ | -------------------------------------------------- | ------------------------------- | -------------------------------------- |
| CPU          | Intel                                              | AMD                             | VPS                                    |
| GPU          | Intel iGPU + NVIDIA PRIME                          | NVIDIA only                     | —                                      |
| Ввод         | xremap + uinput                                    | нет                             | —                                      |
| Сеть         | NetworkManager, v2raya, Amnezia                    | NetworkManager, v2raya, Amnezia | SSH, AWG3.1, AdGuard, NaiveProxy, SFTP |
| Boot         | GRUB EFI removable                                 | GRUB nodev                      | GRUB on `settings.nix.diskDevice`      |
| Доп.         | Hibernate/zram, Bluetooth, brightnessctl, thermald | нет                             | NAT, ACME, profile download            |
| stateVersion | 25.11                                              | 25.11                           | 26.05                                  |

### Home Manager-конфигурации

|                  | samov-laptop-old            | samov-desktop               | samov-server     | samov-mac        |
| ---------------- | --------------------------- | --------------------------- | ---------------- | ---------------- |
| База             | users + core-set            | users + core-set            | users + core-set | users + core-set |
| GUI              | gui-set                     | gui-set                     | —                | —                |
| Apps             | minecraft + creative        | minecraft + creative        | —                | —                |
| Minecraft module | server + instance           | server + instance           | server only      | —                |
| Leaf             | linux/laptop-old            | linux/desktop               | linux/server     | —                |
| Overlays         | filemanager1-common, freesm | filemanager1-common, freesm | нет              | нет              |
| Архитектура      | x86_64-linux                | x86_64-linux                | x86_64-linux     | aarch64-darwin   |

Lenovo owns `laptop`/`samov-laptop` with stateVersion 26.05, its separate hardware
scan, PRIME offload, Disko ext4/48 GiB swap and PPD; review/install gates below.
Its HM leaf is `home/linux/laptop`, with the same GUI overlays but no Minecraft
instance activation. Old `*-next` laptop outputs are removed, not compatibility
aliases: never apply Lenovo's `laptop` profile on Acer. Source renaming does not
change the currently running Acer until the user applies `laptop-old`.

### Модульная структура HM

```
home/
├── users/samov/                 # username, homeDirectory, stateVersion = "25.11"
├── core-set/                    # shell, devtools, security, common CLI packages, rclone
├── gui-set/                     # browsers, MPV, Alacritty, Kitty, ueberzugpp
├── apps/
│   ├── creative.nix             # Blender
│   └── minecraft/               # FreesmLauncher, Packwiz, JDK, current instance paths
├── modules/
│   ├── alacritty/               # terminal module + themes
│   ├── kitty/                   # generated langmap-aware kitty.conf
│   └── minecraft/server/        # Packwiz → Fabric → backup-sync implementation
└── linux/
    ├── core-set/                # xray, adb, btop
    ├── gui-set/                 # Hyprland ecosystem, audio, screenshots, file manager
    ├── modules/                 # Hyprland, Waybar, tofi, xremap, FileManager1
    ├── desktop/                 # desktop leaf and raw host overrides
    ├── laptop-old/              # Acer leaf and preserved raw host overrides
    ├── laptop/                  # Lenovo leaf and raw host overrides
    └── server/                  # server CLI, Mason prerequisites, server Neovim config

hosts/server/
├── default.nix                  # system baseline and server module imports
├── settings.nix                 # example only; real settings are an external input
├── settings-template/           # fail-closed default server-settings input
├── installer.nix                # minimal settings-based provider ISO, no Disko/services
├── vpn.nix                      # AWG3.1 bootstrap, NAT, profile generation
├── adguard.nix                  # private DNS and imported filter set
├── proxy.nix                    # Caddy + NaiveProxy plugin + Karing profiles
└── sftp.nix                     # one-key, chrooted profile download account

hosts/
├── disko/                        # reusable GPT/EFI/ext4/(swap) layouts and docs
├── laptop-old/                   # Acer + legacy swapfile/resume config
├── desktop/                      # current desktop + existing storage config
├── laptop/                       # Lenovo 26.05 target with Disko swap partition
├── desktop-next/                 # EFI Disko template; verify hardware before use
└── server/                       # fresh 26.05 VPS target with Disko
```

`flake.nix` is the source of truth for host composition: a feature exists on a
host only when its module is listed in that host's `modules` array.

Workstation mDNS lives in `hosts/profiles/mdns.nix`, explicitly imported by laptop-old,
laptop, desktop and desktop-next, not server/installer. Avahi + IPv4 NSS resolve
LAN devices such as the Zynthian Pi via `*.local`; UDP 5353 is open, own-service
publishing is disabled. Selected merged declarations/composition are checked by
`hosts/profiles/tests/test-mdns.nix`; real Pi connectivity is not yet checked.
Avahi exclusively owns workstation mDNS: resolved's global MulticastDNS is false,
without disabling its ordinary/VPN DNS. Lenovo's first installed boot exposed two
concurrent stacks. Four-host merged checks pass; after user activation/reboot,
Lenovo's global/link mDNS is off in resolved, Avahi is active and the duplicate-stack
warning is absent. Actual corrected LAN discovery and ordinary/VPN DNS remain unverified.
Lenovo's installed-boot findings are in `hosts/laptop/boot-errors.md`. Its local
`bluetooth.nix` now selects pinned unstable BlueZ 5.87: its actual source passes
all seven empty-default/request/cleanup cases without the removed 5.86 backport.
The user also approved pinned unstable core xdg-desktop-portal 1.22.1 for the
confirmed real-pidfd/proc-dirfd bug, not a portal-routing workaround. A Lenovo-only
overlay preserves exact stable GTK/Hyprland backends (including GTK's build-time
core dependency), stable Mesa/GLib, other hosts and lock. Selected declarations
and extracted upstream portal functions with native Linux descriptors/ioctl pass;
the old function reproduces ENOTDIR. Earlier 5.86/mDNS/environment fixes were
user-applied and observed after reboot. The new package selections are now also
user-applied: latest boot confirms BlueZ 5.87/core portal 1.22.1, no pidns error
and priority-20 RT data-loop threads including onionbell. Real Bluetooth/portal UI
acceptance is pending. Exact shutdown/startup exports are private outside Git;
the previous shutdown exposed PipeWire 1.6.6 SIGSEGV after X11 I/O errors, with
coredump delivery failing. No stored core does not prove no crash. See the audit
for exact timestamps and the journal's late-shutdown coverage limit. No speculative
audio workaround or watchdog suppression. `hosts/laptop/audio.nix` now prepares
stable PipeWire with exact upstream c2fec6c037a1 for repeated X11 disconnect
cleanup; neither pinned 1.6.6 nor 1.6.9 has it. Actual-callback contract tests
detect baseline NULL-source destruction and pass four patched cases; selected
declarations preserve clients, WirePlumber, audio features and other hosts.
This is not a native crash/X11/audio integration test. After user application, the
13:55:53 shutdown exercised both X11 callbacks and stopped PipeWire normally,
without SEGV/core-dump in the selected unit journal. This is one observed cycle,
not universal teardown coverage or evidence about unrecorded late shutdown.
Retain source harnesses on updates. WirePlumber's
startup Lua error did not reproduce in the short private dummy-sink policy probe
(pre-existing sink/stream and two resulting native links are now explicitly checked);
no speculative audio fix. UPower is absent, not just late: enabling it also adds
a critical-battery action, so needs a separate policy decision. Do not silence
remaining ACPI/xe/ISH/WMI/audio messages with unverified workarounds. Fn+Space
keyboard backlight works per user; fingerprint remains deferred. The latest
functional priority order below supersedes the earlier error-first plan.
The user subsequently observed a restored session after manual Hibernate; UPower
with Hibernate is preferred but not enabled. The boot audit records private
resume evidence and remaining SPD5118/Bluetooth/panel/ISH errors. Amnezia 5.0.1.5
emits wakeup on NM ASLEEP and starts reconnecting before freezing; after resume,
route lookup fails and the network-ready trigger is ignored while Reconnecting.
The two affected files are identical in 5.0.3.0. Latest saved startup connected,
but further inspection of the previous startup found default-route discovery and
handshake-send failures before NM became ready; its ready trigger was ignored
while Connecting, with successful connection only after a later Disconnected.
The user confirms intermittent trouble after laptop boot, not manual Connect.
This supports a cold-start readiness race too; the cause of later recovery is
unproven. Desktop autostart has no network-readiness ordering; the helper's
network.target does not guarantee routes. Do not substitute a fixed boot delay.
A shared package readiness patch is now prepared with user approval:
NM state/initial query over existing IPC, pending connection intent, no reconnect
on ASLEEP or SITE/GLOBAL-only changes, recovery while Connecting/Reconnecting and
explicit cancellation. Native Qt events/local QtRO tests exercise actual methods
with protocol/DNS/routes mocked; existing routing tests and three-host declarations
pass. After user application the initial mixed old-GUI/new-helper state was
resolved by reboot: the latest boot `bd1645b2...` confirms matching new store paths.
The user accepts immediate boot autoconnect and quick automatic recovery after
Hibernate, without manual Connect. This is scoped Lenovo acceptance, not repeated
cycles, other hosts, DNS/egress/split-routing/cancellation or kill-switch/leak
testing. The latest private selected-journal export is referenced in the boot audit;
WirePlumber's four startup Lua errors and UPower absence still reproduce.
The latest Hibernate kernel window also repeats Bluetooth reprobe/four gp1
mailbox errors (then successful firmware/DDC/MGMT initialization), SPD5118 -6,
panel double-unprepare and three ISH cmd-2 failures. They remain open despite
successful session/VPN restoration; buffered printk receipt times do not prove
entry-versus-exit placement. Bluetooth was the next diagnostic priority at that
checkpoint; the latest functional order below supersedes it.
No delay or restart hook was added; do not disrupt the working tunnel.
Lenovo's `bluetooth.nix` now separately prepares two named kernel PM backports
(`12997a385f71`, `2926eb396711`). After the user stopped the switch plan over the
live-7.3.3/installed-7.3.1 mismatch, a separate approved `nixpkgs-kernel` input
now selects released 7.3.4, preserving every existing lock node and NVIDIA/firmware.
The new input follows master, with revision fixed normally by flake.lock until
update; no unattended updates. Both PM backports still apply unchanged to 7.3.4.
They avoid unnecessary thaw reset and refresh stale D-state fallback;
true restore FLR remains. Twelve actual-function/table contract cases pass with
mock hardware/reset dependencies, not native kernel/device/Hibernate coverage.
The user built NixOS successfully; reviewed result has both current patch bytes
in its kernel derivation and matching 7.3.4 NVIDIA/Bluetooth module vermagic.
No code/lock review fixes; documentation only. The user subsequently applied/rebooted:
boot `3d979c37...` confirms running/current/booted 7.3.4, loaded NVIDIA 615.78.08
and btintel_pcie binding. Startup firmware/DDC/MGMT succeeds with the adapter powered,
but four GP1 messages, three ISH failures and four WirePlumber Lua errors remain.
The successful private journal export is in the boot audit; the preceding failed
hyphenated-boot-ID capture's zero counts are invalid. One subsequent manual Hibernate
at 17:16:57–17:17:53 returns but repeats one reprobe error, four GP1 messages,
SPD5118 -6, panel double-unprepare and three ISH failures. The adapter re-registers
as hci1; never hardcode hci0 in later diagnostics. Initial headphone connection
trouble is user-reported; later private snapshots show connected/resolved and
running A2DP/aptX. The user confirms audible output after manual reconnect/remove/add
attempts, explicitly deferring headphone connection investigation and tuning.
Automatic reconnection remains unaccepted. A2DP Canceled
and Trusted=false do not establish the cause or authorize policy/trust changes.
Real GPU and reliable Bluetooth recovery remain unaccepted; see the boot audit.
Exact 7.3.4 driver-core review supports PM probe deferral followed by retry as a
reprobe-warning hypothesis, not a measured errno; positive attach success is
normalized to zero. No live tracing or broader core-helper backport was enabled.
SPD5118 now has a concrete startup match: i801 reports SPD Write Disable set.
Merged upstream `bf31dd72f0d5` gates SPD instantiation; its exact patch dry-runs
without fuzz/offset on 7.3.4 with existing SMBus helpers. It removes this host's
SPD5118 hwmon interface, so preparation awaits an explicit user decision; nothing
is configured/built/applied. Do not bypass write protection or hide regcache errors:
the maintainer rejects read-only mode because BIOS can change the register page.
BIOS TRCN23WW research is explicitly deferred, not approved for flashing. The
original EXE, extraction, web-source snapshots/checksums and resume plan are saved
outside Git/tmp at `~/.local/state/nix-config/firmware/lenovo-trcn23ww-2026-11-11/`.
See the boot audit; live ESRT matching needs read-only root access, image signatures
and exact-model Windows-free update compatibility remain unverified. No staging,
trust-policy change or firmware/boot write was performed.
GP1 mailbox handling and the exact saved reprobe errno remain
open; stable 7.3.4 still has both old paths. `BTINTEL PM CLEANUP` and
`hosts/laptop/bluetooth-pm.md` require unpatched-source `--check-upstream` tests
before explicitly removing fixes on update; a conflict/version is not proof.
Preserve the harness/scenarios after removal. Only header context differs from
upstream; all added/removed source lines match. No driver disable/log suppression.
The user also reports removing the reviewed installation leftovers; the scoped
cleanup record and deferred rare Waybar reconnect crash are in the boot audit.
The user subsequently paused journal-error chasing without established functional
impact and prioritized screen brightness, display scale, then lid screen-off,
followed by remaining functional acceptance. Preserve applied fixes and their
regression/removal checks; do not claim residual messages are harmless or fixed.
BIOS/headphone investigation and WirePlumber startup tracing remain deferred.
Read-only display inspection found eDP-2 at 3200×2000/60 Hz, scale 1.0, and default
brightnessctl selecting nvidia_0 instead of intel_backlight (496/496).
The user then confirmed visible panel dim/restore
with explicit intel_backlight 70%/100% commands without sudo. Lenovo's HM brightness
bindings now select that device, preserving -e4/-n2/5% steps. The initial failed-key
report still had old live binds; the user subsequently confirms keys work and
read-only inspection finds the new binds without config errors. Minimum usability
and post-resume control remain unverified. The user prefers roughly 150% over
200%, sees no useful difference from 160%, and approves the technically preferable
value. The user confirms the saved 160% scale applied successfully; it gives
exact 2000×1250 logical dimensions. They then reject 60 Hz: the panel advertises
165 Hz, now selected by the Lenovo HM rule, with external-screen fallback unchanged.
This is not integer pixel scaling or a guarantee for every app/XWayland; the new
mode is now user-applied and accepted. Final read-only review confirms eDP-2 at
3200×2000/164.995 Hz, scale 1.6, DPMS on and no config errors. Later-login persistence
and individual app rendering remain separate checks. The user also accepts the
ordinary lid close/reopen behavior without sleep. Lenovo bindl actions use
switch:on/off:Lid Switch and native dpms off/on eDP-2, not monitor disable or sleep.
Both binds are loaded; external displays/lock-screen integration remain unverified.
Existing keyboard
DPMS wake remains enabled: this is edge-triggered behavior, not a closed-lid lock
against keyboard wake or login/reload while already closed. These are HM-only edits;
logind policy, audio/VPN/drivers and sudo remain unchanged.
The user subsequently ran pinned stable mesa-demos glxinfo -B: ordinary GLX uses
Mesa Intel(R) Graphics (PTL)/Mesa 26.1.8, explicit nvidia-offload uses NVIDIA GeForce
RTX 5060 Laptop GPU/615.78.08, both direct rendering and no llvmpipe. This accepts
GL context creation/selection through XWayland only, not Vulkan/native Wayland
presentation, sustained load, RTD3 or post-resume graphics. The user then ran
nvidia-offload vkcube --wsi wayland --c 600 from pinned stable vulkan-tools: output
selects RTX 5060 and returns to shell without supplied errors; visible rendering
and auto-closure still await explicit confirmation. Plain Vulkan apps may choose
dGPU themselves. Passive RTD3 inspection finds GPU power/control=on, active,
suspended time 0 and NVIDIA Runtime D3 status Disabled by default with parameter 3;
the NVIDIA audio function is already auto/suspended. Automatic RTD3 was an
expectation, not observed behavior here. The user approved preparing Lenovo-only
finegrained RTD3, superseding the old native-default RTD3 baseline. graphics.nix
now enables the native option: 0x02 plus GPU auto/on udev rules, without old
audio/USB removal on 7.3.4. test-nvidia-runtime-pm.nix passes selected merged checks
against the same config with finegrained forced false: all other module parameters
and suspend options match, with no legacy units or explicit VRAM/S0ix overrides.
The lightweight declaration fixture also passes; the broader graphics fixture was
updated but not rerun. The user then applied/rebooted: boot 89e38bd1... has matching
current/booted system hxldrcjja..., 7.3.4/615.78.08, parameter 2 and GPU auto, but
active/D0, suspended time 0 and Runtime D3 status Not supported. RTD3 acceptance
failed. Driver source shows Disabled by default at parameter 3 can mask the same
internal NEVER mode; explicit 0x02 alone was not proven sufficient. A strong exact-
version candidate is NVIDIA issue #1507 (acknowledged internal bug 7039712): Linux
7.3 kthread nullfs makes nv-probe's absolute sysfs config open fail, disabling RTD3.
PR #1512 is open/unmerged, inspected head 369378dc1552ae46f7f95a598a085c0025e464b3.
Source/PR snapshot and hashes are in /tmp/opencode/nvidia-rtd3-615.78.08/. No measured
local open errno/live trace or native patch test exists; do not claim the cause
proven on Lenovo. Explicit finegrained remains applied, not accepted as
effective; no rebind hook, driver reload, firmware change or extra knob was added.
The user then approved preparation without builds/application. The exact saved
PR #1512 diff is now appended only to Lenovo's NVIDIA package.open; actual-function
config-open/probe contracts reproduce baseline defects and pass eight patched
compile variants with mock filesystem/workers. Selected merged tests confirm
module delivery and unchanged kernel/userspace derivations and sleep policy.
This is not native module compilation or hardware RTD3/resume acceptance. No build,
dry-run, activation, reload/rebind or new knob was run. Existing missing build
outputs may still require realization: user should inspect the module dry-run.
The full active-fix inventory is docs/backports/registry.json and README.md:
18 patch files plus inline companions/package selections, classified separately
from customizations/test-only changes. scripts/backport-review.py validates
coverage and compares initial inventory fingerprints (not new acceptance).
The updated HM nix-flake-update-verify checks before builds, then performs bounded
offline cached-source probes and available small unpatched contracts after builds.
No automatic removal/review acceptance, timer or GitHub polling. Plain direct
flake updates bypass the hook; use the script or helper --no-update afterwards.
Conflicts/test failures are review-required, never proof of upstream inclusion;
forward application is not proof the bug persists. Exact evidence, rollback and
acceptance commands are in the graphics audit; apply NixOS for NVIDIA and HM only
for the updated helper. Preserve regression/removal scenarios after fix removal.
The user subsequently staged the patch, saw a module-only dry-run and successfully
built result 73nyv4l2... . Read-only review confirms the unchanged gf6c6ilz... kernel,
all four NVIDIA modules in new 7ib7jzzk... output with version 615.78.08/vermagic
7.3.4, and unchanged NVIDIA userspace/lib32/bin/firmware and modprobe config.
The module derivation differs only in out/patches; patch bytes match the recorded
SHA256. The actual nvidia.ko imports userspace_init_fs, confirming the guarded
branch compiled. Current/booted system remains hxldrcjja..., so application,
module loading and RTD3/offload/Hibernate acceptance are still pending. The agent
did not build, activate or touch the running driver. See the graphics audit.
The user then applied/rebooted: boot 57375bf8... has matching current/booted
73nyv4l2..., kernel 7.3.4 and NVIDIA 615.78.08 with srcversion matching the new
module. User proc output confirms Enabled (fine-grained), Video Memory Off and
suspended; independent read-only inspection confirms D3cold and suspended-time
growth (78875 → 99805 ms), unchanged RTD3/VRAM/S0ix parameters and GPU auto.
Idle RTD3 is now observed working on this boot. The user then repeated pinned
stable native Wayland vkcube: RTX 5060 selected and shell returned without supplied
errors; user reads showed active then suspending. A subsequent independent single
snapshot confirms suspended/D3cold, runtime usage 0 and GPU auto: return to idle
after this invocation is observed, not stuck suspending. Exact latency is not
measured. The user explicitly confirmed visible cube and automatic closure:
one native Wayland NVIDIA offload wake/render/exit/return-to-idle cycle is accepted,
not independent agent UI observation. The user then confirmed the complete manual
Hibernate/session-VPN recovery/cube/return-to-idle procedure: one patched-module
Hibernate/offload/idle cycle is accepted by user report. A later read-only snapshot
on the same boot/system/module confirms suspended/D3cold, usage 0 and suspended
time 505617 ms; it is not independent observation of the entire PM/UI/VPN sequence.
Repeated cycles, sustained load and battery-life measurement remain unverified.
The user subsequently applied standalone HM: installed update-helper now resolves
to qbm2l45z... and contains backport-review.py plus the post-build cached/contracts
hook; installed Bash syntax passes. The user's direct checker reports unchanged=26,
meaning matching inventory fingerprints, not fresh upstream/functional verification.
No real updater/input-update/build cycle was run by the agent to test the hook.
No extra knobs, nvidia-smi polling,
rebind/reload or changes to working audio/VPN/power policy.
At final review the user authorized a local commit and reported the missing Waybar
GPU section. Installed/repository Lenovo config deliberately omits custom/gpu;
the shared Acer/desktop gp.sh polls nvidia-smi every 10 seconds. No panel change
is included in this batch. Treat a runtime-PM-safe GPU indicator as a separate
follow-up; do not undo accepted D3cold by blindly restoring that polling path.
Final lightweight reruns pass: 22 checker tests, four generated-updater mocks,
eight baseline/eight patched NVIDIA compile variants, three selected Nix checks
and pinned nixfmt. No new builds. Preserve exact upstream patch bytes: Git flags
its two single-space blank context lines, which are valid unified-diff syntax;
non-patch source whitespace checks pass. Prettier/Ruff are still unavailable.
The user subsequently rejected always-passive GPU metrics without a confirmed
non-waking API, then approved a manual 60-second Waybar sampling window. Lenovo's
new `custom/gpu-manual` follows disk, starts as GPU, samples utilization/VRAM only
after LMB and renews on another click. At the user's subsequent request, expiry
now hides figures from the bar/tooltip and restores the plain GPU button.
The Waybar-owned helper blocks on private session IPC while idle; no idle NVIDIA
query/cache polling or service. Shared lock/cache deduplicates multi-output
queries; each command has a bounded timeout, BOOTTIME counts suspend, restart is
idle. Explicit sampling can wake/postpone sleep; userspace cannot bound an
uninterruptible kernel ioctl or promise exact D3cold timing. The user applied the
initial reader and confirms correct GPU return to sleep, not independently
measured or repeated-cycle acceptance. The user subsequently applied and accepted
the hide-on-expiry adjustment: only the GPU button remains after the minute.
This is user UI acceptance, not independent agent observation.
Shared CSS removes PPD's bright fills and
adds grey hover without changing profile cycling; only Lenovo uses PPD. Acer/
desktop retain gp.sh. See `home/linux/laptop/waybar/README.md`; no NixOS/power/
driver/audio/VPN policy change, build or activation by the agent.

Lenovo hotkeys are now prepared in its HM leaf: F8 toggles only the named
GXTP5100 touchpad, F9/star opens todo, ordinary F11 (Fn+F11) switches theme without
Super, and ordinary F1 (Fn+F1) retains help. Lenovo's old F3 todo binding is removed;
F1–F6 hardware actions, working F10 screenshot and F7/Super+P stay unchanged.
The Smart Connect F11 side was measured as scancode 0x148/KEY_UNKNOWN, but the user
chose Fn+F11 instead: no kernel backport or code:248 binding. The session-local
touchpad helper serializes presses, records successful hyprctl setters and resets
to enabled on config reload/login; no daemon or sudo. Host-specific Tofi help
preserves Acer/desktop labels. Mocked actual-helper and selected merged checks do
not establish live input/UI behavior. The user subsequently applied and accepted
the hotkeys; this is not independent agent UI or every reload/login scenario
coverage. No further build/activation was run by the agent.
The user confirms camera, screen sharing and video calls work. See
`home/linux/laptop/README.md` for checks, recovery and the HM-only apply procedure.

Lenovo's native UPower battery protection and udiskie mount-point Browse fix are
now user-applied and accepted as configuration/UI. Read-only checks confirm active
UPower, GetCriticalAction=Hibernate, installed percentage policy 15/5/2 and
inode/mount-point → yazi-xdg.desktop. Waybar notifies at 15%/2%; only UPower takes
the 2% action, after its native ~20 s delay, with possible PowerOff fallback if
Hibernate is unavailable. Real low-battery triggering and sufficient reserve are
unverified; do not deliberately discharge or fake live battery state. Statistics
remain deferred. The current installation/maintenance guide is
`hosts/laptop/README.md`; `docs/laptop-audit/lenovo-checklist.md` tracks scoped
acceptance, while `lenovo-history.md` preserves the old preparation timeline.
Do not repeat historical failures, require both closures in RAM, or rerun Disko
on the installed host. Native nixos-install builds into the mounted target store;
first standalone HM follows installed boot, console/network setup and login as samov.

Disko is imported directly by fresh `server`, `laptop`, and `desktop-next`
targets. It runs only through an explicit Disko/nixos-anywhere command, never
through `nixos-rebuild switch`. Existing `laptop-old` and `desktop` intentionally do
not import Disko.

Lenovo target: `laptop` has a separate `samov-laptop` HM output and
`home/linux/laptop` leaf. Acer moved to `laptop-old` with its hardware/settings
preserved except hostname. After the full input update and final configuration
review, the user-approved deliberate install guard was removed on 11.11.2026;
NixOS toplevel evaluation and all merged assertions pass without builds/IFD.
See `hosts/laptop/README.md`. Disko selects the live-observed UMIS NVMe topology
path; recheck disk identity before destructive use. Agreed: plain ext4 + 48 GiB swap,
no zram initially (commented opt-in with evidence-based conditions), weekly GC
keeping 10 NixOS + 10 HM generations. Initial login matches Acer: one tty1 autologin
per boot, the same public bootstrap password and password-authenticated sudo,
no Hyprlock/fprintd; improvements wait for live Lenovo. No extra Acer groups or
trusted-users privileges are copied. Do not apply the Lenovo HM
profile on Acer. Native PPD/Waybar switching is Lenovo-only. The leaf selects a
local Waybar override for dynamic previous/current/next tooltip labels, sharing
one cycle helper with clicks; stock Waybar has no such placeholders. See
`home/linux/laptop/waybar/README.md` for checks and update obligations.
Only the helper/patch/declarations are checked, not the full binary or live UI.
Lenovo graphics uses `hosts/laptop/graphics.nix`: released `linux_latest` from the
kernel-only input, existing unstable `linuxPackagesFor` recipes for matching
NVIDIA latest/open, and unchanged unstable linux-firmware. Selected declarations
check the NVIDIA open module's actual kernel header paths and matching compiler;
the user built the new 7.3.4/NVIDIA 615.78.08 combination. Existing result's kernel,
patch inputs and module metadata are reviewed, not module loading/live behavior.
It is now applied/booted on 7.3.4 with NVIDIA loaded; GPU/offload/Hibernate functional
acceptance remains pending. See the graphics audit's latest section.
Mesa 64/32-bit stays with stable host
userspace/glibc: installed stable Hyprland aborted loading unstable Mesa with
`GLIBC_2.43 not found` (stable glibc 2.42). The user approved Mesa-only correction;
kernel/NVIDIA/firmware and lock stay unchanged. Focused declaration checks pass;
the corrected system is not yet built/applied or live-tested. Do not mask this
with LD_LIBRARY_PATH/glibc replacement or fix only the compositor package.
A separate unfree-enabled `pkgsGraphics` import
is passed only to this NixOS output; a local overlay replaces only linux-firmware,
preserving other firmware and existing hosts/HM package sets. No beta/testing,
hardcoded version, lock update or automatic updater. User-provided live scan is
imported without filesystem declarations. PRIME offload is selected, with Intel
`PCI:0:2:0`, NVIDIA `PCI:2:0:0` and `nvidia-offload`; never force the whole Steam
client or global GPU variables onto NVIDIA. Agreed power baseline keeps native
NVIDIA 615/open VRAM/suspend handling. The earlier default-only RTD3 plan is now
superseded by the approved Lenovo finegrained opt-in above; still no forced
S0ix/deep, legacy suspend units or Dynamic Boost. Real idle/resume
remain unverified. Declaration fixtures and selected merged graphics checks pass
with the updated inputs, including NVIDIA/open derivation evaluation.
Initial 20/90 s timeouts were followed by bounded diagnostics and a successful
graphics check after cache restoration. Selected merged storage/resume checks pass;
after guard removal all merged NixOS assertions pass. Full Lenovo
HM activation derivation evaluation passed in a separately approved 180 s run
after two 90 s timeouts. This does not establish a built/activated HM generation.
No full builds or live installed graphics/resume checks. See `docs/laptop-audit/graphics.md`.
Before main closure downloads, settle Lenovo's storage-aware install/build order:
the live writable store is RAM-backed (~14 GiB previously free), not assumed large
enough for both closures. Do not build updated HM on space-constrained Acer.
No destructive/install consent follows from evaluation or guard removal. First
installed boot needs local console/network setup and separate standalone HM;
live SSH does not persist and the target does not enable an SSH server.

## Ключевые паттерны и gotchas

### stateVersion

- Базовый `home.stateVersion` задан как `lib.mkDefault "25.11"` в `home/users/samov/default.nix`; legacy desktop/laptop-old/mac сохраняют это значение.
- Fresh server использует `system.stateVersion = "26.05"` и явно импортирует `home/users/samov/state-26.05.nix` через `flake.nix`.
- Для нового fresh host повторить ту же схему: system state в `hosts/<host>/default.nix`, Home Manager state module в его `modules` array.
- Когда все хосты перейдут на 26.05, удалить `state-26.05.nix`, заменить common `mkDefault` на `"26.05"` и убрать ненужные version-gated compatibility branches.

### Version-gated настройки

Три места гейтятся через `(lib.versionOlder config.home.stateVersion "26.05")`:

- `home/gui-set/default.nix:10` — Firefox configPath (`.mozilla/firefox` на старых хостах).
- `home/core-set/shell.nix:65` — Yazi shellWrapperName `yy` на старых хостах.
- `home/linux/modules/hyprland/default.nix:12` — configType `hyprlang` на старых хостах.

На новых хостах с stateVersion >= 26.05 условия ложны, поведение по умолчанию.

### Home OpenCode

- Shared exploration policy lives in `home/apps/opencode/config/AGENTS.md`. Use native
  glob/grep/read and tool-output artifacts; mechanical extraction needs no extra
  model. RLM is archived under `archive/rlm-disabled`, excluded from installation
  and normal tests. Home changes do not update the corporate Mac profile.

- Ручной порт на корпоративный Mac: актуальный снимок `~/.config/opencode`
  → объединить общие Linux-улучшения с корпоративными особенностями → полный
  архив для замены всей папки конфигурации. Сохранять модели, proxy, MCP,
  voice/TUI, permissions и npm-манифесты; перенос global-rules → AGENTS
  выполнять внутри архива. `node_modules` не включать: OpenCode устанавливает
  зависимости из package.json при запуске. Короткая инструкция — только
  README архива; отдельного сборщика/мигратора нет. Полные снимки/архивы могут
  содержать авторизацию: держать вне Git, не выводить секреты в логи.

- `home/apps/opencode/default.nix` — HM laptop/desktop на pinned OpenCode 2.1.4
  (отдельный flake input, не nixpkgs-unstable). `package.nix` добавляет
  `patches/session-routing.patch`, `patches/manual-model-routing.patch`, `patches/model-variants.patch`, `patches/session-attention.patch`,
  `patches/question-location.patch`, `patches/theme-mode-cache.patch` и Linux runtime libraries. V1-модуль/исследования —
  `archive/v1`, не импортируются. README/BENCHMARK описывают текущий V2.
- Исходники сгруппированы: `config/` (V2 settings и global rules), `plugins/`,
  `patches/` (включая общий session-attention helper), `scripts/`, `skills/`,
  `sounds/`; структура установки в `~/.config/opencode` не меняется.
- Native V2 config — `config/v2-settings.nix`; установленные plugins — directories с `index.ts`/`tui.ts`
  и API `@opencode/plugin`, не V1 `@opencode-ai/plugin`.
  Model-routing собирается одним store-каталогом, HM `recursive = true` сохраняет
  managed leaf paths. Отдельные store-файлы ломают относительные импорты Bun;
  PTY проверять также с `OPENCODE_TEST_HM_GENERATION` из собранного профиля.
  Server plugins — directory symlinks `*-v2` в store с обычным `index.ts`:
  V2 discovery молча исключает entrypoint, чей realpath вне real plugin root.
  Старые leaf paths убираются HM cleanup; IDs/history сохраняются. Проверять
  server runtime также с `OPENCODE_TEST_HM_GENERATION`, не только копиями.
  Resolver остаётся штатным. После HM updates, меняющих store-каталоги плагинов,
  завершить активные задачи, выполнить `opencode service restart`, затем
  `opencode service status`: кеш Bun может оставить старый entrypoint и молча
  исключить плагин даже после `/reload`. Проверку containment не отключать.
  Закрывать все клиенты заранее не обязательно; restart прерывает серверные задачи.
  После замены binary переоткрыть TUI. Обычные config edits не требуют restart.
  Runtime smoke с HM generation проверяет загрузку ссылок в новом процессе.
- `/delegated-review` is a portable Markdown command in `commands/`, declared for HM installation
  without replacing built-in `/review`. The existing general-purpose `review`
  agent reads `config/review-system.md`, retaining model routing and read-only
  permissions. The command owns immutable scope/fingerprint, minimal independent
  handoff and bounded same-child recovery: initial plus six shared continuations/
  replacements/report repairs, transient-error waits 20/40/60/90/120/120s and a
  10-minute no-progress recovery limit. Never duplicate a running child or infer
  completion from a file read/native idle/text alone. Incomplete coverage has no
  final verdict. Shared counters explicitly count report repairs (INCOMPLETE +
  continuation = 1/6 additional used); provider retries only select backoff. Exact
  canonical JSON `dr-scope-v1` plus executable hash recipe replaces ambiguous NUL
  descriptions; never brute-force a missing recipe. No plugin/permanent checkpoints
  or corporate edits. A user-run Big Pickle test and read-only audit confirm
  same-child INCOMPLETE → COMPLETE, not provider recovery or perfect compliance.
  Six settings/static/hash-recipe, two Git-offline and four fixture-unit tests
  pass. The approved private native HTTP-429 fixture passes: one native retry;
  eleven failures exhaust ten retries, then actual sleep 20 and same-child
  continuation preserve one read without rereading. Scripted mock decisions do
  not prove real-model compliance or full-budget/replacement recovery. A second
  Big Pickle smoke confirms waiting, two-file scope/hash, 1/7 and complete report
  preservation, but took 400s and wrote an external temporary helper. Follow-ups
  clarify first-invocation-only initialization, forbid agent-created temporary
  review artifacts (not native runtime storage), and explicitly bar all final
  verdicts for incomplete coverage. These new guards are not new live acceptance.
  Minimal Mac transfer can preserve corporate model/permissions without home
  plugins/binary patches. A separate four-file package (including a Russian human
  guide) is in `~/Downloads/delegated-review-mac-2026-11-12/`, outside Git; original
  drafts and corporate config are untouched, no Mac acceptance yet. No agent build/
  activation. See `home/apps/opencode/DELEGATED-REVIEW.md`.
- The 2026-11-13 reviewer revision follows a user-supplied R1/R2 comparison:
  behavior/counterexamples precede reporting; material unmet requirements or
  acceptance-changing contract questions require REQUEST_CHANGES, not approval
  with buried caveats. Parent checks consistency without rewriting child verdicts.
  Recovery/model/permissions remain unchanged. Eight settings/static/hash and
  seven synthetic-candidate oracle checks pass, not real-model quality acceptance.
  Blind A/B instructions are in tests/fixtures/delegated-review/EVALUATION.md;
  no live run/build/activation. A separate four-file Mac candidate is in
  ~/Downloads/delegated-review-mac-2026-11-13-scenario1/; command/prompt match source,
  previous package/archive are untouched. The supplied opc-loc.zip Chrome-MCP audit variant
  was only identified; its second scenario remains deferred until the first is settled.
- A user-run same-diff review of that first analysis revision found caret loss
  and requested email changes, but widened accepted overwrite to caret acceptance.
  The full handoff also generalized unknown-ID bubble skip to ignored rejection
  and a failed typecheck to "clean apart from" an env error; the child dropped it.
  Current `Review policy: behavior-v2.` bounds claims/acceptance to specific effects,
  separates handoff code observations from requirements, preserves failure qualifiers
  and does not automatically raise severity or require deduplication. Ten settings/
  static/hash and nine synthetic oracle checks pass, not live v2 acceptance.
  Separate Mac candidate: ~/Downloads/delegated-review-mac-2026-11-13-scenario1-r2/;
  previous packages/exports/archive unchanged, no agent build/activation/model run.
- A later supplied behavior-v2 run is a limited positive same-diff result, not
  general reviewer acceptance; TS2688/conditional history restore remain caveats.
  The subsequently authorized Chrome scenario now adds a self-contained passive
  `/delegated-review-chrome`, `Audit policy: chrome-evidence-v1.`, without changing
  shared reviewer/routing. It distinguishes effect/fixture legitimacy and per-claim
  support/contradiction/absence/contamination; missing required evidence means no
  final verdict. One necessary private parent export is allowed, never child writes
  or browser actions. `drc-scope-v2` freezes evidence/provenance, not authenticity.
  Six static/hash/fixture-integrity checks and eight human-oracle cases are not
  model/browser/export acceptance. Separate three-file Mac package:
  ~/Downloads/delegated-review-mac-2026-11-13-chrome/; prior packages/archive unchanged.
  No agent builds/activation/model/browser tests. See DELEGATED-REVIEW-CHROME.md.
- `/problem-brief` is a manual in-session command, not an automatic review stage,
  skill or agent. After initial byte-exact import, the user approved home-only Scope
  and local-read changes: default is the preceding assistant response; arguments
  select source/scope/output, including local Git and completed-work summaries.
  Downloads/Mac originals stay unchanged; earlier model tests cover the original,
  not new scope semantics. Preserve remaining prompt rules; do not optimize/reformat
  or add model/effort overrides without authorization.
  HM installs the guide outside commands. Briefs supplement full reports, never
  replace evidence or independent-review handoffs. See the module README.
- Глобального formatter и его CLI-зависимостей в OpenCode нет. Короткое правило в
  `config/AGENTS.md` требует использовать объявленный проектом CLI только для
  изменённых файлов; без правил сохранять оформление, без global fallback или
  форматирования моделью. Runtime smoke проверяет отсутствие автоформатирования.
- `decision-support.nix` — явный домашний opt-in через
  `programs.opencode.decisionSupport.enable`: короткие configured instructions,
  on-demand `decision-check` и `agent-todo-v2`. Todo — ручной Markdown/Git в
  `~/agent-todo/todo.md`, не HM-managed content. Native question показывает изменения
  и ручные правки; запись/локальный коммит только после согласия, Plan guard
  независим от session grants. Stable IDs и hash user-message в Markdown
  дедуплицируют подтверждённые обращения; Visits считает интерес, а независимый
  Priority — High/Normal/Low (по умолчанию Normal). Visits — интерес, не срочность.
  Нет фонового семантического детектора/LLM или polling.
  F3/`agent-todo-open` открывает файл в Kitty/Neovim на laptop/desktop, F1 содержит
  этот bind. Live UI/compositor проверяются на целевой машине; runtime smoke
  проверяет native forms API/Git в изолированном HOME.
  Новые заметки: `## [ ] N. Заголовок`, затем закрытый `<details>` с
  `<summary>` — кратким резюме задачи в одном предложении, не общим «Подробности»
  и не дублем короткого говорящего заголовка; ID, счётчик, цель/возврат/заметки внутри.
  `changes.add` назначает следующий номер кодом; title передавать без номера.
  Номер не является stable ID или приоритетом. Ручные `[ ]`/`[x]`, номера и старый
  формат сохранять; автоматической перенумерации нет.
  HTML-спойлер не включает folds в обычном Neovim buffer.
  Чтение `~/agent-todo/*` явно разрешено без prompt, запись остаётся за edit/Plan
  guard и подтверждением изменений. Todo UI, reason и служебные поля — английские;
  новый контент по умолчанию английский даже при русском запросе, русский только
  по явному указанию. Старый контент автоматически не переводить. Артефакты
  (код, конфиги, команды, логи, ошибки, пути, IDs, URLs, дословный текст) сохранять
  на исходном языке и без перефразирования; переводить только по прямому запросу
  перевода конкретного артефакта. Язык запроса сам по себе не делает его артефактом.
  `changes.update` меняет явные Priority/Status (Todo/In progress/Done).
  `sort: true` — только по запросу: In progress → Todo → Done; первые две группы
  по Priority, Visits ↓, Created ↑; Done по Completed ↓. Даты Unknown идут в конце,
  равенства сохраняют порядок. Номера/IDs и содержимое не переписываются; старые
  даты восстанавливаются по ограниченной локальной Git-истории с пометкой источника.
  Created/Completed и Total/Done/In progress вычисляет код; ручное закрытие помечается
  Observed, повторное открытие снимает Completed. Без фонового наблюдения.
  Только затронутые заметки/строки вместо unified diff; ручные правки показаны
  отдельно без обрезания. В 2.1.4 question description не прокручивается: todo-плагин
  использует `agent-todo-tui.tsx`: public dialog/slot/keymap/form API, одна полная
  заметка на вкладку с внутренней прокруткой, сразу первая задача. Без Proposal,
  счётчиков Review/Change и HTML-обёрток; в Markdown spoilers сохраняются.
  ←/→, Tab/Shift+Tab циклически листают, ↑/↓ прокручивают заметку, Home/End — начало/конец.
  На финальной вкладке ↑/↓ выбирают Submit/Reject/own answer; Ctrl+↑/↓ прокручивают
  пояснение, путь, commit и ручные правки. Подсказка в привычном native-стиле;
  PgUp/PgDown не листают вкладки. Одна native form — только consent/cancel transport;
  `agent-todo-review.ts` связывает поля с IDs и Submit с конкретным предложением.
  Без TUI presenter stock form не даёт случайно сохранить обрезанный текст.
  Непрозрачная подложка плагина скрывает underlying Questions до удаления формы
  после ответа/отмены, без правки host tree/cache. PTY 140×40 и 160×48 проверяет
  отсутствие второго видимого Questions/own-answer/hint, включая финальную вкладку.
  Только финальный Submit без комментариев сохраняет весь файл одним коммитом;
  Reject/Esc/закрытие/уход с сессии отменяют пакет. Reload не даёт автоматического согласия.
  Fingerprint проверяется перед формой и записью; локальное листание не вызывает
  сервер/модель. `a` открывает own answer текущей заметки, Enter сохраняет комментарий
  в форме, Tab сохраняет и листает. Любой комментарий блокирует запись; инструмент
  возвращает `feedback: [{id,title,feedback}]`, глобальный `batchFeedback` и исходный
  `draft`. Модель меняет только затронутые формулировки, сохраняет остальные черновики
  и снова запрашивает согласие. Реальный PTY 80×24 проверяет конец длинной заметки,
  циклическую навигацию, изоляцию/восстановление комментариев и однократный commit.
  `changes.add` принимает
  формулировки, код собирает Markdown/spoilers и сохраняет остальные записи побайтно;
  `changes.replace` делает точечные unique-match правки внутри stable ID, без metadata.
  Для возврата достаточно `revisited`. Полный `content` — совместимый путь только
  для явно запрошенной перестройки файла. Вложенный `changes` не попадает в огромную
  строку native generic-tool summary; старые вызовы в истории не переписываются.
  Merge/diff/counters/review/Git выполняются кодом, без модельных вызовов между
  вкладками. Новый binary patch не нужен. Esc перехватывает только `QuestionTool.CancelledError` и
  завершает tool обычным `declined`; остальные ошибки/abort не подавляются.
  `question-location.patch` сохраняет Location
  nested native question из Promise-плагина: без него форма есть в API, но не
  видна TUI. PTY smoke проверяет реальные кнопки. Этот patch меняет server runtime:
  после первого применения завершить задачи и выполнить `opencode service restart`,
  проверить `opencode service status`, переоткрыть TUI; одного `/reload` недостаточно.
- `/switch-free`/`/switch-paid` — локальные TUI-команды, без LLM. Режим живёт
  в metadata корневой сессии и влияет на последующие запросы существующих детей.
  Paid role table — единый `plugins/model-routing/routing-models.json`: Sol High work, Sol XHigh plan,
  Luna Max explore, Sol High compaction/summary, Luna Low title. Free — Big Pickle
  для всех ролей, без автоматического paid fallback. Обычная compaction до
  явного переключения сохраняет наследование session model.
  Manual model selection keeps one Free/Paid helper stack: configured Sol/Luna
  select Paid, Big Pickle selects Free, and unknown identities prompt for the
  helper stack. Do not infer a stack from provider names or catalog prices.
  Model/effort overrides are scoped to session and agent in live-root metadata;
  effort changes preserve helpers and never save a global model preference.
  Old global variant preferences must not override configured agent defaults.
  Explicit `/switch-free` or `/switch-paid` resets all overrides for the family;
  automatic agent switching preserves them. Home selections carry their metadata
  into native session creation. `manual-model-routing.patch` awaits durable policy
  updates before applying selection; reopen TUI after replacing the binary.
  `LocalProvider` wraps `DialogProvider`: NEVER call `useDialog()` from its init.
  The nested `App` binds its dialog instance through `bindHelperDialog` with cleanup;
  unknown-model selection cancels safely before binding or after disposal.
  После metadata mutation вызывать `data.session.invalidate(id)` перед `sync(id)`:
  sync кеширует hydration и иначе оставляет старый режим/модель в TUI. PTY проверяет
  public `ui.model.current()` после переключений и настоящего model picker, не одну DB.
  В каталоге только настоящие Sol/Luna с variants High/XHigh и Low/Max, без
  role-specific aliases `(plan)`/`(summary)`/`(explore)`. `model-variants.patch`
  нормализует старые session/model-routing ссылки при чтении, без правки DB/history.
  Старый `variant = "default"` у alias означает его прежний effort, а не потерю
  XHigh/High/Max; явный non-default variant сохраняется. Проверять старые сессии
  через настоящий runtime, не только plain-object unit fixture.
- Auto compaction: soft input 244000 − buffer 32000 = 212000; output 128000,
  keep.tokens 15000. V2 не имеет прежнего `prune=false`; между шагами возможен overshoot.
- Theme `mode = "system"` follows terminal appearance, not GTK; `name = "system"`
  selects a terminal-derived palette, not an automatic-mode requirement. Keep the
  user's Flexoki choice. `theme-mode-cache.patch` gives fresh renderer appearance
  priority over saved system-theme colors, after explicit light/dark locks. Never
  delete personal cache/preferences to mask this startup bug. Four actual-patch
  policy tests pass; approved isolated installed-binary PTY reproduces the old
  stale-cache bug and fresh-cache control. The user built the fixed HM output;
  both PTY controls pass on that result after fixing relative-path resolution
  in the harness. A separate Kitty 0.47.0 auto-theme exception then explained the
  remaining live failure; its local backport was deliberately dropped (see Kitty
  below), not the independently confirmed OpenCode 2.1.4 cache fix. Reopen TUI
  after applying this client-only patch; no service
  restart required. See README/BENCHMARK and `tests/test_theme_mode_tui.py`.
- `plugins/limits/` — local V2 hooks/RPC/TUI, без стороннего quota-плагина,
  отдельного LLM и idle network polling. OpenAI ChatGPT OAuth usage snapshot,
  общий per-account cache и event-driven active workers (не открытые вкладки).
  Проценты доступны только через legacy Codex OAuth; token sharing показывает
  `Limits: not exposed by token sharing`, без legacy HTTP/cache/WS и credential
  fallback. Active и ручные checkpoints сохраняются. `default.nix` напоминает
  `OPENCODE QUOTA API` при HM evaluation/build и activation (штатный жёлтый warnEcho).
  Проверять openai/codex#54219/API вручную при обновлении; удалять reminder только
  после реальных процентов/reset times, account switching и per-window warnings,
  не просто закрытия issue. Ссылки/границы проверки — README/BENCHMARK.
  Пятичасовой резерв 15/20/25% для 1/2/3 workers, warning на 10 п.п. раньше;
  недельные пороги — каждый пятичасовой × 3/22 с округлением до целого процента.
  Статусный `⚠` рядом с каждым сработавшим окном: ранний серый, основной жёлтый;
  без отдельного поля предупреждения, автоматических бюджетных инструкций модели
  и `notices`. Latch сохраняется после checkpoint, уменьшения
  workers и обновления порогов до подтверждённого renewal / >95% остатка.
  `/limits-reset` — подтверждённый override текущих limiting windows, не quota reset;
  `/checkpoint` — явный reviewed handoff request, `/checkpoint-reset` — pending.
  `Checkpoint +/✓` всегда отображается и означает agent-reported смысловую готовность,
  не Git status. Review → fixes → repeat review до отсутствия blockers; Git commit
  только по отдельному прямому запросу пользователя; `/checkpoint` больше не
  разрешает его. Без запроса reviewed изменения остаются незакоммиченными с
  перечислением в handoff, что не блокирует готовность. Native `git commit`
  permission — Ask (не выдавать Always); остальные Git-команды без изменений.
  Без Git — связный код/текст и resume plan. Plan не обходит.
  Checkpoint state — session metadata; private hashed account cache — XDG state.
  `Session.Info.metadata` необязательно: отсутствие означает pending; server hooks
  не должны ломать prompt/tool admission. `checkpoint_ready` — direct tool с
  `codemode: false`. Unit/mock и узкий native runtime `test_v2_runtime.py --limits`
  покрывают отсутствие metadata, prompt/tool и создание/сброс checkpoint; живой
  OAuth/quota, installed HM layout и настоящий TUI/PTY не проверены. См. README.
  Prepared reconnect fix replaces the one-shot RPC subscription with the host's
  reconnecting data stream and refreshes limits/checkpoint on server.connected.
  Current Lenovo cache/RPC were fresh while the old TUI remained frozen after
  the logged 00:55 UTC disconnect; pinned RPC/SharedEvents reproduce the failure
  with mocked transport. The targeted 22 unit/declaration/TUI-fixture checks pass,
  not live fixed UI acceptance. No restart, build, activation or commit by agent.
  The changed store plugin directory needs the established post-HM service restart
  and TUI reopen in a later user-chosen maintenance window, not now or via /reload.
- `/permissions` is a prepared TUI-only saved-Always manager for the current native
  project ID, not configured policy. Public native select/confirm replace custom
  rendering: search/arrows select, Ctrl+D or Enter requests confirmation, q/Esc
  closes the list and Cancel/Esc cancels confirmation. Completion uses a toast,
  without reopening. Frozen scope and fresh pre-delete validation refuse stale
  operations, not automatically close dialogs. Disposal avoids global clear:
  public promise dialogs have no ownership handle. The ID-only API remains
  non-atomic; dispatched DELETE cannot be undone. Twenty-two actual-controller/
  HM/native-dialog fixture tests pass, not native TUI/PTY/installed-generation
  or very-long-pattern layout acceptance. The user subsequently accepted the
  native UI; this is user-reported acceptance, not independent agent observation
  or proof of every deletion/layout scenario. No live grants deleted, service
  restart, build or activation by agent. Apply HM/reopen TUI; the separate
  limits/server changes still need their later maintenance window. See README.
- Audio — только native notifications/OpenTUI; mutable `cli.json` seeded once,
  `attention.sound`/volume/custom permission/done/error sounds. Старые V1
  notifications/mute plugins не устанавливаются. `quiet-urgency.ts` независимо
  от mute вызывает только `silent-attention.py`, без BEL/второго player.
  `session-attention.patch` + общий `session-attention.ts` изолируют native
  sound/notifications/error-toasts and local urgency through one last-selected
  live TUI per root-session family, including inactive internal tabs. Shared tab
  membership cannot claim ownership; home/plugin/workspace navigation retains
  still-open claimed tabs. Closing releases a claim; stale PID/start-time records
  are ignored. Private runtime IPC freezes an owner per event and deduplicates
  native/urgency channels separately; no player, BEL, service or idle polling.
  The user reports the revision works live; this is scoped user acceptance, not
  independent agent observation of the full multi-window/focus/crash/mute matrix.
  Six policy/actual-handler/two-process tests and three silent urgency fixtures
  pass; no agent build/activation. The updated PTY harness is not run.
  Unknown ancestry/sessionless forms stay silent. После замены
  binary переоткрыть TUI (не только `/reload`); общий server менять не нужно.
  Самостоятельный Mac archive с официальным binary не содержит этот patch.
  Quiet urgency устанавливается одним store-каталогом с TS helper и Python kitten;
  imports/assets относительны к real entrypoint. Не подставлять пути flake source
  через replaceVars: прежний output не имел Nix references, и GC удалял helper.
  Для исторического отказа todo после GC эта причина не подтверждена; при проверке
  он был загружен. Известный кеш при retarget plugin symlink — отдельный случай.
- Звуковая граница: домашние anime done/error и freedesktop permission — только
  для личных laptop/desktop. Корпоративный Mac использует стандартные встроенные
  звуки и штатный `opencode.notifications`; удалённый `session-notifications`
  не восстанавливать. При Mac-порте не копировать домашний `cli.json`,
  `attention.sounds`, аудиофайлы или `quiet-urgency`; сохранять Mac CLI preferences
  отдельно от командного репозитория. Кастомизация native sound settings и
  изоляция через binary patch независимы. См. `home/apps/opencode/macos/README.md`.
- `workspace-context.ts` использует native V2 TUI data/router; реальный PTY smoke:
  `OPENCODE_TEST_BINARY` указывает на собранный V2 binary (см. BENCHMARK).
- Permissions — native baseline плюс Git network policies и `git-offline.ts`
  (transport/lazy-fetch env). Cached `remote show -n` не равен сетевому `show`.
  `permission-stats.ts` — native event stream, прежний history + session/request IDs.
- `opencode-task-report --session <id>` — read-only per-task accounting; методика
  в `home/apps/opencode/BENCHMARK.md`. Старые ledger-файлы XDG state
  `opencode/task-usage` сохраняются. `model-calls.ts` пишет отдельные session
  transport attempts (kind, model/variant, wire model/effort, HTTP headers status)
  в private0600 `opencode/model-calls/<session>.jsonl`, без prompts/URLs/headers.
  Отчёт читает журнал отдельно от token totals; старые title models не восстановить.
  Title usage есть в native V2 events, но не добавляется к message totals отчёта;
  это не invoice или измеритель подписочной квоты. WS response.create проверен
  unit-тестом, реальный HTTP — mock runtime с retries и обеими compaction.
- Verification coverage after changes: build without activation, isolated V2
  runtime/mock Responses, native and summarizing compaction, title/summary/children,
  and real TUI PTY. This is a coverage checklist, not authorization to run it
  automatically. Leave builds to the user unless explicitly requested; obtain
  separate approval before resource-intensive runtime or PTY checks.
  `tests/test_v2_runtime.py <binary>`: обычный, `--native`, `--catalog`, `--mac`.
  Live Kitty/audio/Waybar и Mac AVFoundation проверяются на целевой машине.
- Mac source overlay — `home/apps/opencode/macos/`; актуальная база — `Downloads/opc.zip`.
  Полный архив вне Git, два слоя opencode/opencode-local, native `{env:...}`,
  `.env.example` в Fish и явный source. Для shared service нужно окружение
  самого server/launchd, не только TUI. Локальный voice V2 использует ffmpeg +
  whisper.cpp, V1 npm voice plugin не подключать. Инструкция — README архива.

### Kitty langmap

- Kitty 0.47.0 has an auto-theme notification bug, fixed upstream by
  `2d9b10413490` / Fix #10058 in 0.47.1. The user deliberately removed the local
  backport, overlay and dedicated tests before migration, accepting Acer's live
  switching limitation until an update. Do not restore commented workaround code.
  The existing Lenovo checklist requires Kitty ≥0.47.1 and live F11 both ways;
  a fresh install using the same flake.lock does not upgrade packages. The separate
  proven OpenCode 2.1.4 startup-cache fix remains enabled. Temporary live tracing
  and fix trials were restored/disabled; no backported Kitty package was applied.
- `home/modules/kitty/default.nix` собирает version-matched template из `${pkgs.kitty}` с common и Linux/macOS fragments, затем `build.py` дублирует каждую active `map`-строку с русской раскладкой. Commented upstream examples никогда не активировать. Не возвращать полную snapshot-копию upstream `kitty.conf` в репозиторий.
- `map.txt`: две строки — латиница и транслит (йцукен→qwerty).
- Активные настройки в сгенерированном конфиге: Fish, 10k scrollback, nvim pager, font size 14, NotoSansM Nerd Font Mono, grid layout, remote control, powerline tabs. Linux сохраняет stock Kitty shortcuts; macOS `kitty_mod = Cmd+Shift`, `Cmd+N`/`kitty_mod+N` создают nvim tab, `Cmd+E` — Yazi, panes `kitty_mod+Left/Right`.

### Alacritty + toggle-theme

- Темы хранятся в `~/.config/alacritty/themes/{dark,light}.toml` как symlinks.
- `toggle-theme.sh` (F11): меняет dconf GNOME color-scheme и GTK3 gtk-theme (`Adwaita`/`Adwaita-dark`), вызывает native Qt appearance helper, меняет Alacritty symlink и уведомляет через hyprctl. Не пишет в Ardour UI config.
- Ordinary GTK3 apps such as Blueman follow the native GTK theme through the
  Wayland settings/portal path, without a GTK_THEME override, extra service or
  app wrapper. GTK and Qt dark names differ in case. F11 fixtures and real dconf
  on a private bus are checked, not live Blueman rendering/portal notifications,
  XWayland or arbitrary custom/sandboxed UIs. No activation dconf writes; the next
  F11 synchronizes both keys. See `docs/laptop-audit/gtk-theme.md`.
  The GUI set must install `gnome-themes-extra`: GTK3's built-in Adwaita dark
  variant is not the named `Adwaita-dark` theme. Without the upstream alias GTK
  silently falls back to light even when dconf/portal/settings report the dark
  name. Native GTK CSS-color fixtures reproduce this and verify the exact alias,
  not the built package/installed layout or live Blueman. After first adding the
  package, reopen GTK apps to discard a previously cached missing-theme fallback.
  The user then confirmed Blueman works on Acer; this is user acceptance, not
  independent agent UI verification or evidence for every GTK app/host.
- `home/linux/modules/ardour` wraps unchanged stable Ardour on the three Linux GUI
  HM profiles. Desktop/CLI startup reads the same dconf mode and selects built-in
  `captain_light`/`dark` in an existing mutable ui_config, with one original backup.
  No live hook/daemon, no activation edits; running instances and first-run setup
  are left alone. Major comes from the package. Synthetic launcher/F11/process
  fixtures and selected merged declarations are checked, not the full HM build,
  installed desktop or real DAW UI. See the module README for limits/application.
  The user subsequently confirmed the Acer startup-theme scenario works; this
  does not establish independent agent UI coverage or desktop/Lenovo acceptance.
- `alacritty-preview` позволяет пролистать все темы из alacritty-theme.

### Hyprland

- Shared Linux GUI HM security enables native `services.hyprpolkitagent` on
  Acer/desktop/Lenovo, tied to UWSM's graphical session; no extra exec-once.
  Mac/server are unchanged. Blueman's Polkit build override is separate and
  NixOS-only on the two laptops. Stock Blueman permits its four helper actions
  to wheel without authentication; do not call this per-application isolation.
  Fixture/declaration checks pass; installed Acer POLKIT=True/actions/wheel rule
  are checked and the user confirms a pkexec password prompt with the agent active.
  This is not independent GUI/PAM or Bluetooth helper-action coverage; other hosts
  remain unverified. The host-portal app-ID warning did not block that scenario.
  See `docs/laptop-audit/polkit.md` for apply/acceptance and override cleanup.
- Native desktop portals remain Hyprland + GTK with Hyprland's supplied
  `default=hyprland;gtk`, not a custom routing policy. Selected three-host
  declarations, installed Acer config/descriptors and active service states are
  checked, not live chooser/screen sharing or per-client environment/overrides.
  Do not add routing/cache workarounds solely for the agent's already-associated
  app-ID warning. See `docs/laptop-audit/portals.md` and the Lenovo checklist.
- Disk status in shared Waybar is `custom/disk` on Acer/desktop/Lenovo: home
  filesystem available/total GiB plus whole backing-disk I/O busy %, read/write
  MiB/s in tooltip. A Waybar-owned Python JSON stream reads statvfs/sysfs every 5s,
  no new service/cache/load test. Missing/stacked devices never pretend idle 0%.
  `programs.yazi.freeSpaceStatus.enable` disables only the legacy FREE widget on
  those GUI profiles; Mac/server retain it, the separate Yazi context hook stays.
  Helper fixtures/configs/five selected HM declarations and a short real Acer
  read-only helper smoke pass; installed panel/GTK/other hardware not verified.
  See `home/linux/modules/waybar/README.md`; apply HM and reload Waybar via USR2.
- Qt appearance — shared `home/linux/modules/qt-theme` on Acer/desktop/Lenovo only:
  native qt5ct/qt6ct proxies with Adwaita, no fixed `QT_STYLE_OVERRIDE`.
  The systemd session override uses native
  `${QT_STYLE_OVERRIDE:+}` to clear inherited values: literal empty assignments,
  even quoted, are rejected by the installed environment.d generator. Evaluated
  Lenovo HM text passes native isolated-generator regression checks and five
  profiles' selected declaration checks. The user applied the corrected Lenovo
  HM and rebooted; the assignment is installed without the generator error.
  This does not establish installed Qt appearance/live F11 acceptance.
  F11 updates mutable appearance-only INI keys; native plugin watchers reload open Qt Widgets
  apps (qt6ct debounce ~3 seconds), no daemon/polling. HM activation also migrates
  nomacs to `System.css` + `qt6ct-style`, with one-time backups and unrelated
  preferences preserved. Close Qt apps before activation and start a fresh session
  to replace stale environments; old `uwsm/env-toggle` is no longer sourced.
  Helper/F11 fixtures, five profiles' selected merged attributes and isolated real
  nomacs Qt6 startup/live/reopen rendering passed. Qt5, all other apps, installed
  HM layout and live Wayland/F11 remain unverified. See the module README.
- Конфиги хостов — raw `.conf` файлы, подключаемые через `xdg.configFile`. Не NixOS-модули.
- Laptop: без compose:ralt (xremap перехватывает), есть `on_focus_under_fullscreen`.
- Desktop: compose:ralt активен, есть `new_window_takes_over_fullscreen`.
- Оба: dwindle, zero gaps/borders, UWSM autostart, waybar, terminal-layout-en.sh.
- Системный Wayland bell: `onionbell.service` в HM-модуле Hyprland воспроизводит общий `xdg-system-bell-v1` (не только Kitty). Пакет pinned в `pkgs/onionbell`, с compatibility-правкой для отсутствующего `clients.pseudo` и `ogg-first-span.patch`: Rodio 0.21 принимает пустой первый Vorbis span за EOF; полное декодирование короткого bell в PCM устраняет тишину. Регрессионный тест пропускает настоящий freedesktop `bell.oga` через output mixer. Kitty использует `enable_audio_bell yes` в `common.conf`. После перехода с 0.55/0.56 на Hyprland со встроенным звуком bell (upstream PR #15502) удалить onionbell service, чтобы исключить двойное воспроизведение.
- `ipc-eof.patch` в onionbell завершает IPC reader при обрыве соединения вместо busy loop с ростом памяти. Независимые `ipc-test-harness.patch` и `ipc-tests.rs` проверяют реальные Unix-сокеты без аудиоустройства; повторное чтение после EOF ограничено guard-ом. При обновлении pinned `rev` проверить пакет без `ipc-eof.patch` по `pkgs/onionbell/README.md`: удалить только этот фикс, когда все EOF-тесты проходят без него, тесты сохранить. `flake.lock` не обновляет этот pin; конфликт patch — повод для review, не доказательство upstream-исправления.
- Для живой проверки выхода через `pw-record` обязательно задавать `--properties '{ stream.capture.sink = true }'` вместе с `--target <sink-name>` и проверять PipeWire links от `monitor_FL/FR`: без этого WirePlumber может записывать микрофон вместо выхода. Ненулевой peak сам по себе не доказывает воспроизведение bell.
- HM-модуль предупреждает `ONIONBELL CLEANUP`, когда выбранный Hyprland получает зависимость `libcanberra` — признак native bell из PR #15502, включая backports. Проверка выполняется при evaluation/build/switch без сетевых запросов. Сначала применить NixOS update и перезайти в Hyprland, остановить onionbell и проверить `printf '\a'`; после успешной проверки удалить пакет, конфиг, службу и сам reminder из HM, затем применить HM.

### Window management policy

- На Lenovo пользователь разрешил штатный resize через `Super+Shift+ЛКМ` для floating и tiled; `Super+ЛКМ` сохраняется для перемещения. Нужен механизм сброса: `Super+Ctrl+T` возвращает текущее Dwindle-деление к 50/50 через `splitratio 1 exact`, не восстанавливает всё дерево раскладки или прежнюю геометрию floating. Это подготовка, не live-приёмка. Других keyboard resize bindings не добавлять; другие хосты, fullscreen и app maximize policy не менять.
- Основные window controls: `Super+T` (Dwindle split), `Super+F`/`Super+Shift+F` (floating/tiled focus), `Super(+Shift)+HJKL`, workspaces и переносы между ними. `Super+N` открывает отдельное Kitty nvim window. Laptop: horizontal three-finger touchpad swipe переключает workspace. `Super+W` открывает semantic workspace/window switcher.
- `F1` открывает read-only `hypr-controls` через Tofi; поддерживать его список в соответствии с фактическими bind-ами laptop/desktop.

### Minecraft server

- `home/modules/minecraft/server/default.nix` — пользовательский systemd модуль: Packwiz serve → update → Fabric, плюс backup path/service.
- `minecraft.server = null` по умолчанию: import generic-модуля сам по себе ничего не запускает.
- `home/apps/minecraft/default.nix` задаёт instance с путями `/home/samov/Projects/minecraft/`, памятью `20G`, FreesmLauncher, Packwiz и JDK.
- Desktop/laptop-old импортируют оба модуля в `flake.nix`; server и Lenovo laptop импортируют только generic-модуль, Lenovo leaf отдельно сохраняет клиентские приложения.
- Чтобы включить идентичный Minecraft stack на server, добавить `./home/apps/minecraft` в `samov-server.modules` в `flake.nix`.

### filemanager1-common

- `pkgs/filemanager1-common/` — месон-сборка D-Bus сервиса FileManager1.
- `home/linux/modules/filemanager1-common/` — HM-модуль с options: fileManager, wrapperScript, terminalCommand.
- По умолчанию: Yazi через Alacritty.

### xremap (laptop-old/Acer only)

Lenovo separately uses an isolated socket daemon in
`hosts/laptop/command-keys.nix` and a Hyprland context bridge plus native TUI
bindings in `home/linux/laptop/command-keys/`. Only the measured built-in keyboard
is granted to a dedicated service UID; samov gets IPC-group membership, not raw
input. Left Alt/Super only; no global terminal Ctrl-Z translation. The user
applied the changes and reports successful ordinary use, not independent agent
UI observation or full lifecycle/EN-RU/clipboard/latency coverage.
The user chose Kitty as primary, accepting
Alacritty's terminal-native C/V limitation, and deferred an OpenCode input C/X
plugin until a real failure; no such plugin or cli.json edit was made. Native
OpenCode paste is retained for attachments, not live-tested. Seven actual-action
fixtures, native headless Neovim undo/redo/select, Fish syntax/bind checks, Kitty's
native mapping parser, generated-script Bash syntax and fourteen selected merged
checks pass; not keyboard/UI/clipboard/latency acceptance. See that README for
limitations and recovery. Acer is unchanged.

- Модификаторы:物理 Super → Alt,物理 Alt → Super, Menu → Alt.
- GUI: Super+key → Ctrl+key (copy/paste/cut/undo/redo).
- Терминал: Super+C/V → Ctrl+Shift+C/V, остальной Ctrl не трогается.

### Fish personal environment

- `home/core-set/shell.nix` sources optional `$__fish_config_dir/local-env.fish`
  in new interactive Fish sessions across HM profiles. Default location is
  `~/.config/fish/local-env.fish`; custom XDG paths follow Fish itself.
  This is trusted, manually maintained Fish code (`set -gx NAME 'value'`, mode 600),
  NEVER HM-managed content. Do not create/overwrite it or read its secrets during
  ordinary audits. The old `~/.config/llm-secrets/env` is no longer loaded and is
  not automatically migrated/deleted. See `docs/laptop-audit/fish-local-env.md`.

### Yazi archives

- Shared `home/core-set/shell.nix` patches compress 0.6 to abort password-mode
  cancellation/empty input, reject formats without password support and isolate
  flags/argument tables per invocation. Existing API substitutions and bindings
  stay. Eight Lua/API-fixture and real tiny 7zz checks pass; actual Yazi UI,
  full HM builds and Darwin remain unverified. The user subsequently accepted the
  Acer archive workflow, not independent UI coverage or other-host acceptance.
  Passwords still use upstream argv.
  On upstream update, remove the password patch only after the same regressions
  pass without it; review API substitutions separately. See
  `docs/laptop-audit/archives.md` for application and acceptance.

### Neovim

- Global Go is not imported by any HM profile. `home/core-set/go.nix` is retained
  for explicit future opt-in; project devenv/direnv supplies the toolchain when
  needed, including for Go-based Mason tools. Python/Node prerequisites remain.
- Сейчас ставится только `neovim-unwrapped` из nixpkgs без конфигурации.
- Server хранит Neovim repo, Lazy/Mason и Tree-sitter parsers вручную вне Nix
  store. Home Manager намеренно не подключает `~/.config/nvim` через
  `xdg.configFile`; для VPS используется ручная ветка `server-build`.
- Git editor и алиасы vi/vim → nvim.

### Nix generations и GC

- Store paths удаляются только когда на них не ссылается ни один GC root. NixOS
  system profile, Home Manager profile и modern `nix profile` независимы, но
  могут удерживать одни и те же store paths.
- На NixOS единственный полный cleanup запускается `sudo systemctl start
nix-gc.service`; штатный `nix-gc.timer` вызывает этот же service. Не запускать
  отдельный user timer или `nix-collect-garbage` как регулярную альтернативу.
- `nix-gc-run` запускает этот же service и выводит очистку профилей и store в
  реальном времени. `systemctl start` намеренно не передаёт stdout service в
  вызвавший терминал.
- Общий `hosts/profiles/gc.nix` запускается перед `nix-gc.service`: `nix-gc-env`
  очищает system/legacy profiles, `samov-profile-gc` очищает XDG Home Manager и
  modern user Nix profile от имени `samov`, затем `nix-gc.service` очищает store.
- Home Manager generations сохраняются по host policy: server `+2` daily,
  laptop-old `+3` weekly, laptop `+10` weekly, desktop `+5` weekly. Это обеспечивает rollback именно
  конфигурации Home Manager.
- Короткий retention текущего laptop-old (Acer): три поколения NixOS и три HM,
  weekly GC — вынужденный компромисс из-за недостатка места на SSD, не общая
  рекомендация. После переименования в laptop-old эта причина сохраняется.
  Для Lenovo (`laptop`) согласованы 10 поколений NixOS и 10 HM, weekly GC через
  общий service. Запас места оценить после updates; не переносить агрессивную
  политику Acer автоматически.
- Modern `nix profile` сохраняет только current generation через `nix profile
wipe-history`: Nix не предоставляет API "keep N", а его history откатывает
  bootstrap CLI, не Home Manager configuration. Не применять `nix-env` к modern
  `nix profile`: эти форматы несовместимы.
- Текущий `~/.nix-profile` на Acer laptop-old содержит рабочий `home-manager`; не удалять
  сам current user profile. Проверка 2026-09: очистка 33 старых `nix profile`
  generations и последующий store GC освободили около 14 GiB, а повторный GC
  удалил 0 paths.
- `nix-collect-garbage` без flags удаляет только уже недостижимые store paths;
  он не удаляет profile generations. Сначала очищаются generations, затем store.
- `samov-mac` импортирует `home/modules/profile-gc` только как future interface.
  Когда Mac получит расписание, реализовать `launchd` agent: Home Manager prune,
  `nix profile wipe-history`, затем `nix-collect-garbage`. macOS не имеет
  NixOS `nix-gc.service` или system profile.

### Server services

- Никакого Docker: AWG3.1 использует NixOS `wg-quick`, AdGuard Home и Caddy — обычные systemd services.
- `settings.nix` содержит незасекреченные VPS-specific значения. `server-preflight` сначала показывает read-only inventory и открывает wizard только при валидных disk/IPv4 candidates; administrator key всегда вводится вручную полным OpenSSH public key. При отсутствии global IPv6 с default route wizard требует явное `y` для продолжения без IPv6; по умолчанию выходит без записи settings. После явного подтверждения он записывает локальный, некоммитящийся settings-файл. Private keys и профили живут вне Git в `/var/lib/amneziawg` и `/var/lib/naiveproxy`.
- `hosts/server/settings.nix` — только пример. Реальные settings живут вне Git в `~/.config/nix-config/server/settings.nix` и передаются через `--override-input server-settings "path:$HOME/.config/nix-config/server"` (подразумевает `--no-write-lock-file`). Никаких private keys/passwords: input попадает в Nix store. Default input явно отказывает для server/installer; остальные hosts и server HM независимы. Preflight/verifier используют `SERVER_SETTINGS_DIR` или XDG default; verifier также принимает `--server-settings DIR`. Не фиксировать локальный путь в `flake.lock`. Перед server deploy агент обязан сверить SSH target с disk, WAN interface, IPv4 endpoint и IPv6 VPN ULA; при несовпадении остановиться. Один input описывает один live VPS, не переключать его между серверами. Для nixos-anywhere использовать готовые `--store-paths`: этот CLI не принимает override-input. Полные команды — `SERVER_AI_INSTRUCTIONS.md`.
- `awg-add-client <name>` публикует structured AmneziaVPN `.vpn` и QR, а также native `.conf` и QR; `naive-add-client <name>` публикует Karing/sing-box JSON.
- `vpn-download` разрешает только `internal-sftp` по одному ключу в `/srv/vpn-download/files`; shell и forwarding запрещены.
- AdGuard DNS доступен только через `awg0` и localhost; UI — через SSH tunnel на `127.0.0.1:8008`.
- Caddy/NaiveProxy включается после заполнения domain и ACME email; Caddy собран с pinned `forwardproxy` plugin.

### AmneziaVPN clients

- `pkgs/installer-vpn` exposes Linux `nix run .#installer-vpn -- up|status|down /external/profile.conf`
  for an x86_64 live installer before full closure downloads. Shared pinned AWG 3.1
  Go backend lives in `pkgs/amneziawg-3.1/go.nix`; server tools are reused unchanged,
  with a separate userspace-only quick script. No GUI, kernel-module build, NixOS/HM
  activation or VPS administration is needed. Profiles stay outside Git/store;
  hooks/custom routing are rejected, raw upstream output is suppressed. Direct LAN
  SSH is checked when metadata is present; this is not a universal connectivity
  guarantee. Wrapper/actual-script fixtures and selected derivation checks do not
  establish a built helper or live VPN/DNS/SSH/teardown. Separately, the user built
  checkout `b5ccba9` on Lenovo live and accepted handshake, AdGuard DNS, IPv4 VPS
  egress, LAN SSH and return to ordinary routing/DNS/IPv4/HTTPS after down.
  This does not cover IPv6 leaks, all firewall state or the updated lock.
  See its README and Lenovo checklist. Leave builds and real tunnel operations to the user.
- `pkgs/amnezia-vpn/` вендорит Linux-клиент `5.0.1.5` с `amneziawg-go`
  `v3.1.20260814`, который upstream release использует для AWG 3.1.
- Локальный клиент `5.0.1.5` проверенно работает с deployed AWG3.1 server.
- Linux split fixes в `pkgs/amnezia-vpn`: пустой DNS не добавляется в
  AllowedIPs; `linux-routing.patch` + `linux-default-route.h` читают netlink
  dump без общего лимита 8 KiB и исправляют dangling `qPrintable` в маршрутах.
  `checkPhase` запускает socket fixtures и ASan/UBSan на реальном
  `buildAllowedIp`; ручная проверка обоих режимов описана в README пакета.
- Overlay подключён только к NixOS desktop/laptop-old/laptop в `flake.nix`; эти хосты
  используют `pkgs.amnezia-vpn`, а daemon PATH содержит `iptables`,
  `ip6tables` и `gawk`.
- Shared `linux-network-readiness.patch` and `linux-connection-state.h` prepare
  event-driven NM readiness/recovery on all three hosts, not just Lenovo. The pin,
  AWG backend, routing/DNS/address fixes and lock stay unchanged. Both patches apply
  to the exact source without fuzz; native Qt/local QtRO actual-method fixtures
  (mock protocols/DNS/routes), routing ASan/UBSan and selected declarations pass.
  The user applied the changes and accepted Lenovo boot autoconnect and quick
  Hibernate recovery. A subsequent reboot resolved the initial old-GUI/new-helper
  mismatch; matching new paths are checked. DNS/egress, split routing, cancellation,
  kill-switch/leaks, repeated cycles and other hosts remain separate acceptance.
  No boot sleeps, extra services or blanket
  VPN restart hooks. See the package README for limitations and acceptance.
  Its changed IPC requires matching GUI/helper and a full GUI exit/reopen after
  NixOS application; no HM change. Retain scenarios when reviewing upstream fixes.
- При обновлении `nixpkgs-unstable` NixOS warning появляется только если его
  официальный `amnezia-vpn` новее нерабочего upstream 5.0.3.0. Этот release
  завершает AWG3.1 handshake, но не назначает `amn0` VPN IPv4 из dual-stack
  `Address`, оставляя DNS недоступным. Перед удалением override проверить
  включение upstream PR #2840 (IPv4 assignment) и #3231 (endpoint routes),
  затем проверить backend AWG и service PATH; автоматически на upstream не
  переключаться.

### Disko + nixos-anywhere

- `disko` pinned as a flake input; shared layouts live in `hosts/disko/layouts.nix`.
- Remote VPS install uses verified `--store-paths` for nixos-anywhere from another machine in provider rescue mode; obtain both closures with the external settings override per `SERVER_AI_INSTRUCTIONS.md`. Keep both GC-root links via `--out-link` under `~/.local/state/nix-config/deploy/server/` until successful installation, not `--no-link` results that GC may remove.
- `root@<vps-ip>` is SSH syntax for the remote rescue host. A local laptop/desktop install needs no IP: boot a NixOS installer USB, run the reviewed locked Disko locally, then `nixos-install --flake .#laptop` after storage planning, disk re-identification and explicit destructive-stage consent.
- Before any destructive install, replace every `REPLACE_ME` after checking `lsblk`; future desktop must also confirm BIOS vs EFI with `efibootmgr -v`.
- Acer laptop-old retains `/swapfile` plus `resume_offset`; Lenovo laptop uses a swap partition with `resumeDevice = true`, so the two schemes never coexist on one host.

## Форматирование этого репозитория

Форматировать только изменённые файлы через CLI, не весь репозиторий и не моделью.
Эти правила принадлежат проекту; глобальной настройки formatter в OpenCode нет.
Neovim-конфигурация не меняется. Новые конфиги не означают массовый style rewrite.

| Файлы                                | Инструмент и источник правил                                                                                                                         | Команда из корня репозитория                                                         |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Nix                                  | nixfmt из flake.lock (текущий pin 1.5.0), defaults (100 columns, 2 spaces), как nixd → `nixfmt`                                                      | `nix fmt -- file.nix`                                                                |
| TS/JS/MJS, JSON/JSONC, CSS, Markdown | Prettier, `.prettierrc.json` + `.prettierignore`; defaults текущего Neovim Prettier 3.9.5                                                            | `prettier --write path/to/file`                                                      |
| Python                               | Ruff, `[tool.ruff]` / `[tool.ruff.format]` в `pyproject.toml`; defaults текущего Neovim Ruff 0.17.2 (88 columns, 4 spaces, Python 3.11, без preview) | `ruff format path/to/file.py`                                                        |
| Shell                                | Beautysh 6.4.3, `[tool.beautysh]` в `pyproject.toml`: 4 spaces, `paronly`, как в Conform                                                             | `beautysh path/to/file.sh`                                                           |
| Lua                                  | LuaLS / EmmyLuaCodeStyle, `.editorconfig`, 2 spaces как LSP options Neovim; не StyLua                                                                | Форматировать через LuaLS в редакторе; без соответствующего CLI сохранять оформление |

Использовать доступный CLI той же версии, что в редакторе; если его нет, сообщить,
не подменять другим formatter и не устанавливать без запроса. Версии Prettier/Ruff/
Beautysh здесь описывают проверенный снимок, не отдельную систему установки/pinning.
Одинаковый конфиг сам по себе не гарантирует byte-identical output разных версий.
`nix fmt` использует nixfmt из flake.lock; nixd уже вызывает установленный `nixfmt`
из того же nixpkgs через `home/core-set/nix-authoring.nix` (после применения профиля).
У nixfmt нет нативного файла конфигурации стиля; выдуманный `.nixfmt`/nixd config
не добавлять. Beautysh читает `pyproject.toml` только из cwd: запускать из корня.
На `hosts/server/preflight.sh` Beautysh 6.4.3 даёт существующую ошибку
`indent/outdent mismatch`; не менять скрипт ради форматтера и не скрывать ошибку.
Python lint fixes (`ruff check --fix`) не являются форматированием.

Для C/C++, Rust, raw `.conf`, patches, ключей и прочих типов без объявленного
formatter сохранять существующее оформление. Generated locks не форматировать.
Neovim раньше не выбирал Prettier без config/dependency; `.prettierrc.json` теперь
явно включает его для поддерживаемых типов в этом проекте, включая CSS/Markdown.

## Полезные команды

## Обновление flake и конфигураций

`nix-flake-update-verify` — декларативная команда из `home/core-set`.
Она обновляет ровно один root input и выполняет настоящие `nix build --no-link`
только для выбранного host. Большой update может потребовать дополнительное
место в `/nix/store`, сопоставимое с размером текущего closure; при массовом
пересборе ориентироваться на запас до двух размеров текущего closure.
Backup OpenCode-сессий для этой операции не нужен: update и build не меняют
установленный OpenCode или его storage.

На Acer обновить один input и проверить только laptop-old outputs:

```bash
nix-flake-update-verify --hosts laptop-old --input nixpkgs
```

- Inputs: `nixpkgs`, `nixpkgs-unstable`, `nixpkgs-kernel`, `home-manager`, `browser-previews`,
  `disko`, `freesm`, `nix-gc-env`, `xremap-flake`; `all` доступен только
  явно через `--input all`.
- Hosts: `laptop`, `laptop-old`, `desktop`, `server`, `server-installer`, `mac`; `--hosts
all` проверяет все hosts, поддерживаемые текущей платформой: Linux hosts на
  Linux и `mac` на macOS.
- Kernel-only Lenovo update: `nix-flake-update-verify --hosts laptop --input nixpkgs-kernel`
  after HM installs the updated helper. Before that, direct `nix flake update nixpkgs-kernel`
  works; a normal `nix flake update` includes it too. Updating only `nixpkgs-unstable`
  does not advance this independent pin. No automatically scheduled updates.
- Linux hosts `laptop`, `laptop-old`, `desktop` и `server` строят свои NixOS и Home Manager
  outputs; `server-installer` строит только NixOS ISO output; `mac` строит
  только свой Home Manager output на macOS.
- `desktop-next` намеренно не поддерживается: это непроверенный шаблон будущего
  оборудования. Старое имя `laptop-next` удалено; `laptop` — Lenovo, его install
  guard снят после review, но builds/install ещё не выполнены. Не запускать `--hosts all` ради миграции одного ноутбука.

После переноса одного и того же `flake.lock` на другую машину проверить её
host без изменения lock-файла:

```bash
nix-flake-update-verify --hosts desktop --no-update
nix-flake-update-verify --hosts server --no-update
```

Локальный server build не подключается к VPS. Сверка server settings с VPS
нужна перед deploy, не перед verification.
Для `server`, `server-installer` и Linux `--hosts all` verifier требует внешний
`settings.nix` до update/build. По умолчанию — `~/.config/nix-config/server`,
переопределение — `--server-settings DIR` или `SERVER_SETTINGS_DIR`.
Override применяется только к серверным NixOS outputs и не записывается в lock.

На Mac:

```bash
nix-flake-update-verify --hosts mac --no-update
```

Для обновления input на Mac заменить `--no-update` на `--input <name>`.

При любой ошибке команда немедленно завершается и оставляет `flake.lock` для
обычного Git review или rollback. Nix печатает исходную ошибку, после чего
скрипт выводит machine-readable summary, например:

```text
FAILED: phase=build; input=nixpkgs; host=laptop; output=home-manager; exit=1
```

Команда не делает switch, Git commit или автоматический rollback.

## Применение конфигурации

- NEVER run `nixos-rebuild switch` or `home-manager switch`. The user applies
  NixOS and Home Manager configurations after personal review.
- Leave Nix closure verification builds to the user by default. This includes
  `nix build`, `nix flake check`, rebuild/build commands, and scripts that invoke
  builds, including `nix-flake-update-verify`. Run a specific build only when the
  user explicitly requests it; general review or commit approval is not enough.
- Lightweight evaluation without realizing derivations is allowed. Obtain
  approval before expensive evaluation.
- Provide the smallest verification command for the affected host/output.
  Do not run the full verification matrix automatically.

### Область применения изменений

В итогах всегда явно указывать, как применять каждую группу изменений:

- `hosts/<host>/` и NixOS-модули: пользователь запускает `nixos-rebuild` с
  рабочей станции; для VPS — через `--target-host` SSH alias.
- `home/` и Home Manager-модули: пользователь запускает Home Manager для
  нужного профиля; server Home Manager активируется на VPS по SSH.
- Документация и ручное состояние (Neovim, Lazy, Mason, созданные VPN
  профили): Nix activation не требуется; явно привести ручную команду, если
  она нужна.

```bash
# NixOS
sudo nixos-rebuild switch --flake .#laptop-old
sudo nixos-rebuild switch --flake .#desktop
sudo nixos-rebuild switch --flake .#server --override-input server-settings "path:$HOME/.config/nix-config/server"

# Fresh remote VPS: run preflight first. Try only the kexec bootstrap, then
# use the provider ISO fallback documented in SERVER_AI_INSTRUCTIONS.md.
# First obtain verified $disko_script/$nixos_system per SERVER_AI_INSTRUCTIONS.md.
nix run github:nix-community/nixos-anywhere -- --store-paths "$disko_script" "$nixos_system" --phases kexec root@<vps-ip>
nix build --override-input server-settings "path:$HOME/.config/nix-config/server" .#nixosConfigurations.server-installer.config.system.build.isoImage
# After a NixOS installer is running:
nix run github:nix-community/nixos-anywhere -- --store-paths "$disko_script" "$nixos_system" --phases disko,install,reboot root@<vps-ip>

# Home Manager
home-manager switch --flake .#samov-laptop-old
home-manager switch --flake .#samov-desktop
home-manager switch --flake .#samov-server

# Проверка
nix flake check --override-input server-settings "path:$HOME/.config/nix-config/server"
nix eval .#nixosConfigurations.laptop-old.config.system.build.toplevel --no-build 2>&1 | head
```

## Текущее состояние хостов

- **laptop-old**: текущий Acer с Intel/NVIDIA, ext4, GRUB EFI, Hibernate/zram. Пользователь успешно применил NixOS/HM под новыми именами и подтвердил работу; оставшееся transient hostname обновлено отдельно. Повторная загрузка/resume этим не проверены. Снимок stable inputs требует актуализации; короткий GC-retention обусловлен нехваткой места на SSD Acer.
- **laptop**: Lenovo ThinkBook 16 G8+ IPD (21VJ), Core Ultra 7 356H + RTX 5060 Mobile. Пользователь установил NixOS и standalone HM, применил boot fixes и подтвердил cleanup. После reboot Amnezia подключается автоматически, после Hibernate быстро восстанавливается; matching GUI/helper проверены. Один post-fix shutdown PipeWire завершился без прежнего SIGSEGV. WirePlumber Lua/UPower и аппаратные ошибки остаются; это не полная приёмка графики, RTD3, Bluetooth, DNS/split routing/kill-switch или battery policy. Актуальное состояние — `hosts/laptop/boot-errors.md`; install-stage описания выше исторические, не разрешение повторять установку.
- **desktop**: старше laptop. AMD + NVIDIA, два монитора (DVI 1680x1050 + HDMI 3840x2160@3x). Нет Bluetooth/uinput/xremap/hibernate.
- **server**: модульный VPS stack без Docker, Disko и generic virtio hardware modules. Preflight пишет внешний settings input по данным rescue environment; в Git остаётся только пример.
- **mac**: только standalone HM (users + core-set). Без nix-darwin, без GUI, без проверки совместимости Linux-пакетов.
