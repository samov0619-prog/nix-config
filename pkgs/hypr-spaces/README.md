# hypr-spaces

`hypr-spaces` is a local Hyprland plugin for this flake. It is deliberately
built against the exact Hyprland package selected by nixpkgs, rather than a
separate upstream flake or `hyprpm` runtime build.

## Product contract

- `Super+Space` opens a fit-all canvas of regular workspaces on the current
  monitor.
- Every workspace is a scaled copy of its real work area. Tiled geometry is
  preserved; floating windows remain above tiled windows.
- A pseudotiled window keeps its visible fixed size and also shows a muted tile
  slot frame.
- `special:magic` is represented separately from numbered workspaces.
- Previews are compositor-side live surfaces, not screenshots.
- Search highlights matching workspace numbers, window titles, classes,
  foreground terminal processes, and working directories without rebuilding
  the canvas.
- `H`, `J`, `K`, `L` select the nearest preview in that direction. `Enter`
  commits focus, `Escape` closes, `Space` restores fit-all, and wheel/`+`/`-`
  zoom around the selection.

The first MVP renders a live, scaled active workspace with opaque backdrop and
swallows keyboard/pointer input until Escape closes it. It is loaded
declaratively by the Linux Hyprland module.
