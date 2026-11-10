# Lenovo-only Waybar power-profile tooltip

`../default.nix` selects this override only for Lenovo's `samov-laptop`. No global
overlay, shared Waybar module, Acer or other existing profile is changed.

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
c++ -std=c++17 -Wall -Wextra -Werror -pedantic home/linux/laptop/waybar/test-cycle.cpp -o /tmp/opencode/lenovo-waybar-cycle-test
/tmp/opencode/lenovo-waybar-cycle-test
```

Optional package-only build, from the repository root, **for the user to run**:

```fish
nix build --impure --no-link --expr 'let f = builtins.getFlake (toString ./.); in import ./home/linux/laptop/waybar/package.nix { waybar = f.inputs.nixpkgs.legacyPackages.x86_64-linux.waybar; }'
```

After the Lenovo draft blockers are resolved and its NixOS/HM configurations are
reviewed, built and applied on Lenovo:

1. Compare `powerprofilesctl list` / `powerprofilesctl get` with the icon and hover.
2. Check LMB/RMB transitions from every available profile, including wraparound.
3. Set another available profile with `powerprofilesctl set <profile>`; the icon
   and both hover destinations must update without restarting Waybar.
4. Confirm that a failed switch does not leave a false active mode in the UI.

Do not activate this HM profile on Acer. No activation is needed on the current
machine. The system draft's installation guard is unchanged. On nixpkgs updates,
review and refresh this patch against the chosen Waybar source; do not silently
drop it while leaving unsupported placeholders in the config.
