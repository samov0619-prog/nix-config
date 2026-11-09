# Kitty: generated configuration and automatic themes

The version-matched upstream configuration is combined with shared/platform
fragments, then `kitty-langmap/build.py` adds Russian-layout counterparts to active
shortcuts. Commented upstream examples stay inactive. Do not replace this with a
full copied `kitty.conf` snapshot.

## Automatic-theme notification fix

`overlay.nix` adds `auto-theme-background-images.patch` to Linux Home Manager's
Kitty package. Acer, desktop and the Lenovo draft use the same fixed `pkgs.kitty`,
including existing launch helpers and the template generator. Server gains no
Kitty; Mac keeps its existing unmodified package. NixOS packages and the separate
corporate Mac archive are unchanged. No lock update, daemon, polling, app-specific
theme writes or personal config/cache deletion is involved.

This is the two-hunk upstream backport of
[2d9b10413490, Fix #10058](https://github.com/kovidgoyal/kitty/commit/2d9b10413490c6d8e9e029ddeda7b7b379538480),
included in Kitty 0.47.1. In 0.47.0 auto themes collect `background_image` as a tuple,
even `()` when no image is configured. The runtime setter accepts one path or
`None`. The old call changes colors, then raises
`TypeError: argument 1 must be str or None, not tuple` before sending the subscribed
child its theme notification. Thus Kitty itself changes but OpenCode stays stale.
The backport maps an empty collection to `None`, otherwise its first/default image.
The full configuration collection and layout/interpolation/tint options are kept;
exceptions are not swallowed and the notification policy is not changed.

This does not establish complete replacement/cycling behavior for different
multi-image collections in different automatic themes. Current home themes have
no background images. When updating Kitty to 0.47.1 or later, verify that upstream
contains these hunks, then remove the local patch, overlay and its registration.
A patch conflict is a review prompt, not a reason to silently discard changes.

## Evidence and checks

- Read-only probes verified the new OpenCode binary, Kitty's active subscription
  and the actual dark/light default background. Manual native notification delivery
  worked; automatic theme changes produced no input notification.
- User-authorized, one-call Kitty tracing captured the exact exception at
  `colors.py:295`, with `notify_bg=true`, a changed background and the correct
  subscribed window. Its stderr was `/dev/null`, explaining the invisible failure.
  Tracing and all temporary Kitty function replacements were restored afterward.
- With separate approval, the actual backported function was temporarily installed
  in that single running Kitty. The user confirmed live F11 both ways, and the
  opt-in protocol observer recorded real notifications, OSC color replies and
  OpenCode renderer/theme mode changes. This verifies that live intervention,
  **not** a newly built/installed Kitty package or other hosts. The temporary
  OpenCode observer was then disabled; no personal preferences were edited.

```fish
python3 -B home/modules/kitty/test_auto_theme.py
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/modules/kitty/test-declarations.nix
```

Six Python tests apply the real patch to the installed 0.47.0 source and execute
its actual `patch_colors` function with native/GUI contract fixtures: old failure
before notification, both color directions without images, first-image selection,
preserved image options/collection, absent image value, explicit notification
suppression and unchanged-background behavior. Native profile allocation/comparison
was separately checked in the installed Kitty, without altering real windows.
These fixtures are not an independent native GUI/package test. An alternate
baseline source can be supplied through `KITTY_TEST_COLORS_SOURCE`.
Selected merged declarations check all five HM profiles without realizing packages.

## Apply on Acer

1. Review, then build only `nix build .#homeConfigurations.samov-laptop.activationPackage`.
   **This rebuilds Kitty**, potentially acquiring build dependencies. It does not
   require another OpenCode rebuild. No build or activation was run by the agent.
2. Apply `home-manager switch --flake .#samov-laptop`.
3. Finish active work, fully close the old Kitty processes, and launch a fresh
   Kitty. Reopening only an OpenCode tab does not replace the terminal process.
4. Start OpenCode and verify F11 in both directions without reopening it.

Desktop uses its own HM profile. Do not apply the Lenovo draft on Acer. No NixOS
rebuild or OpenCode shared-service restart is required for this Kitty-only change.
