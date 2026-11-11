# Lenovo Intel PCIe Bluetooth: PM backports

Prepared on 11 November 2026; **built and applied by the user; Hibernate/device acceptance pending**.
This is separate from the already-applied BlueZ 5.87 userspace fix.
The user stopped the earlier switch plan after noticing the kernel version.
The target now selects released **7.3.4** via the separate kernel-only input;
the installed/booted system now runs 7.3.4. See the
[kernel update audit](../../docs/laptop-audit/graphics.md#1111-released-stable-kernel-input).

## Scope and evidence

The installed controller is PCI `8086:e376`, subsystem `8086:0111`, handled by
`btintel_pcie`. The saved 7.3.1 Hibernate window has `BT reprobe failed`
and four `Received gp1 mailbox interrupt` records, then successful firmware/DDC
initialization and MGMT registration. See [the boot audit](boot-errors.md).
Neither controller registration nor restored VPN/session proves Bluetooth-device
functionality or that all these messages share one cause.

The 7.3.1 driver routes both `.thaw` and `.restore` through a function that requests
FLR when the saved event was FREEZE/HIBERNATE. Linux's Hibernate snapshot path
also calls `dpm_resume(PMSG_THAW)` **before writing the image and powering off**;
thaw is not exclusive to a failed attempt. At that point firmware has not lost
power, so the extra asynchronous reset/reprobe is unnecessary. The exact errno
behind the observed reprobe failure is still unknown; removing an unnecessary
reset is not proof that every possible reprobe failure is fixed.

Two upstream fixes are backported, only via Lenovo's `boot.kernelPatches`:

1. [`12997a385f71`](https://github.com/torvalds/linux/commit/12997a385f7140c66f733128b76845fd906c270a),
   [refresh-dstate patch](btintel-pcie-refresh-dstate.patch): refresh the boot-stage
   cache from hardware before the missed-interrupt fallback state check. This
   avoids a false `-EBUSY` when hardware reached the requested D-state.
2. [`2926eb396711`](https://github.com/torvalds/linux/commit/2926eb396711f1f843a0aafee6778822f50e9021),
   [PM-flow patch](btintel-pcie-pm-flow.patch): separate thaw's normal D0 transition
   from true restore's FLR/firmware recovery, distinguish S0ix from S3, and retain
   error reporting/recovery. True S4 recovery is **not disabled**.

Only header context differs from the original patches: 7.3.1 lacks later mailbox
and debug fields. All added/removed source lines match upstream, including the
header comment and removal of `pm_sx_event`. No unrelated driver series is pulled
in. The PM patches do not choose a kernel version themselves. The subsequent
kernel-only update changes 7.3.1 to 7.3.4 and adds one lock input, while preserving
all existing input nodes, NVIDIA/firmware versions, stable Mesa and other hosts.
NVIDIA remains selected from the patched kernel's package set, using its compiler
and headers. Applying these changes requires a local kernel/module rebuild.

The inspected stable **7.3.4** still has the old thaw/restore and GP1 code, so a
stable point update alone is not an alternative fix. Mainline's GP1 mailbox
processing is a substantial separate implementation, not a log-level adjustment.
These backports do not implement it. Keep the mailbox finding open; no message
filter, driver disablement, fixed delay or resume restart hook is added.

## Focused checks

From the repository root, with unpatched source containing
`drivers/bluetooth/btintel_pcie.c` and `.h`:

```fish
set linux_source /path/to/unpatched/linux-source
python3 -B hosts/laptop/test_btintel_pm.py $linux_source
nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/test-bluetooth-pm.nix
```

The Python test extracts actual D-state functions, PM callbacks, callback table
and state definitions. The C harness mocks PCI, interrupts/registers, reset
requests, time and diagnostics; PM routing uses a mock transition function while
the separate fallback cases execute the real `set_dxstate`. Twelve cases cover
thaw, true restore, poweroff, S0ix, S3, error propagation, error/halt recovery,
missed interrupts in both directions, exhausted retries and delivered interrupts.
The default run reproduces baseline defects before requiring corrected behavior
with both patches applied using `--fuzz=0`. It does not build a kernel, test real
IRQ concurrency, execute a reset worker or establish firmware/device behavior.

The original tested 7.3.1 source is from the upstream stable tag; the C file matches the
previously retained exact-version source. The Nix source archive was no longer
present locally, so it was not re-extracted. No kernel realization was requested.
Selected Nix declarations check that the patches actually reach the chosen kernel,
preserve existing package patches/source/version and matching NVIDIA/BlueZ, leave
other hosts alone, and retain the cleanup reminder. This is not a full system or
NVIDIA module compilation check.

After the separate kernel-source change, the same baseline/patched test passes
on the selected 7.3.4 stable-tag C/header source, with no fuzz or line offsets.
Both fixes are still needed; neither became redundant in this point update.
Selected declarations now also require NVIDIA open-module `SYSSRC`/`SYSOUT`
to reference the actual patched kernel's headers and require the same compiler
derivation. The declaration check itself does not establish compilation or ABI acceptance;
the subsequent built-result review below separately confirms built modules.

Completed locally: baseline/patched contracts, zero-fuzz application, exact
upstream added/removed-line comparison and selected merged declarations for
Lenovo/Acer/desktop. Server is excluded from merged evaluation because its
external settings are not selected; flake composition imports this module only
on Lenovo. The removal-mode control passes on a temporarily patched source tree
without applying patches inside the test and rejects pristine 7.3.1; this is a
harness control, not a claim about a newer upstream release. Changed Nix files
pass pinned nixfmt 1.5.0. Ruff/Prettier are unavailable, so Python/Markdown were
not run through substitute formatters. No agent-run kernel/module/system build was run.

After the user reported a successful NixOS build, review inspected the existing
`result` (no rebuild): system `gn2f71lbm17cr7mk1wyqyz3clqmjzcdr`, kernel
`gf6c6ilz4nkma7xrzv6iisafnack99ky-linux-7.3.4`. The built kernel derivation's
structured patch attributes reference both backports with bytes matching the
current files. Its merged module tree includes NVIDIA open 615.78.08 and
`btintel_pcie`; `modinfo` reports `7.3.4 SMP preempt mod_unload` for both NVIDIA
core/DRM and Bluetooth modules. This confirms built artifacts/metadata, not real
module loading, Bluetooth, GPU or Hibernate acceptance. At that review, running/current
system still used 7.3.1. Source/configuration review found no known application blocker.

The user then applied/rebooted. Boot `3d979c37f8d44f169933195991de40e3` confirms
running/current/booted 7.3.4, loaded NVIDIA 615.78.08 and `btintel_pcie` binding.
BlueZ's adapter is powered and firmware/DDC/MGMT initialize, but four GP1 startup
messages remain. A subsequent manual Hibernate at 17:16:57–17:17:53 returns, but
still records one reprobe error, four GP1 messages, SPD5118/panel/ISH errors and
controller re-registration as hci1. The user reports initial headphone connection
trouble; later snapshots show a connected device and running A2DP/aptX sink. The
user then confirms audible output after several reconnect/remove/add attempts and
explicitly defers headphone connection/tuning investigation. Automatic reconnection
and full device/GPU acceptance remain open. See [the boot audit](boot-errors.md) for
private export coverage and the independent ISH/WirePlumber/firmware findings.

Further exact-source review rules out the normal positive attach return as the
reason for `BT reprobe failed`: the rescan helper normalizes it to zero. PM probe
deferral (`-EPROBE_DEFER`) followed by retry is a source-supported hypothesis, not
the measured errno on this machine. No live tracing, diagnostic suppression or
broader driver-core reprobe backport was introduced. The boot audit
links the source/review evidence and the separate upstream SPD instantiation fix.

## Updating and explicitly dropping the backports

NixOS emits **BTINTEL PM CLEANUP** while the backports remain configured. It is a
deliberate update reminder, not an automatic version-based switch. Upstream can
backport fixes under different commit IDs, and a patch conflict can also mean an
unrelated refactor. Neither the version nor a conflict proves correctness.

1. Review the new selected kernel's **unpatched** source after an input update.
   Keep the existing lock review; no network Git operation is needed here.
2. Run the fixed-behavior test without applying either backport:

   ```fish
   set linux_source /path/to/new/unpatched/linux-source
   python3 -B hosts/laptop/test_btintel_pm.py $linux_source --check-upstream
   ```

   If upstream refactored the functions, the harness must be reviewed/adapted
   while preserving the contracts. Compilation/extraction failure is not proof
   that the fix is absent. If only one fix landed, review that patch separately;
   do not drop both or keep applying a duplicate. Partial inclusion needs an
   explicit patch/harness update, not an automatic fallback.
3. Once both fixes are upstream and the unpatched checks pass, remove the two
   named entries and the `BTINTEL PM CLEANUP` warning from `bluetooth.nix`, delete
   the two `.patch` files, and adjust declaration assertions to require their
   absence. Retain `test_btintel_pm.py`, `btintel-pm-test.c` and the behavioral
   scenarios; use `--check-upstream` from then on. Update this document/audit.
4. Review/build the affected Lenovo NixOS output, then apply/reboot and repeat the
   live Bluetooth/Hibernate checks. Do not remove the independent BlueZ selection
   based on a kernel fix. No Home Manager activation is needed.

## User application and live acceptance

Save work and review the kernel build cost/free disk space before proceeding.
No build, activation, driver reload or Hibernate is run by the agent.

1. Build only Lenovo NixOS: `nixos-rebuild build --flake .#laptop` (completed).
2. After reviewing the result, apply with
   `sudo nixos-rebuild switch --flake .#laptop`, then reboot. A switch alone does
   not replace the running kernel. Keep a known-good boot generation available.
   Application/reboot are completed; continue with device and Hibernate acceptance.
3. Confirm the rebooted generation, connect a real Bluetooth device, and check
   its actual function (audio/input as applicable) before Hibernate.
4. Run one manual Hibernate cycle and record the approximate entry/exit times.
   Check device function/reconnection and the kernel journal around both phases.
   The hypothesis is removal of the unnecessary pre-poweroff reset, not guaranteed
   disappearance of GP1 messages. Keep any remaining reprobe error visible.
5. Confirm session/VPN restoration remains intact. SPD5118/panel/ISH messages are
   separate findings; do not call this full Hibernate acceptance.
