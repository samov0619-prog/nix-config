# hypr-spaces TODO

## Workspace UI

- Render readable workspace number labels, optionally as card headers.
- Render one distinct `+` crown card after the global maximum real workspace.
  It must never appear inside a numeric gap or once per monitor.
- Decide whether `Enter` should keep its current release activation or move to
  press activation after comparing both workflows.
- Add search when the numeric canvas has enough cards to require it.

## Pointer And Touch

- Add pointer hover and click selection without leaking pointer input to
  Hyprland while the canvas is open.
- Add drag-and-drop for real workspace cards. Dragging changes their monitor
  owner; it must never renumber real IDs. Recompute virtual allocations after
  the drop.
- Add touchpad two-finger pan and pinch zoom. Wheel zoom is intentionally kept
  separate from these future gesture handlers.

## Multi-Output Verification

- Visually verify the shared canvas on physical outputs and a fake output with
  different scales. Check window positions, floating order, wallpaper layers,
  `Tab`/`Shift+Tab`, and workspace activation.
- Test physical output arrangements beyond one horizontal row: vertical stacks,
  staggered/transitively overlapping rows, gaps, and mixed monitor sizes.
- Test source and target output transforms with rotated or flipped outputs.
- Tune group sizing and camera framing only after the above visual checks; the
  selected group should remain close to the single-monitor card size while
  neighbouring group edges stay visible.

## Later Canvas Scope

- Evaluate pseudotile tile frames.
- Decide whether special workspaces should remain excluded or gain dedicated
  non-numeric cards.
