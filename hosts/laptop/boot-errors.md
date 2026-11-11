# Lenovo: installed boot errors

Observed on 11 November 2026: ThinkBook 16 G8+ IPD (21VJ), BIOS TRCN21WW,
Linux 7.3.1, stable base userspace. Initial logs were under
`/tmp/opencode/laptop-boot-90d02df9/` and may not survive reboot; VPN application
contents are not retained here. Earlier inspected boot:
`b3e33a50-ea4a-4f23-898f-7e7439176b1b`. Full private export/JSON/text snapshots
of this boot and the previous boot's shutdown are under
`/tmp/opencode/laptop-power-cycle-b3e33a50-1794384052168705/`, outside Git.
`manifest.json` records boot IDs, capture cutoff, record counts and SHA-256 sums.
These unfiltered files may contain sensitive data; do not publish them directly.

## Latest application, cleanup and acceptance status

On 11 November the user reported applying all prepared changes, then confirmed
manual removal of the installation leftovers listed during review:
`/etc/nixos/`, `~/vpn-fix/`, `~/vpn-fix.tar.gz` and the
`/nix/var/nix/gcroots/installer-vpn-bootstrap` symlink. This is user-reported
cleanup, not an independent post-deletion inventory. Before removal, `/etc/nixos`
was a clean independent checkout of the same commit as `~/nix-config`; all 336
archive files matched `~/vpn-fix`, whose only extra file/link was `result`.
The conditional `/root/lenovo.conf` item was inaccessible to the agent; its removal
and profile-retention decision are not independently established. The working
checkout, current Nix/HM profiles and Amnezia profiles/keys are not cleanup targets.
Cleanup requires no NixOS or Home Manager activation.

During the NixOS switch at `13:38:13 +03:00`, PipeWire/Pulse restarted and Waybar
0.15.0 aborted with recursive `AudioBackend::connectContext()`/libpulse frames.
This matches upstream [#5141](https://github.com/Alexays/Waybar/issues/5141),
not the separate PipeWire shutdown SIGSEGV. The compact private coredump export is
`/tmp/opencode/waybar-coredump-1295.txt`. Both pinned channels select the same
unpatched Waybar source. The user elected not to prepare a Waybar reconnect fix
for this rare scenario; no audio module removal, restart hook or patch was added.
Manual recovery is `uwsm app -- waybar`; an already foreground-launched Fish job
can be suspended with Ctrl+Z, resumed with `bg`, then detached with `disown`.

A read-only post-switch check found a mixed Amnezia runtime: GUI PID 1317 still
used `/nix/store/awchlkc485m2pshahlg4xnndffp7nmqa-amnezia-vpn-5.0.1.5`, whereas
the active helper and installed GUI use
`/nix/store/mkwayra2z03ryfc1cgf83npj6l26bg71-amnezia-vpn-5.0.1.5`.
The matching version label does not imply matching IPC. The user subsequently
rebooted; the fresh boot check below confirms that this mismatch is resolved.
No live VPN operation was run by the agent.

### Fresh reboot and Hibernate acceptance

The user confirms that Amnezia connected immediately after reboot without manual
Connect, and recovered quickly through a reconnect after Hibernate. A reconnect
when the physical network returns is expected; a permanently unchanged tunnel is
not the acceptance criterion. This accepts the reported Lenovo startup/resume
scenarios, not every network timing, cancellation, split-routing mode, DNS/egress,
kill-switch/leak policy or another host.

The latest inspected boot is `bd1645b2-9f74-4c76-8dd4-ef0c00f58526`.
GUI PID 1319 and the active helper both use the new `mkwayra2...` package above.
Systemd records Hibernate at `13:57:15.407859 +03:00` and return at
`13:58:17.844072 +03:00`. There are no currently failed system/user units.
These are read-only runtime checks plus user acceptance, not an agent-run VPN
connectivity or leak test. They do not independently establish the exact timing
of VPN recovery or the absence of every pre-sleep reconnect.

Private, selected journal exports are under
`/tmp/opencode/laptop-acceptance-20261111-140155/`, with a SHA-256 manifest:
previous boot's three audio units, current audio units, current warning/error
kernel records and current Hibernate unit. This is not a full journal export;
the manifest records capture time, coverage and boot IDs. Raw records stay outside Git.

The preceding shutdown now provides a successful PipeWire fix observation:
the two X11 I/O callbacks still logged at `13:55:53.212539` / `.213176 +03:00`,
but Pulse stopped at `.569783` and PipeWire at `.636889`, without `SEGV` or
`core-dump` in those unit records. This is one observed post-fix shutdown, not
proof about unrecorded late shutdown or every audio teardown. The new boot still
has four WirePlumber `source_plugin` Lua errors and UPower `NameHasNoOwner`;
they are not fixed by the PipeWire or Amnezia changes.

The user also reports Bluetooth and other messages visible around both entry and
exit. The same private export now includes all 172 kernel records in the selected
`13:57:10`–`13:58:30 +03:00` window (`current-hibernate-kernel.jsonl`):

- SPD5118 logs `Failed to write b = 0: -6`, a failing `spd5118_resume` callback and
  `failed to restore async: error -6` at `13:58:17.063...`.
- The panel logs `Skipping unprepare of already unprepared panel` at `.064800`.
- Intel Bluetooth logs `BT reprobe failed for BDF:0000:00:14.7` at `.065502`.
  Four `Received gp1 mailbox interrupt` errors follow at `13:58:17.885094`,
  `.885153`, `.885159` and `13:58:18.329145`. Firmware/DDC initialization then
  completes, `Fseq status: Success (0x00)` is logged at `.330161`, and MGMT
  registers at `.368132`. This is controller progress, not device-level acceptance
  or proof that the reprobe failure is harmless. These kernel/firmware messages
  are distinct from the BlueZ userspace `load_defaults` error already fixed.
- ISH reloads `intel/ish/ish_ptl.bin` and logs `cmd 2 failed 10` three times at
  `13:58:17.066668` / `.067057` / `.067572`.

Kernel messages buffered around console suspension are journaled together after
resume, including preparation records. Journal receipt times alone cannot assign
every tty-visible message to the user's entry-versus-exit observation. No extra
Hibernate cycle, driver reload, firmware substitution or log suppression was run.
Successful session/VPN restoration does not close any of these hardware findings.

### Review and local commit checks

The batch preserves the lock and package pins except the explicitly selected
Lenovo daemon packages; the Amnezia correction is shared by its three Linux
hosts. No Waybar reconnect patch or battery policy was added. Earlier recorded
source/Qt IPC/ASan/UBSan/declaration checks are reused rather than rerunning
builds. The user performed the package/system application and live scenarios.

Before the local commit, Python syntax, changed Nix formatting with the current
flake-pinned nixfmt 1.5.0, local Markdown links and non-patch whitespace pass.
The installed HM environment file also passes both native systemd-generator
tests, including the old-assignment rejection control. A whole-diff whitespace
check reports unified-patch context lines (including exact upstream PipeWire
tabs/blank context); those patches are deliberately not reformatted. Prettier
and Ruff are unavailable, so Markdown/Python formatting was not rerun and no
fallback formatter was substituted. No agent-run build, activation, reboot,
Hibernate, VPN operation or remote Git operation is part of this commit review.

## Applied fixes observed after reboot

- **Two mDNS responders:** [the workstation module](../profiles/mdns.nix) now
  disables only resolved's global `MulticastDNS`. Ordinary/VPN DNS stays with
  resolved, Avahi/NSS discovery stays enabled. See [mDNS checks](../../docs/laptop-audit/mdns.md).
- **Invalid environment.d assignment:** the [Qt module](../../home/linux/modules/qt-theme/default.nix)
  uses native `${QT_STYLE_OVERRIDE:+}` expansion, always yielding empty even with
  an inherited fixed style. The installed generator rejects literal empty values,
  including quoted ones. No application is forced onto a new Qt style.
- **BlueZ 5.86 false error:** with no changed default parameters, `load_defaults()`
  reached an error branch without a management request. The originally applied
  Lenovo-only override added the byte-identical upstream
  [b9a72fef5cd5 patch](https://github.com/bluez/bluez/commit/b9a72fef5cd51f849ce01c9f2775d129a687d855).
  It frees the empty list and returns; real request failures remain errors.
  That first fix preserved the stable version, upstream patches, adapter settings
  and other hosts. The current [selection](bluetooth.nix) supersedes the backport.

Four-host mDNS and five-profile Qt selected declarations pass without builds.
The evaluated Lenovo HM file passes the installed native environment generator
with isolated HOME/XDG and inherited overrides; system-wide defaults are still
read. This does not reload the live manager or test Qt rendering.

The user built/applied NixOS and HM and rebooted. Both the previous inspected
boot (`114caa34-3ed4-4c5b-82a6-3eccdc293df1`) and the latest boot have no failed
system/user services or Hyprland configuration errors. Global/link mDNS is `no`,
Avahi/resolved/Bluetooth are active, the corrected Qt assignment is installed,
and the three targeted startup messages do not recur. This is not acceptance of
LAN discovery, ordinary/VPN DNS/HTTPS, real Bluetooth devices or Qt rendering.

The applied BlueZ 5.86 backport was the original fix; the package selection below
now replaces it. The local patch is removed.

## Applied package updates: pinned unstable, Lenovo only

The user approved using already-fixed packages instead of maintaining backports:

- `hardware.bluetooth.package = pkgsUnstable.bluez` selects **5.87**. Its actual
  tagged `load_defaults()` passes all seven fixed-behavior cases without a local
  patch: empty defaults, skipped configuration, successful requests and real
  failures/cleanup. Management calls are stubbed, not a radio/integration test.
- The Lenovo overlay selects **xdg-desktop-portal 1.22.1**. Stable 1.20.4 passes a
  real pidfd to a function expecting a `/proc/<pid>` directory fd; `fstatat`
  therefore fails with `ENOTDIR`. The new release includes upstream
  [PR #1713](https://github.com/flatpak/xdg-desktop-portal/pull/1713), using
  `PIDFD_GET_PID_NAMESPACE`. The actual extracted functions reproduce the old
  error and pass the new native namespace, fd-cleanup and descriptor-error cases.
  Only GLib diagnostics are stubbed; Linux descriptor/ioctl calls are real.
- GTK/Hyprland backend derivations and native routing remain unchanged. GTK's
  build-time dependency is explicitly kept stable; simply overriding the core
  portal would otherwise change that derivation. Mesa/GLib remain stable, and
  there are no global library-path overrides. These daemons communicate with the
  stable desktop over IPC rather than injecting unstable libraries into it.
- Flake inputs/lock, kernel/firmware, WirePlumber, UPower and other hosts are
  unchanged. No local portal patches were added. The earlier BlueZ patch is no
  longer needed; keep the behavior harness on future package updates.

Selected package/routing/scope declarations and source-function tests pass.
The user applied updated NixOS and rebooted. The latest installed service
ExecStarts confirm BlueZ 5.87 and core portal 1.22.1. The captured startup has
zero pidns/old BlueZ/mDNS/environment errors, no currently failed system/user
services and no current-boot coredump records. PipeWire, Pulse, WirePlumber and
onionbell have SCHED_RR data-loop threads with priority 20; onionbell previously
had no RT thread. This is native runtime evidence, not a traced portal method
call or acceptance of Bluetooth devices, file chooser and screen sharing.
No package/NixOS build was run by the agent.

```fish
nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/test-bluetooth.nix
nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/test-desktop-services.nix
python3 -B hosts/laptop/test_bluez.py /external/bluez-5.87/src/adapter.c
python3 -B hosts/laptop/test_portal_pidns.py /external/xdg-desktop-portal-1.22.1/src --baseline /external/xdg-desktop-portal-1.20.4/src
```

Use the selected packages' actual source on update; review function changes rather
than weakening the invariants. Source-function coverage is not a full portal
service, D-Bus Realtime request, scheduler, Bluetooth or desktop test.

## PipeWire shutdown fix: user-applied, one clean shutdown observed

The Lenovo-only [audio module](audio.nix) selects the same stable PipeWire 1.6.6
source with upstream [c2fec6c037a1](https://github.com/PipeWire/pipewire/commit/c2fec6c037a191d535319f99d7720232d03f315b).
The X11 I/O exit handler can run again before deferred module destruction. Its
first invocation clears `impl->source`; the original second invocation attempts
to destroy that NULL source. The upstream fix makes this cleanup idempotent.
The observed two X11 errors followed by SIGSEGV strongly match this failure path,
but there is no shutdown stack trace proving it is the only cause.

Both pinned stable 1.6.6 and unstable 1.6.9 have byte-identical affected module
sources, and neither package's patch list includes this fix. An audio-stack
upgrade therefore does not substitute for this backport. The patch is byte-for-byte
upstream (SHA-256 `7475a4b9f28747b555332491148540d19028f25cd3ec34c388ee290a0d8afeb7`).
It applies to both sources without fuzz or offsets. No upstream log messages,
X11 bell functionality, RT scheduling or audio features are disabled.

`test_pipewire_x11.py` extracts the actual callback and uses explicit dependency
stubs. The baseline detects invalid NULL-source destruction; patched code passes
single, repeated, already-detached and independent-module cases. This is callback
contract coverage, **not a native SIGSEGV reproducer** or actual X11 teardown,
bell/audio-output, full package or installed-service test. The release module
source SHA-256 is `0db366736588206159976e37490c9489d875eaeedfd31c9fa938a1d73f4916fa`.

Selected Nix assertions confirm the stable source/patches, ALSA (including 32-bit),
Pulse/JACK/RTKit, unchanged global client package/WirePlumber and other hosts.
Only `services.pipewire.package` changes, not a global overlay. No working audio
service was restarted by the agent. The user subsequently reported applying the
changes; post-switch PipeWire/Pulse services are active. The later shutdown above
exercised repeated X11 callbacks without reproducing the SIGSEGV. Preserve the
coverage limit: this is one cycle, not universal audio/teardown acceptance.

```fish
nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/test-audio.nix
python3 -B hosts/laptop/test_pipewire_x11.py /external/pipewire-1.6.6/src/modules/module-x11-bell.c
```

On update, exercise the new source with `--check-upstream`. Remove the local patch
and override only when fixed behavior passes without them, update the declaration
test and retain the callback harness. A patch conflict is not proof of a fix.

### Apply and accept this block

1. For a future application/update, review the audio module, patch and tests.
   New imported files must be included in the Git flake before building.
2. On Lenovo, run `sudo nixos-rebuild switch --flake .#laptop`. No Home Manager
   change is needed. This user-run command builds and may restart audio services;
   finish playback/recording first.
3. Confirm ordinary audio and X11/Wayland bell still work, then reboot when ready.
   Capture the previous shutdown and new startup privately, as above. Require no
   PipeWire `status=11/SEGV`/`core-dump` result; an X11 disconnect warning alone
   can still occur when the X server exits and is deliberately not suppressed.
4. If SIGSEGV remains, obtain an isolated native teardown reproducer/stack before
   attributing it to another component. WirePlumber startup errors are separate
   and are not expected to disappear with this patch.

## Manual Hibernate: session restored, peripheral/VPN issues remain

On 11 November the user ran `systemctl hibernate` and observed the previous
session return after power-on. Preflight found 48 GiB free swap for about 32 GiB
RAM, matching kernel resume device `259:2`, offset zero and `CanHibernate=yes`.
Native NVIDIA suspend notifiers were enabled. This is one successful user-observed
cycle, not repeated-cycle or critical-battery acceptance.

The private journal snapshot is
`/tmp/opencode/laptop-hibernate-1794389275017404/hibernate-resume.jsonl`;
its manifest SHA-256 was rechecked. It contains 1,872 records, including sensitive
VPN data, and must not be published. Times below are MSK (+03:00), same boot ID
as above. Hibernate was requested at `12:22:48.082998`, kernel entry was
`.423407`, and systemd reported successful return at `12:23:39.768264`.
The journal shows S4 preparation/wake and image-memory allocation, but does not
independently record every image-write/read stage. No failed system/user units
were found after recovery.

- **Amnezia 5.0.1.5:** NetworkManager state `10` reached the watcher at
  `12:22:48.087959`; reconnect began at `.089210`, before process freezing.
  After resume, default-route discovery failed at `12:23:41.154175` and sending
  a handshake returned `network is unreachable`. State `70` arrived at
  `12:23:44.896542`, but the client rejected that reconnect signal because it
  was already `Reconnecting`. Manual recovery eventually completed a handshake
  at `12:26:16.563339`.
  Upstream `client/platforms/linux/linuxnetworkwatcherworker.cpp` emits `wakeup()`
  on **ASLEEP**, not on waking; `service/server/localserver.cpp` forwards it over
  IPC, and `client/vpnConnection.cpp` connects it to `reconnectToVpn()`. That
  function stops/starts immediately and accepts triggers only from `Connected`.
  This source/log match identifies a pre-sleep reconnect defect; it does not prove
  every intermittent connection failure has the same cause. Both affected source
  files are byte-identical in 5.0.3.0, so that release is not a fix for this path.
  In the latest saved ordinary startup, state `70` arrived at `10:57:37.142044`, a trigger
  was ignored while `Connecting` at `10:57:38.293290`, but handshake completed at
  `10:57:38.558293`. That startup did **not** reproduce a persistent connection
  failure. On further inspection, the **previous ordinary startup** did capture
  the reported startup problem: default-route discovery failed at
  `10:30:54.624087` / `.624326`, followed by `network is unreachable` at `.626184`.
  NetworkManager state `70` arrived at `10:30:55.890198`, but the client ignored
  its trigger at `.890589` because it was still `Connecting`. It reported
  `Disconnected` at `10:31:26.750425`; a handshake finally completed at
  `10:31:33.340953`. The log does not establish whether user intervention caused
  that later recovery. This supports a network-readiness race at cold startup,
  not merely an S4-specific problem or proof of every intermittent VPN failure.
  The user confirms the other reported intermittent failures occur after laptop
  boot, not when manually pressing Connect. The installed desktop autostart runs
  `AmneziaVPN --autostart` after graphical-session targets, without a network
  readiness dependency. Its system helper is ordered after `network.target`,
  which does not guarantee an address/default route; wait-online is disabled.
  These orderings explain why early attempts are possible, not by themselves a
  reason to delay all boot networking. A client-side correction should handle
  actual underlying network/route readiness and pending connection intent, not
  a fixed sleep or unconditional resume restart. The user approved a shared
  package fix rather than a Lenovo condition: `pkgs/amnezia-vpn` now prepares
  `linux-network-readiness.patch` plus an explicit connection-intent helper.
  It gates startup on NM SITE/GLOBAL, retains recovery intent across network
  loss, accepts recovery from Connecting/Reconnecting, cancels on Disconnect and
  avoids restart on SITE/GLOBAL-only changes. Its initial state comes over the
  existing local IPC; wired-only hosts do not depend on Wi-Fi enumeration.
  Actual patched methods pass real Qt event/local QtRO tests with mocked protocol,
  DNS and route operations. Both package patches apply to the exact pinned source
  with zero fuzz; existing routing ASan/UBSan fixtures and selected three-host
  declarations pass. These are not full package, installed UI, real NM/VPN,
  kill-switch/leak or Hibernate integration tests. See the
  [shared package README](../../pkgs/amnezia-vpn/README.md) for limits and the
   user-run NixOS-only apply/acceptance plan. The user subsequently reported
   applying the changes. The initial post-switch check found the old GUI with the
   new helper; the subsequent reboot resolved it, and the user accepted startup
   autoconnect and Hibernate recovery as recorded above. Other acceptance remains
   scoped separately. The agent
   ran no build, activation or live tunnel operation; no VPN restart hook or fixed
   delay was added. GUI/helper must be upgraded together because the local IPC
   schema changes.
- **Intel Bluetooth:** the user confirms seeing `Received gp1 mailbox interrupt`
  on tty. Linux 7.3.1's `btintel_pcie_msix_gp1_handler()` logs it at error level and
  dumps debug registers. Four occurrences followed the resume reset/reprobe
  warning; firmware loading then completed, DDC parameters were applied and
  `Fseq status: Success (0x00)` appeared at `12:23:40.323138`, followed by MGMT
  registration. This confirms controller initialization progressed, not successful
  device reconnection. `BT reprobe failed` does not include its return code, so
  its cause remains open. BlueZ `Powered=true` is not device-level acceptance.
  No interrupt-log suppression, module reload or firmware substitution was added.
- **SPD5118:** separate resume callback returned `-6` (ENXIO). A later temperature
  read succeeded at 41.25°C; that does not erase the resume failure. Panel
  double-unprepare and existing ISH failures also remain open.

The user prefers UPower with Hibernate over HybridSleep. Automatic battery policy
is still disabled pending follow-up; no new activation is needed for this audit.

## Remaining findings and historical failures

- **PipeWire shutdown SIGSEGV, not reproduced after the fix:** previous boot `dafc44b5...` requested reboot at
  `10:57:07.932226 +03:00`. PipeWire 1.6.6 logged fatal X11 I/O errors at
  `10:57:08.053708` / `.053960`, followed by user systemd reporting
  `pipewire.service: Main process exited, code=dumped, status=11/SEGV` at
  `10:57:08.146102`, and result `core-dump` at `.147213`. The coredump helper
  reported `Failed to send coredump datagram: Connection reset by peer` at
  `.048890`; no stored coredump was found. Journal ordering alone does not prove
  which path caused the crash. Current-boot service health does not erase this
  shutdown failure; startup WirePlumber Lua errors are a separate issue. The
   applied backport above addresses the matching upstream bug; the latest
   captured shutdown exercised the repeated callbacks and stopped normally.
- **Other shutdown messages:** Intel xe reported selective-fetch calculation
  failure; sound/rfkill activation requests were rejected because shutdown jobs
  already existed. The kernel logged `watchdog0: watchdog did not stop!` at
  `10:57:08.731263`, between systemd's watchdog setup and systemd-shutdown's
  continued use of the same watchdog. `Finished System Reboot` was at
  `.688728`, `Journal stopped` at `.756112`; no stop timeout was found in the
  captured shutdown interval. The first next-boot entry is `10:57:21.193041`.
  The journal ends when journald stops: later physical power/reset events are
  not recorded here. Do not call the entire shutdown error-free or disable the
  watchdog merely for this message.

- **ACPI `AE_ALREADY_EXISTS`:** duplicate firmware namespace objects (`BG*`,
  `PTMA`, `PTMS`, `PTIA`); duplicate method definitions are skipped. No verified
  BIOS fix for this exact model has been established. Do not disable ACPI,
  override `_OSI` or replace DSDT to silence it. Sleep/hibernate/thermal behavior
  still needs acceptance before classifying the impact.
- **Intel display WARN:** `Port A asks to use VBT vswing/preemph tables`.
  The driver initializes and drives the internal panel. Upstream added VBT #57
  support and removed the warning in [this series](https://ratatoskr.run/intel-gfx/2026/07/17207361/t),
  ending with [4bda5543b3c6](https://github.com/torvalds/linux/commit/4bda5543b3c6697ca435e89aeea655eea9087f96).
  v7.3 lacks that support. Removing only the warning is not the fix; no kernel
  update/backport has been selected or built.
- **Intel ISH `cmd 2 failed 10`:** generic `ish_ptl.bin` is attempted; ISHTP has
  no clients and IIO devices are absent. No OEM PTL name was found in the
  installed `intel/ish` firmware directory.
  [Similar failures](https://bbs.archlinux.org/viewtopic.php?id=312550) need an
  OEM-signed image, but none is verified for this ThinkBook. Do not substitute
  ThinkPad/other-vendor blobs. Vendor/family/product/SKU DMI CRCs for firmware
  naming are `53c4ffad` / `1ed8bf4e` / `242732cd` / `2ed809bd`.
- **Lenovo WMI:** gamezone profile probe fails and fan tuning is unsupported,
  but native `ideapad-laptop` and `SoC Power Slider` expose all three profiles;
  PPD lists them. Do not force an experimental driver for this message.
- **WirePlumber Lua startup errors:** `source_plugin` is nil in early linking
  hooks (four errors at initial startup). WirePlumber is active with zero
  restarts, speaker/default microphone nodes exist and onionbell is linked to
  speakers; the user confirms output. Late registration of the event-source
  plugin is a source-supported hypothesis, not a proven startup trace. A bounded
  private PipeWire/WirePlumber policy-profile probe with a real pre-existing
  `pw-cat` stream did not reproduce it. It used a dummy sink, no hardware monitors
  and no live buses; this does not cover installed full-profile timing. Do not
  add nil guards, delays or an audio upgrade without a reproducer. Microphone
  function and Bluetooth routing remain unverified. The repeated bounded probe
  explicitly confirmed both sink/stream nodes before manager startup and two
  real PipeWire links afterwards; zero `source_plugin` errors. Debug tracing
  exercised `select-target` hooks, but not hardware monitors/full-profile timing.
  The affected lookup and component-loader/plugin-registration code remain
  unchanged in pinned unstable 0.5.19; no version-only upgrade was selected.
- **UPower `NameHasNoOwner`:** not merely an early boot race: UPower is disabled
  and absent on the system bus. PipeWire's BlueZ plugin asks for the host battery
  percentage with auto-start disabled. PPD's `org.freedesktop.UPower.PowerProfiles`
  is a different service. Do not enable UPower only to silence the message:
  NixOS also defaults its critical-battery action to `HybridSleep`, which needs a
  separate power-policy decision. No service or battery policy was changed.
- **D-Bus duplicates:** all 12 system and nine explicit session service-directory
  duplicate groups have byte-identical contents (system-path and package paths).
  Mako's two user locations resolve to the same file. FileManager1's intentional
  HM descriptor adds `SystemdService` but runs the same binary. No conflicting
  alternate implementation was found in those groups; do not remove service
  packages or HM descriptors just to remove their diagnostic messages.
- **HPET:** the kernel deliberately disables HPET because of its PC10 limitation;
  the selected clocksource is `tsc`. No timer/kernel-parameter workaround is needed
  on this evidence.
- **NVIDIA:** `/dev/nvidiactl`, `/dev/nvidia0` and `/dev/nvidia-uvm` exist with the
  expected device-node type; duplicate creation is plausible for the udev mknod
  failure, not independently proven. The active panel is Intel `eDP-2`; NVIDIA's
  EDID warnings are not evidence that its EDID failed. External display/offload
  acceptance remains open; do not force NVIDIA or change PRIME for these logs.
- **Remaining userspace messages:** Qt host-portal app-ID registration (see
  [portal audit](../../docs/laptop-audit/portals.md)), udiskie's one GTK scale
  assertion and NetworkManager's P2P forwarding warning remain separately open.
  They are not evidence that all portal, mounting or network operations fail.
  No journal priority filtering or global log suppression was added.
  NetworkManager's warning names a `wifi-p2p` control device with an empty IP
  interface and no matching netdev. Its sysctl setter returns FALSE without
  setting errno when no IP interface exists; the caller then formats errno as
  `Success`. This matches the diagnostic, not evidence of failed forwarding on
  the real Wi-Fi/VPN interfaces. Those functions remain unchanged in pinned
  unstable 1.58.1; P2P/forwarding were not disabled. Qt's host-registration code
  also remains unchanged in pinned unstable Qt 6.12.0 versus stable 6.11.2. No
  broad Qt/network upgrade was made on the assumption that a version fixes it.

## Next error-work order

1. Investigate the freshly repeated Intel Bluetooth reprobe/mailbox errors around
   Hibernate first, using the saved timeline and actual device acceptance; review
   SPD5118/panel/ISH as separate findings, not consequences of the VPN fix.
2. Investigate the freshly reproduced WirePlumber startup Lua errors with an
   installed full-profile trace/reproducer; the earlier dummy-sink probe did not
   reproduce them. Preserve working audio and do not add speculative guards.
3. Decide UPower's complete critical-battery policy, using the user's preference
   for Hibernate rather than HybridSleep. Successful manual Hibernate is useful
   evidence, not authorization to enable automatic battery actions.
4. Keep ACPI/ISH/VBT/WMI and the separate Qt/udiskie diagnostics visible; follow
   verified upstream fixes rather than suppressing logs or disabling features.
5. Waybar's rare Pulse reconnect crash remains deliberately deferred. Brightness,
   scale, lid and fingerprint changes still follow error work; sudo stays unchanged.

## Apply and accept on Lenovo

1. Review changes. For the new package selections, only NixOS needs application:
   `sudo nixos-rebuild switch --flake .#laptop --no-update-lock-file`.
   The earlier Qt/mDNS fixes are already applied; no new HM update is required here.
2. After success, run `sudo reboot`; NixOS deliberately sets
   `bluetooth.service.restartIfChanged = false` to avoid disconnecting input
   devices during activation, so switching alone leaves the previous daemon.
3. In the new session, expect global mDNS `no`, active Avahi,
   working ordinary/VPN DNS/HTTPS and no repeated mDNS/environment/BlueZ errors.
   Confirm the new BlueZ/portal versions are running, no repeated Realtime pidns
   errors appear and a real Bluetooth device still works. Also open/cancel an
   ordinary file chooser; screen sharing is a separate opt-in acceptance scenario.
   The user has applied/rebooted; versions and startup error absence are observed.
   Real Bluetooth and portal-UI acceptance remain pending. This audit-only update
   requires no further activation or service restart.
4. Continue open firmware/kernel/audio investigations separately. Brightness,
   scaling, lid behavior and fingerprint login follow error work; sudo is unchanged.
   The user confirms keyboard backlight switching already works via Fn+Space;
   no extra keyboard-backlight binding is needed.
