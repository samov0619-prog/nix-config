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
python3 -B home/linux/modules/waybar/test_disk_status.py
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/modules/waybar/test-disk.nix
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

1. After review, apply your profile: `home-manager switch --flake .#samov-laptop`
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
