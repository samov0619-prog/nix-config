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
  select the next or previous enabled group; `H`, `J`, `K`, `L` stay within
  that group's grid.
- Regular workspaces with at least one window are global positive-integer
  anchors. Derived cards fill their numeric gaps, including the leading tail;
  each absent gap follows the preceding window-backed anchor (the leading range
  follows the first anchor), and cards never extend beyond the highest real ID
  `H`. Existing IDs keep their actual Hyprland monitor even when empty. Empty
  workspaces are ignored as anchors; special workspaces are excluded. One
  distinct `+` crown follows the selected monitor group and moves with `Tab`.
  An output without real workspaces shows its active empty workspace only as a
  crown. On outputs with real workspaces, empty IDs inside `1..H` remain regular
  gap cards, while the crown targets an empty head above `H` or the first
  globally unused ID. Empty heads never extend the numeric range.
  On empty-only outputs the active empty ID has priority over persistent empty
  IDs, independent of workspace enumeration order.
- Every slot is a scaled copy of the monitor work area. Layer-shell background
  and bottom-layer wallpaper surfaces are included; there is no fallback
  background renderer. Empty slots remain visible and can be selected; `Enter`
  switches to (and creates, if needed) the selected ID on the canvas monitor.
  Tiled geometry is preserved; floating windows remain above tiled windows.
- Previews are compositor-side live surfaces, not screenshots.
  Moves recalculate the moved workspace's layout even when it is not active.
  Preview placement uses final global window geometry relative to the owning
  output, including negative monitor origins and off-monitor floating windows.
  While open, every canvas output is fully redrawn at its own refresh cadence;
  closing the canvas stops this redraw loop.
- Every card has its numeric ID centred in the top header, including `+`.
  Activating `+` uses its current local head target, keeping focus on the
  selected monitor. Hyprland may rename or drop an empty head after a workspace
  switch; the next canvas rebuild reads that live state again rather than
  retaining the old ID.
- A fixed top-left outline on both single- and multi-output canvases lists real
  output names and their regular canvas
  cards. The selected output name is bold, the selected card is accent-coloured,
  and active workspaces use a heavier weight. Selecting `+` renders an
  accent-coloured `...` in place of its hidden target ID.
  Headers and outline typography follow each output's scale. Text textures use
  an LRU cache capped at 256 entries and approximately 16 MiB of RGBA pixels;
  closing the canvas clears it.
- When no workspace has a window, the canvas instead shows one active empty
  workspace per enabled monitor and no `+` card. `Enter` only focuses that
  monitor; it does not create or renumber a workspace.
- `H`, `J`, `K`, `L` move through the grid with horizontal and vertical wrap.
  Vertical moves keep their exact column but never cross a missing column between
  a short row and a long row, in either direction. This deliberately simple,
  experimental policy may be replaced by a smarter scheme. `Enter` commits
  focus and `Escape` closes.
- In a multi-output canvas, `Ctrl+Tab` and `Ctrl+Shift+Tab` move the selected
  existing workspace to the next or previous output in the same physical order
  as `Tab`. The canvas stays open and selects the moved card on its destination.
  This includes an empty crown when its target exists; the source is activated
  first so Hyprland preserves it. A virtual regular card is materialized on the
  target output via a normal workspace switch. A nonpersistent empty head may
  then disappear; an existing workspace with windows is retained. Synthetic
  crown targets cannot be moved. Selecting a real card alone does not activate
  it in Hyprland; its layout is updated on move without forcing activation.
- `Enter` activates the selected workspace and closes the canvas on key
  release. Pressing any other key (including a modifier), clicking or scrolling
  cancels the pending activation. Release Enter and press it again to activate
  the new selection; autorepeat cannot re-arm it. A changed selection/output or
  activation mode also cancels it. `Escape` closes without activating.
- `+`/`=` and mouse-wheel up zoom in; `-` and mouse-wheel down zoom out. The
  zoom level is preserved when `Tab` or `Shift+Tab` changes the selected output
  group.
  Touchpad scrolling, pinch, pointer selection, and dragging remain reserved
  for later handlers.
- Ctrl and Shift come from Hyprland's aggregated keyboard modifier state, not
  separately tracked key presses. Monitor hotplug repairs selection before
  rendering or dispatching input, preserving zoom.
- `F12` saves the current canvas output to `~/Screenshots/hypr-spaces-<timestamp>.png`.

Pseudotile tile frames, special-workspace cards, search, and pointer gestures
are planned, not implemented. The canvas has an opaque backdrop and swallows
keyboard and pointer input while it is open. It is loaded declaratively by the
Linux Hyprland module.

## Operation

The Linux Hyprland module builds the plugin and writes
`~/.config/hypr/hypr-spaces.conf`; both laptop and desktop Hyprland configs
source that file and bind `Super+Space` to `spaces:toggle`. Outside the canvas,
`Super+Tab` and `Super+Shift+Tab` focus the next or previous enabled output in
the same physical row-major order; adding `Ctrl` moves the focused workspace
instead. These bindings never name monitors.

After changing this plugin, activate the applicable Home Manager profile and
reload Hyprland:

```sh
home-manager switch --flake .#samov-laptop
# or: home-manager switch --flake .#samov-desktop
hyprctl reload
```

Do not use manual plugin unload/load as the routine update workflow.

## Foundations

One pure canvas model builds groups, crown and selection from a current
workspace/monitor snapshot for both single- and multi-output rendering.
Workspace existence, window presence and visual role are separate properties.

Pure C++ tests cover allocation, empty-head priority, Tab into empty groups,
empty/real move snapshots, virtual-card materialization, crown promotion,
hotplug fallback, no-window mode, and cancelled Enter activation. Exhaustive
small snapshots verify unique IDs, correct owners and enumeration-order
independence. Geometry tests cover global-to-preview placement, negative
origins, floating windows across output edges, and scales `1.0`, `1.25`, `2.0`.
They run in the Nix check phase without Hyprland. Actual compositor transfers,
damage scheduling, keyboard modifiers, DPI and rendering remain runtime checks;
see `TODO.md`.
