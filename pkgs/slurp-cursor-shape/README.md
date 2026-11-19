# Slurp: compositor-owned selection cursor

The shared Linux Home Manager screenshot workflow uses stock Slurp 1.5.0 with
the exact upstream commit
[`0465f03a7949da338d90a0788451815a02b6f1d2`](https://github.com/emersion/slurp/commit/0465f03a7949da338d90a0788451815a02b6f1d2).
The release has cursor-shape request code but never binds its advertised global.
The fix binds it, guards cleanup of the unused client cursor theme and destroys
the manager on exit. No new protocol, custom cursor renderer or theme is added.

With `wp_cursor_shape_manager_v1`, Slurp requests a crosshair and Hyprland owns
its theme/size, including the installed Rose Pine Hyprcursor theme. On compositors
without the protocol, the existing Xcursor fallback remains unchanged. This does
not align GTK/application-owned cursors or change monitor scaling and PNG size.

The patched package is used both by `hypr-screenshot-region` and the interactive
`slurp` command on the three Linux GUI profiles. Mac/server are unchanged.

## Checks and removal contract

```fish
python3 -B pkgs/slurp-cursor-shape/tests/test_install_check.py
python3 -B pkgs/slurp-cursor-shape/tests/test_cursor_shape.py /path/to/slurp-source
python3 -B pkgs/slurp-cursor-shape/tests/test_cursor_shape.py /path/to/unpatched-source --check-upstream
```

The shell fixture checks source-root selection from a Meson build directory,
including a source directory containing spaces; its Python invocation is mocked.
The next command applies the patch to a disposable copy with zero fuzz. The
last is the removal contract: no patch is applied. A tiny C harness executes
the actual registry callback with stubbed protocol interfaces/bind calls. It
checks binding a version-2 advertised manager at version 1, unknown globals and
the ordinary shared-memory global without a cursor-shape manager. Three source
contracts check guarded cleanup and retained native-crosshair/Xcursor fallback
paths; those checks do not execute the full Wayland lifecycle. The package runs
these contracts on its patched source during installCheck.

The first user build reached installCheck but failed because it was given `$PWD`
(`/build/source/build`) instead of the source root. The phase now passes
`$NIX_BUILD_TOP/$sourceRoot`, following stdenv's unpacked-source location. The
fix does not disable installCheck or change the upstream patch. The user later
reported that the corrected setup works on Lenovo; the agent did not repeat the
package build or independently observe the full live scenario matrix.

The new shell fixture passes for both source-directory layouts. The actual
Nix-evaluated installCheck phase was also run from a disposable `source/build`
directory against patched 1.5.0 source: all four contracts pass (only `runHook`
was stubbed). This verifies the corrected invocation, not a repeated package
build or installed-cursor behavior.

Remove the package override and registered patch only after the unpatched
candidate passes these contracts (or an explicitly reviewed equivalent), then
the live scenarios below pass. Preserve the regression checks when removing the
backport. A newer version number or reverse-applying patch is not sufficient.

After the user builds/applies Home Manager:

1. Press F10/Print on the 1.6-scaled Lenovo panel: selection must use a normal-size
   crosshair from the compositor theme. The crosshair need not look like an arrow.
2. Cancel with Esc: no capture/editor starts and the ordinary cursor returns.
3. Complete a safe selection: Swappy opens; save/copy remain manual and PNG
   resolution is unchanged. No cursor-size change should persist after exit.
4. If protocol confirmation is needed, run `env WAYLAND_DEBUG=1 slurp`, cancel,
   and check for binding `wp_cursor_shape_manager_v1` plus `set_shape(..., 8)`
   (crosshair), instead of a client-owned cursor surface. Avoid sharing full logs.

Source/harness checks alone are not a Slurp build or live protocol/theme proof.
See the [screenshot audit](../../docs/laptop-audit/screenshots.md) for diagnosis
and the limits of the earlier one-shot Adwaita comparison.
