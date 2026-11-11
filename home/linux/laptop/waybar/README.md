# Lenovo Waybar controls

`../default.nix` selects the package override and manual GPU helper only for
Lenovo's `samov-laptop`. Acer/desktop retain their existing GPU reader and stock
Waybar. The shared CSS now gives Lenovo's PPD control a monochrome appearance;
only Lenovo currently includes that module.

## Click-only GPU monitoring

`custom/gpu-manual` sits immediately after the disk module. Initially it displays
**GPU**, with the same neutral hover highlight as the audio control. LMB enables
one minute of NVIDIA utilization and VRAM used/total sampling. Another click
renews the minute from that click, not from the original start. The bar shows
utilization and used GiB, with total VRAM and the last sample time in its tooltip.
After expiration the figures disappear from both the bar and tooltip, leaving
the plain **GPU** button. Before the first successful sample, errors also leave
the plain GPU label, not fabricated zeroes. During an active window, failed
updates keep earlier figures dimmed and explicitly marked as not current.

This deliberately supersedes the earlier always-passive indicator proposal:
**a click may wake NVIDIA and sampling can postpone its sleep during that minute**.
There is no claim of passive telemetry while enabled. The helper never writes
power policy, reloads a driver or starts a persistent NVML/nvidia-smi session.

`gpu-status.py` emits a Waybar JSON stream and waits on a private session-local
Unix datagram socket. While idle it blocks without periodic wake-ups, NVIDIA
queries or reading cached metrics. Clicks reach existing bar listeners; they do
not launch an independent polling daemon/service. During an enabled window:

- A short-lived, PCI-targeted `nvidia-smi` queries only utilization and VRAM
  used/total, at most once every two seconds across bars on multiple outputs.
- A nonblocking lock and a small cache in private `$XDG_RUNTIME_DIR` deduplicate
  samples. The cache alone never enables monitoring. Restarted bars start idle.
- Each child has a timeout of at most two seconds, shortened to the remaining
  window; timeout/termination kills and reaps it. No new query is scheduled after
  expiration. `CLOCK_BOOTTIME` counts suspend time, preventing a new minute after
  resume. All driver handles belong to the short-lived command, not the listener.
- Errors keep previous figures explicitly stale rather than showing them as
  fresh data. Once the window expires, listeners return to blocking IPC waits.

Timers/cancellation remain userspace best effort: scheduling latency and an
uninterruptible driver/kernel ioctl cannot be forcibly bounded by Python. The
minute is a query budget, not a promise of D3cold at exactly 60 seconds. The user
applied the initial version and confirmed correct GPU return to sleep after
monitoring. This is user-reported acceptance of that scenario, not independent
agent measurement, repeated cycles or broader PM coverage. The user subsequently
applied and accepted the hide-on-expiry adjustment: after the minute, the plain
GPU button returns without old figures. It does not change the sampling budget
or power policy. No independent agent UI observation is claimed.

The PPD icon now inherits light/dark foreground colors without the old red/blue/
green fills. Its three distinct icons, confirmed profile, click cycle and dynamic
tooltip remain unchanged. Both PPD and the manual GPU control use the existing
grey hover highlight. No other module's colors are changed.

### Checks and application

Small tests use fake GPU commands and real local IPC/subprocesses, never the GPU:

```fish
python3 -B home/linux/laptop/waybar/tests/test_gpu_status.py
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/laptop/waybar/tests/test-gpu.nix
```

They cover startup/expired-window silence, renewal, stale/error data, malformed
metrics/cache, multi-output query sharing, bounded child timeouts, termination
cleanup, boot-time expiry, raw config placement and theme selectors. The Nix
fixture checks selected merged Lenovo/Acer/desktop declarations and the wrapper.
Completed: 19 new helper tests, eight existing panel-helper tests, the selected
merged GPU declarations and existing Lenovo draft fixture, plus pinned nixfmt.
The installed pinned GTK3 CSS provider also parses the common/light/dark styles
successfully without opening a display or window; this is syntax/import coverage,
not rendered hover/color acceptance.
This does not build the helper/package, exercise real Waybar events/GTK rendering,
or prove hardware power behavior. Prettier/Ruff are unavailable; layout is
preserved without substituting a formatter.

User application/acceptance, **Lenovo only**:

1. Review changes. If the new helper is still untracked, include its source in
   the Git flake with `git add -- home/linux/laptop/waybar/gpu-status.py` (no commit
   required), then run `home-manager switch --flake .#samov-laptop`.
2. Reload the bar with `pkill -USR2 waybar`. Confirm a plain GPU button after disk,
   grey hover, and monochrome PPD icons/hover in both light and dark themes.
3. Before clicking, check that an otherwise idle GPU remains suspended using
   `cat /sys/bus/pci/devices/0000:02:00.0/power/runtime_status`. Do not use
   `nvidia-smi` to test passive behavior: that itself accesses the GPU.
4. During an intentionally started NVIDIA workload, click GPU. Check utilization,
   VRAM and tooltip, then confirm renewal with a second click if wanted.
5. After the last click's minute, confirm the plain GPU button and stopped tooltip,
   without old figures. Close the workload and allow normal driver idle handling; check
   `runtime_status` above and
   `cat /sys/bus/pci/devices/0000:02:00.0/power_state` for suspended/D3cold.
6. Reload Waybar again: it should return to the plain GPU label, with no automatic
   sampling. No NixOS rebuild, reboot or driver/VPN/audio changes are needed.

## Power-profile tooltip package override

The patch targets pinned Waybar **0.15.0**. It adds tooltip substitutions:

- `{previous_profile}` / `{next_profile}`: canonical PPD profile names.
- `{profile_label}` / `{previous_profile_label}` / `{next_profile_label}`:
  names translated through the optional `profile-labels` object; unknown names
  fall back to the canonical name. Existing `{profile}` remains unchanged.

The Lenovo configuration shows, for example:

```text
Сбережение ← ПКМ | Баланс | ЛКМ → Производительность
```

Tooltip and clicks use the same `powerProfileCycleIndex` helper over the actual
PPD list. Two profiles, wraparound and unknown profile names do not assume the
presence of `performance`. Changes to the profile list refresh the module; changes
to the active profile still arrive through the existing D-Bus subscription.
No separate process or polling is added. A rejected switch does not optimistically
change the displayed profile: PPD's confirmed state remains authoritative.

## Checks and limitations

Completed: a tiny C++17 unit test of the production cycle helper (zero/one/two/three
profiles, bounds, wraparound and custom ordering), zero-fuzz patch dry-run against
the upstream 0.15.0 source, Nix declaration fixtures and actual pinned package
attribute inspection preserving upstream patch hooks. These do **not** compile
the full Waybar module or exercise GTK, D-Bus permissions or the live tooltip.

Reproduce the small unit test from the repository root:

```fish
c++ -std=c++17 -Wall -Wextra -Werror -pedantic home/linux/laptop/waybar/tests/test-cycle.cpp -o /tmp/opencode/lenovo-waybar-cycle-test
/tmp/opencode/lenovo-waybar-cycle-test
```

Optional package-only build, from the repository root, **for the user to run**:

```fish
nix build --impure --no-link --expr 'let f = builtins.getFlake (toString ./.); in import ./home/linux/laptop/waybar/package.nix { waybar = f.inputs.nixpkgs.legacyPackages.x86_64-linux.waybar; }'
```

After reviewing/building/applying the Lenovo HM configuration:

1. Compare `powerprofilesctl list` / `powerprofilesctl get` with the icon and hover.
2. Check LMB/RMB transitions from every available profile, including wraparound.
3. Set another available profile with `powerprofilesctl set <profile>`; the icon
   and both hover destinations must update without restarting Waybar.
4. Confirm that a failed switch does not leave a false active mode in the UI.

Do not activate this HM profile on Acer. On nixpkgs updates, review and refresh
this patch against the chosen Waybar source; do not silently drop it while leaving
unsupported placeholders in the config.
