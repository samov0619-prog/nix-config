# Waybar disk status

Acer, desktop and the Lenovo draft show `custom/disk` beside CPU/RAM:

```text
disk:12% · 18/93 GiB
```

The percentage is **I/O busy time**, followed by **available / total filesystem
space** in GiB, not percent full. Hover shows more precise space, the kernel disk
name, read/write MiB/s and the metric's meaning. Dark/light styles share the normal
module padding and text colors. Panel fit/tooltip rendering need live acceptance.

## Scope and mechanism

- The configured path is the profile's home directory: a separate `/home` is
  handled without assuming it shares `/`. Capacity is this filesystem, not the
  whole SSD including swap/other partitions. Available space uses `f_bavail`,
  excluding administrator-reserved blocks; it may not equal total minus used.
- `os.stat().st_dev` locates `/sys/dev/block/<major>:<minor>`. A partition maps to
  its whole parent disk, without hardcoded SATA/NVMe names. I/O includes **all**
  partitions of that disk, including swap; it is not per-directory or per-process.
- A Waybar-owned Python child emits flushed JSON lines every five seconds. Its
  interpreter and script are explicit Nix references in the installed wrapper,
  not dependencies on shell PATH. No separate systemd service, sysstat dependency,
  sudo, persistent cache, disk benchmark or file-content scan is added. Multiple
  bar instances can each have a small reader; there is no shared daemon.
- Counter deltas use monotonic elapsed time. Sector counts always mean 512 bytes,
  regardless of the device's logical sector size. Busy uses the delta of kernel
  I/O milliseconds, bounded to 0–100%. This is a kernel busy-time approximation,
  **not maximum bandwidth/saturation**, especially on parallel NVMe devices.
- The initial sample needs one interval for rates. Missing/malformed counters,
  counter rollback or a changed `diskseq` never produce invented idle `0%` or
  negative rates. Missing filesystem capacity is explicit as well. Filesystem
  space remains visible when only I/O is unavailable. Stacked device-mapper/RAID,
  network, tmpfs and unsupported multi-device filesystems have no guessed physical
  aggregation: I/O is unavailable rather than double-counted. These are limitations,
  not a claim of end-to-end support for every storage layout.
- `home/core-set/yazi-free-space.nix` retains the previous Yazi widget by default.
  This Waybar module disables it only on the three GUI consumers receiving the
  replacement. Mac/server keep their old widget; archive/image openers, compress
  plugin and the separate Yazi window-context Lua hook are unchanged.

Contracts: [Waybar 0.15 custom JSON stream](https://github.com/Alexays/Waybar/blob/0.15.0/man/waybar-custom.5.scd),
[Linux block statistics](https://docs.kernel.org/block/stat.html),
[sysfs counters/diskseq](https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-block).

## Checks and application

```fish
python3 -B home/linux/modules/waybar/tests/test_disk_status.py
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/modules/waybar/tests/test-disk.nix
```

Fixtures exercise the real helper: partition/whole-disk/NVMe discovery, counter
fields/sector units, available vs reserved space, elapsed-time rates, idle and
clamped busy, resets/replacement, missing/stacked devices, malformed counters,
filesystem failure and actual two-line CLI output. Config fixtures check all
three JSONC panels use a continuous worker, not competing Waybar polling. Selected
merged declarations cover all five HM profiles and preservation of Yazi context.
An additional short read-only smoke on Acer produced real capacity and I/O JSON;
it did not benchmark the disk or verify the built wrapper/installed GTK panel.
No full HM/Waybar build or activation was run by the agent.

1. After review, apply your profile: `home-manager switch --flake .#samov-laptop-old`
   on Acer, or `.#samov-desktop` on desktop. Do not apply the Lenovo draft on Acer.
2. Reload the existing panel with `pkill -USR2 waybar`; reopen Yazi. The current
   configs use Waybar's default SIGUSR2 reload action. No Hyprland logout or
   NixOS rebuild is needed.
3. Wait at least five seconds. Check free/total space, I/O percentage and hover
   read/write rates. Compare available space with `df -h "$HOME"` (rounding may
   differ). Observe ordinary activity, not an artificial write/load test.
4. Check the block fits the panel and remains readable in both F11 themes; Yazi
   no longer shows `FREE`, but ordinary navigation/preview and window context work.

Lenovo follows the same procedure after its installation blockers are resolved.

## Other panel and menu helpers

- `nix-updates-view.sh` reads the local cache and compares its lock hash with
  `NIX_FLAKE/flake.lock`. A missing workspace/environment/lock means **unknown**,
  never a still-valid cached clean/pending result. It performs no network request.
- `check-nix-updates.sh` is invoked on click, not by a polling timer. It calls
  `nix flake update` for all inputs with a temporary `--output-lock-file`, compares
  locks and removes its temporary directory. This is a network-capable update
  **check**, not a build, activation or change to the repository's lock. It does
  not replace the separate one-input `nix-flake-update-verify` workflow. No real
  update/network operation was run during this audit; only a fake Nix was used.
- `gp.sh` retains the existing single-NVIDIA-GPU reader on Acer/desktop. Lenovo
  instead prepares a click-only 60-second reader: idle listeners make no GPU
  queries, but an explicit click may wake it. After expiration only the GPU button
  remains. Its helper/tests/application are in
  [the Lenovo README](../../laptop/waybar/README.md). The user confirms correct GPU
  return to sleep with the initial reader and subsequently accepted the plain GPU
  button after expiration. This is user acceptance, not independent UI/PM
  observation. Shared CSS removes the colored PPD fills (only Lenovo
  uses that module), adds neutral hover and styles only the new GPU module ID;
  Acer/desktop's GPU modules are unchanged.
- `startup-time.sh` parses the current boot's systemd startup summary, not the
  time to a usable desktop. Seconds/minutes/hours and missing summaries are
  covered by fixture logs. Colour thresholds are cosmetic legacy host policy;
  revisit the Acer/Lenovo mapping at the agreed host rename, not as a boot SLA.
  Actual journals were not read in this step.
- The Tofi session menu still accepts only `Poweroff`/`Reboot`; cancellation or
  another answer performs no action. Tests extract its actual shell body from
  `../tofi/module.nix` and use a fake systemctl, never real power actions.
- The terminal-layout watcher was source-reviewed only: it listens to Hyprland
  focus events and selects layout 0 when entering a terminal, reconnecting after
  a socket loss. No real window inventory/layout changes or live reconnect test.

```fish
python3 -B home/linux/modules/waybar/tests/test_panel_helpers.py
```

Eight test methods exercise the actual scripts, with subcases for cache validity,
missing workspace/lock, loading/error/empty cache, temporary-lock-only clean/pending
checks and failures, preflight, power-menu cancellation, fake GPU results and boot
time parsing. The old viewer failed six missing-workspace/lock subcases; all pass
after the two-line fix. Builds, installed panel/UI and actual Nix network behaviour
are not covered. Beautysh/Ruff/Prettier were unavailable; existing script layout
was preserved, without installing a formatter or using a fallback.

For the viewer fix: review the diff, apply the appropriate HM profile, then reload
Waybar with `pkill -USR2 waybar` as above. Do not click the update icon just to
validate rendering: that explicitly starts the network-capable check. NixOS
rebuild, lock update and service restart are unnecessary.
