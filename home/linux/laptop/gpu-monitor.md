# Manual NVIDIA profile comparison

Run immediately from the repository, without a build or activation:

```fish
python3 -B home/linux/laptop/gpu-monitor.py
```

One row every **5 seconds**, indefinitely; **Ctrl+C** stops. Rows contain time,
the PPD profile (`power-saver`, `balanced`, `performance`), GPU temperature in °C,
reported board power in watts, GPU utilization, VRAM used/total MiB and VRAM capacity
percentage. A heading repeats every 20 rows, but no rows are discarded by the
program. Terminal scrollback has its own limit. To retain the full run:

```fish
python3 -B home/linux/laptop/gpu-monitor.py | tee /tmp/opencode/gpu-monitor.log
```

Change the profile with Waybar; this monitor only reads it. The profile label is
sampled before the GPU query, not an atomic record of a simultaneous switch.
Use the same game scene, power source, settings and FPS cap for each profile, allow
settling time, and repeat the comparison. A minimized/unfocused game may throttle
itself. GPU utilization is not FPS; PPD does not promise a particular NVIDIA power
limit. Board watts are not whole-laptop/battery consumption. The driver may average
power/utilization over its own interval; these are not 5-second integrated readings.

**Explicit NVIDIA polling can wake the GPU or postpone sleep.** Stop the monitor
before checking RTD3 or leaving the game; there is no idle mode, auto-start, service,
cache or NVML session held between samples. Each query is a short-lived `nvidia-smi`
process (2-second timeout); PPD has a separate 1-second timeout. Userspace cannot
forcibly bound an uninterruptible kernel ioctl. Slow queries do not trigger catch-up
bursts. Unsupported values show `n/a`; failed queries are new error rows, not stale
metrics presented as current. Missing PPD does not hide valid GPU metrics.

The Lenovo HM leaf installs `gpu-monitor`, using the system's matching
`nvidia-smi` and `powerprofilesctl` on PATH, not another NVIDIA package/driver.
Default GPU is Lenovo's `0000:02:00.0`; `--gpu` accepts another PCI ID or NVIDIA
index. `--interval` changes cadence (minimum 1 second); `--once` prints one snapshot.

## Checks and application

```fish
python3 -B home/linux/laptop/tests/test_gpu_monitor.py
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/laptop/tests/test-gpu-monitor.nix
```

Tests cover actual parsing, read-only commands/timeouts, missing/invalid values,
failure handling, continuous history beyond 20 rows, per-row profiles, terminal
control sanitization and cadence without real NVIDIA/PPD access. A separate single
real `--once` query on Lenovo returned valid temperature/power/utilization/VRAM and
`balanced`; it is not an interactive session, repeated sampling or a profile-impact
benchmark. No build, activation or profile change was performed by the agent.

1. For immediate game testing use the source command above, then switch profiles
   yourself in Waybar while keeping the workload comparable.
2. Optionally install the short command later:
   `home-manager switch --flake .#samov-laptop`, then run `gpu-monitor`.
   Acer/desktop/Mac/server are unchanged; no NixOS activation or panel reload.
3. Stop with Ctrl+C when finished. If sharing results, include game scene/FPS cap,
   plugged-in/battery state and the time windows for each profile. Any log created
   by `tee` is manual state outside Git, not automatically rotated or removed.
