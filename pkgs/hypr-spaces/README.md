# hypr-spaces

`hypr-spaces` is a local Hyprland plugin for this flake. It is deliberately
built against the exact Hyprland package selected by nixpkgs, rather than a
separate upstream flake or `hyprpm` runtime build.

## Product contract

- `Super+Space` opens a canvas. With one output it shows that output's numeric
  slots; with multiple outputs it renders one shared logical canvas on every
  output. The output below the pointer selects the initial monitor group. That
  group is centred initially, while adjacent group edges remain visible.
- Multi-output groups follow physical row-major order: vertically overlapping
  outputs form a row and each row sorts left to right. `Tab` and `Shift+Tab`
  select the next or previous non-empty group; `H`, `J`, `K`, `L` stay within
  that group's grid.
- Regular workspaces are global positive-integer anchors. Derived cards fill
  their numeric gaps, including the leading tail, and one distinct `+` creation
  card follows the highest real workspace. Special workspaces are excluded.
- Every slot is a scaled copy of the monitor work area. Layer-shell background
  and bottom-layer wallpaper surfaces are included; there is no fallback
  background renderer. Empty slots remain visible and can be selected; `Enter`
  switches to (and creates, if needed) the selected ID on the canvas monitor.
  Tiled geometry is preserved; floating windows remain above tiled windows.
- Previews are compositor-side live surfaces, not screenshots.
- Every card has a centred numeric title at its top edge. The `+` card creates
  the next numeric workspace when activated.
- `H`, `J`, `K`, `L` move through the grid with horizontal and vertical wrap.
  Vertical moves keep their exact column but never cross a missing column between
  a short row and a long row, in either direction. This deliberately simple,
  experimental policy may be replaced by a smarter scheme. `Enter` commits
  focus and `Escape` closes.
- `Enter` activates the selected workspace and closes the canvas on key
  release intentionally. This experimental input policy is retained to compare
  with press activation later; `Escape` closes without activating.
- `+`/`=` and mouse-wheel up zoom in; `-` and mouse-wheel down zoom out.
  Touchpad scrolling, pinch, pointer selection, and dragging remain reserved
  for later handlers.
- `F12` saves the current canvas output to `~/Screenshots/hypr-spaces-<timestamp>.png`.

Pseudotile tile frames, special-workspace cards, search, and pointer gestures
are planned, not implemented. The canvas has an opaque backdrop and swallows
keyboard and pointer input while it is open. It is loaded declaratively by the
Linux Hyprland module.

## Operation

The Linux Hyprland module builds the plugin and writes
`~/.config/hypr/hypr-spaces.conf`; both laptop and desktop Hyprland configs
source that file and bind `Super+Space` to `spaces:toggle`.

After changing this plugin, activate the applicable Home Manager profile and
reload Hyprland:

```sh
home-manager switch --flake .#samov-laptop
# or: home-manager switch --flake .#samov-desktop
hyprctl reload
```

Do not use manual plugin unload/load as the routine update workflow.

## Foundations

Pure C++ tests cover global workspace allocation, physical monitor row
ordering, and target physical-to-logical preview geometry at scales `1.0`,
`1.25`, and `2.0`. They run in the Nix check phase without Hyprland. Visual
verification of real multi-output layouts, rotation, and full interaction
remains manual; see `TODO.md`.
