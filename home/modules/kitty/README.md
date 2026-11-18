# Kitty interface parity

## Scope and sources

The 2026-11-18 comparison used the active Lenovo configuration (Kitty 0.49.1),
this Home Manager module and macOS config commit `019c79e` from the supplied
`kitty-config.bundle`, inspected through `/home/samov/scratch/kitty-config.git`.
The Mac application/version and live UI were not accessible. The independent
Mac config is **not** the same as this repository's `darwin.conf`.

Keep the independent Mac configuration. No automatic Git synchronization,
repository migration or extra runtime script is needed. The one-time
[`macos/kitty-ui.patch`](macos/kitty-ui.patch) targets that supplied commit and
preserves its project launchers, keybindings, fonts and transparency settings.
The shared Home Manager changes also affect other hosts importing this module;
only the Lenovo configuration was compared against an active installation.

## Implemented interface changes

- Put the powerline tab bar at the top on both systems. Keep the default minimum
  of two tabs, so a one-tab terminal has no tab bar.
- Set `window_title_bar_min_windows 2`: built-in split title bars appear only
  with at least two visible Kitty windows in a tab. These are not the native
  macOS title bar. A Kitty window here means a terminal pane, not an OS window.
- Put active/inactive colors in the existing automatic theme files. Built-in
  split titles inherit the corresponding tab colors, without duplicate settings
  or a custom renderer. Switching the OS color scheme selects the appropriate
  palette through Kitty's existing automatic theme support.
- Follow the user's later manual adjustments in `kitty-uncommitted.patch`:
  `window_border_width 1px`, full borders (`draw_minimal_borders no`), zero
  margins, 4pt padding, centered cell placement and left-aligned split titles.
  These deliberately supersede the earlier zero-border/top-left proposal.
- Use the user's revised title and border palette, including a pure white
  light-theme terminal background. Keep the existing Linux cursor overrides.

| Theme | Active text / background | Inactive text / background |
| --- | --- | --- |
| Dark | `#F5F6F8` / `#4B6D79` | `#C7CBD4` / `#455360` |
| Light | `#23272F` / `#C7D0DF` | `#444444` / `#ECEEF2` |

Active/inactive borders are `#525866` / `#2C2E34` in dark and
`#444444` / `#FAFAFA` in light. Calculated opaque-color title contrast ratios are
5.16:1 / 4.86:1 (dark active/inactive) and 9.64:1 / 8.38:1 (light).
The active colors follow the user's later `kitty-active-tab-23272F.patch`;
geometry and inactive colors remain as in the previous manual adjustments.
Actual appearance under user-adjusted transparency still needs visual acceptance.

The supplied patch contains repeated `placement_strategy` and light-theme
`inactive_tab_background` entries. Normalize these to their effective final
values: `center` and `#ECEEF2`, respectively. Earlier `top-left` and `#C1C6CC`
entries were overridden in the user's own config and are not copied as duplicates.

### Title inset behavior

Kitty 0.49.1 lays out the title bar using the terminal's whole-cell geometry
(`window.py:Window.set_geometry`). A window whose pixel size is not divisible
by the cell size still has leftover pixels, now distributed with centered
placement. The title background does not automatically extend across that
remainder. There is no separate documented title-bar inset/bleed setting in
this version. Therefore this configuration does **not** guarantee a flush right
edge at every window size. No Kitty source patch, watcher or custom renderer is
introduced to work around that limitation. The user's later choice of full
1px borders and 4pt padding intentionally retains visible insets rather than
enforcing the original edge-to-edge proposal.

## Home Manager launch scheme

The user chose the tab/window migration after the initial UI audit. The shared
HM Kitty config now uses the same launches on Linux and macOS:

| Program | Tab in the active Kitty | Separate OS window |
| --- | --- | --- |
| Fish | `Super+,` | `Super+Shift+,` |
| Yazi | `Super+E` | `Super+Shift+E` |
| Neovim | `Super+N` | `Super+Shift+N` |

All six Kitty launch mappings use native `launch` and shifted/ASCII layout fallback.
The three tab mappings use `--cwd=~`: Fish, Yazi and Neovim start at home,
independent of the focused pane's directory. Kitty expands `~` itself, without
a shell wrapper. The Shift OS-window mappings retain `--cwd=current`.
Yazi also receives `EDITOR=nvim`, matching the Linux launcher.
The old Darwin-specific Neovim/Yazi mappings no longer override the shared
scheme. In particular `Cmd+Shift+N` now means an OS window, not another tab.

On Lenovo, Acer and desktop, Hyprland handles only **Shift+comma/E/N** for
global launches. Physical evdev/XKB codes 59 (comma), 26 (E) and 57 (N) avoid
EN/RU keysym aliases and shifted-punctuation ambiguity. The old unshifted launch
bindings and their Russian aliases are removed, including the unrelated
Russian `Super+Й` terminal alias. `Super+Shift+E` no longer runs sudo Yazi;
no replacement elevated shortcut is invented. F1 help matches this scheme.

Tab commands require a focused Kitty window. Outside Kitty they are not global
application launchers; use Shift+comma/E/N or the application launcher to open the first window. Global
Hyprland launches use the compositor's ordinary launch directory, **not** the
foreground Kitty pane's cwd. This deliberately avoids a custom context/router
script. Kitty's own OS-window mappings (for example on HM-managed macOS) do
inherit the active cwd.

Tab navigation uses `Super+]` / `Super+[` for next/previous.
`Super+Shift+[` / `Super+Shift+]` move the current tab left/right using Kitty's
native `move_tab_backward` / `move_tab_forward`. All four use shifted/ASCII
fallback for EN/RU. The shared Shift+comma/period tab mappings are removed.
Shift+comma opens a terminal OS window in Kitty and globally through Hyprland;
it is not used to move tabs.
`Ctrl+Tab` / `Ctrl+Shift+Tab` also remain available.
Linux `kitty_mod` remains
Ctrl+Shift, avoiding compositor conflicts with dictation/cancel and window
controls. `Super+Q`, workspace switching, pane resizing and recording are not
remapped. On HM macOS `Cmd+Shift+E` replaces URL hints; Shift+brackets now move
tabs instead of selecting them. Shift+comma opens an OS window instead of moving
a tab; the native Shift+period default is not overridden.
No speculative replacement shortcuts
are added. Existing `Cmd+Shift+Left/Right` pane navigation is retained.

`Super+W` closes the current **tab**, including all of its panes, rather than
only the focused pane. Its shifted/ASCII fallback also accepts physical W in
the Russian layout. Hyprland no longer intercepts W or its old Cyrillic alias
on any of the three Linux profiles. The textual workspace/window switcher
remains installed as `hypr-semantic-switcher-tofi`, invoked from a terminal;
no replacement global shortcut is assigned. `Super+Space` still opens the
workspace canvas. Existing close-confirmation policy is unchanged.

The independent Mac config receives the tab controls through the separate
[`macos/kitty-keybindings.patch`](macos/kitty-keybindings.patch), not through HM.
Its launch methods deliberately retain native `new_tab` and `fish -l -c` from
the original Mac config; Shift app/window launches are disabled on request.
`macos/kitty-keybindings-fix.patch` corrects the already applied earlier patch.
The existing `macos/kitty-ui.patch` remains UI-only. See the
[Mac application guide](macos/README.md) for scope, shortcuts and verification.

### Text contrast investigation

The user reports unusually faint `man-cache>` prefixes in both light and dark
terminal output. Nix 2.34.9 emits these prefixes with ANSI FAINT
(`src/libmain/progress-bar.cc`, build-log handling); Kitty's `dim_opacity` is
still the original 0.4. That explains their dim styling, but is not evidence
that a regression was caused by changing tab colors.

Comparing the theme files with Git HEAD found no changes to terminal foreground,
ANSI palette or dimming settings. Only the light terminal background changed
from `#FAFAFA` to `#FFFFFF`, which the user explicitly chose to keep. The dark
terminal palette did not change. Tab/title/border colors are separate settings.
Do not adjust the ANSI palette or `dim_opacity` speculatively.

A read-only query of the focused Kitty process during diagnosis still reported
the old light background `#FAFAFA` and default active-tab background `#EEEEEE`,
not the values in the current files. Reload before comparing old/new appearance;
this snapshot does not establish the configuration active when the screenshots
were taken. No live colors were changed by the diagnostic queries.

### Original keyboard comparison (before migration)

| Action | Lenovo / NixOS | Supplied macOS config |
| --- | --- | --- |
| New OS terminal | `Super+,` via Hyprland | Default `kitty_mod+n` is overridden by Neovim launcher |
| New tab | `Ctrl+Shift+T` | `Cmd+,`, `Cmd+Shift+T` and default `Cmd+T` |
| Next / previous tab | `Ctrl+Tab` / `Ctrl+Shift+Tab`; also `Ctrl+Shift+Right/Left` | `Ctrl+Tab` / `Ctrl+Shift+Tab`; `Cmd+Shift+Right/Left` instead selects panes |
| New Neovim | `Super+N`: OS terminal via Hyprland | `Cmd+N` / `Cmd+Shift+N`: Kitty tab |
| New Yazi | `Super+E`: compositor file manager | `Cmd+E`: Kitty tab |
| Record | `Super+Shift+R`: Handy compositor binding | `Cmd+Shift+R` is unbound in Kitty, reserved for external recording |
| Resize Kitty panes | Default `Ctrl+Shift+R` | Explicit `Ctrl+Shift+R` |
| Reload config | `Ctrl+Shift+F5` | `Cmd+Shift+F5`, or native `Ctrl+Cmd+,` |

`Super` is Kitty's name for Command on macOS. Do not change Linux `kitty_mod` to
Super+Shift wholesale: Hyprland reserves many such chords, including recording
and cancel. Likewise, do not add a Kitty recording action to a key handled by
the compositor/global recording tool.

The initial decision to preserve Lenovo `Super+,` was superseded by the launch
scheme above. The independent Mac config has the behavior in this historical
table until the keyboard patch is applied; its UI patch alone does not change
working-directory handling.

## Keep platform-specific

- Fonts: Mac uses Noto Sans Mono at 12pt; Linux uses the Nerd Font variant at
  14pt plus symbol maps. Physical size depends on DPI/scaling; identical numbers
  do not guarantee identical perceived size. Do not remove fallback maps before
  checking actual glyph availability.
- Lenovo's foreground-aware command-key routing and Linux per-process remote
  socket serve existing integrations; do not copy them blindly to macOS.
- Mac project launch scripts, session files and Chrome shortcuts are local work
  tools. Linux has no equivalent directories/app paths to import them into.
- Preserve macOS dynamic opacity, blur and native title-bar behavior.
  `macos_titlebar_color background` conflicts with transparency, so it is not
  enabled. With the normal opaque background, blur has no visible effect, but
  can become useful when opacity is adjusted dynamically.
- Linux keeps 10,000 scrollback lines and Neovim as pager; Mac currently uses
  Kitty's default 2,000 lines and less. These are functional workflow differences,
  not prerequisites for matching tab/title appearance.
- Both keep Fish, grid layout, cursor trails, audio bell and disabled close
  confirmation. Those last two are explicit behavior choices, not safe cleanup.

## Cleanup candidates, not automatic deletions

- The commented stock configuration is documentation, not enabled bindings;
  removing it only shortens the file. Do not expand this task into rewriting
  the existing generation/langmap machinery.
- `themes/MyTheme.conf` on Mac and the named themes under `themes/` in this module
  duplicate automatic themes but may still be selected manually. They are not
  used by automatic switching and are not updated/deleted by this patch; selecting
  one manually can restore its older title colors.
- Mac `Cmd+Shift+1/2/9/0` shadow some defaults after `kitty_mod cmd+shift`.
  Their project/browser actions may be intentional. The browser shortcuts disable
  web security, and one enables port 9222: keep those only if still deliberately
  needed, not as a cross-platform default. `google_without_cors` is not referenced
  by the active config but could be used manually.
- `allow_remote_control yes` is used by Mac scripts and existing Linux context
  integration. It is broad access (including through terminal/SSH output), not a
  cosmetic option to delete. Hardening needs a separate compatibility check.

## Validation and application

Completed: patch dry-run/application with zero fuzz against the supplied Mac
files; both resulting configs parsed without errors by Kitty 0.49.1; the Linux
config was assembled through the existing langmap generator with the Lenovo
command-key map shape. Kitty's actual automatic-theme parser confirmed matching
tab palettes on both platforms, and contrast/layout arithmetic was checked.
The launch follow-up adds `tests/test_launch.py`: it exercises both assembled
HM platform configs through the existing langmap generator and Kitty parser,
checks resolved action precedence/fallbacks, and checks all three Hyprland
launcher declarations plus the help text. The manual-style follow-up adds
assertions for the requested geometry and literal automatic-theme palette.
Both the supplied patch and the prepared cumulative Mac patch were applied
with zero fuzz to the original Mac files, parsed by Kitty and compared for
effective geometry/colors; HM uses the same palette and geometry.
The separate Mac keyboard patch also applies cleanly before or after the UI
patch with identical results. The full patched config was parsed and its
synthetic EN/RU shortcut resolution checked; the keyboard-only patch leaves
themes and all unrelated config lines unchanged. `test_launch.py` additionally
checks the Mac-specific native/login-shell launches, disabled Shift launches
and tab controls. The correction produces the same config as the revised full
keyboard patch. Mac startup errors remain unverified without the actual host.
This does not establish real keyboard
delivery, foreground cwd integration or native macOS behavior.

```fish
kitty +runpy 'import runpy; runpy.run_path("home/modules/kitty/tests/test_launch.py", run_name="__main__")'
```

No Nix build, activation or live UI test was run. Prettier and Ruff were
unavailable; the existing Markdown/Python layout is preserved without a fallback
formatter.

After reviewing the diff:

1. On Lenovo run `home-manager switch --flake /home/samov/nix-config#samov-laptop`.
   Run `hyprctl reload`, then `hyprctl configerrors`; expect no errors.
   No NixOS rebuild or reboot is required. Other Linux hosts use their own HM
   profile, not `samov-laptop`.
2. Copy `macos/kitty-ui.patch` to `~/Downloads/kitty-ui.patch` on the Mac. Save
   any local config edits, then run `git -C ~/.config/kitty apply --check ~/Downloads/kitty-ui.patch`
   followed by `git -C ~/.config/kitty apply ~/Downloads/kitty-ui.patch`. Stop if
   the check fails; the patch must not overwrite divergent local edits. This is
   a cumulative patch against the original supplied Mac commit. If the Mac
   already has the manual changes from `kitty-uncommitted.patch`, do not apply
   the same UI changes again; the current task brings HM into line with them.
3. Reload with the platform shortcuts above. If theme-file changes are not picked
   up by an already-running instance, save terminal work and restart Kitty.
4. With one tab and one pane, expect neither tab bar nor internal title bar.
   Add a tab with `Ctrl+Shift+T` on Linux or `Cmd+Shift+T` on Mac: tabs appear at
   the top. Use `Ctrl+Tab` / `Ctrl+Shift+Tab` to switch.
5. Add a pane with `Ctrl+Shift+Enter` on Linux or `Cmd+Enter` on Mac. Expect
   pane titles only while two or more panes are visible. Close the extra pane
   with `exit` and confirm the remaining title disappears.
6. Switch the OS light/dark scheme with both tabs and panes present. Check active
   and inactive title contrast and resize the OS window to inspect residual
   right-edge gaps. Record a screenshot if unacceptable gaps remain.
7. In HM Kitty test `Super+,/E/N` from a known working directory: each creates
   the requested tab at home, not in the source directory. In a shell tab, `pwd`
   must print your home directory. Test `Super+]` / `Super+[` in EN/RU
   to switch next/previous tabs and `Super+Shift+[` / `Super+Shift+]` to reorder
   the current tab left/right without opening an OS window. Test Shift+comma/E/N in Kitty,
   another app and an empty workspace: exactly one new OS window should open,
   and Yazi must not ask for sudo. Repeat in EN/RU. Check `Super+Shift+R` still
   invokes Handy on Lenovo. On the independent Mac, apply the separate
   keyboard patch or its correction following [its guide](macos/README.md).
   Mac launch shortcuts deliberately differ: only unshifted app launches are
   enabled, using the original native/login-shell methods. Check recording,
   project launchers and dynamic opacity.
8. In a disposable Kitty tab, test `Super+W` in EN/RU: the whole tab closes,
   including any panes. Check `hypr-semantic-switcher-tofi` still works as a
   terminal command, and `Super+Space` still opens the canvas.
