-- Swayimg configuration. The full Lua API reference ships with the package at
-- share/swayimg/swayimg.lua (example.lua shows all available hooks).

-- When a single image is opened, pull in every image from its directory so the
-- viewer can move between them (this is what the Yazi opener relies on).
swayimg.imagelist.adjacent = true
swayimg.imagelist.order = "numeric"

-- Switch images with Left/Right (PgUp/PgDn keep their default bindings).
swayimg.viewer.on_key("Left", function()
  swayimg.viewer.open("prev")
end)
swayimg.viewer.on_key("Right", function()
  swayimg.viewer.open("next")
end)

-- Ctrl+= / Ctrl+- also zoom (same step as +/-, centered).
swayimg.viewer.on_key("Ctrl+equal", function()
  swayimg.viewer.scale = swayimg.viewer.scale + swayimg.viewer.scale / 10
end)
swayimg.viewer.on_key("Ctrl+minus", function()
  swayimg.viewer.scale = swayimg.viewer.scale - swayimg.viewer.scale / 10
end)

-- Mouse wheel zooms around the pointer (no modifier, as before).
swayimg.viewer.on_mouse("ScrollUp", function()
  local mouse = swayimg.get_mouse_pos()
  local scale = swayimg.viewer.scale
  swayimg.viewer.set_abs_scale(scale + scale / 10, mouse.x, mouse.y)
end)
swayimg.viewer.on_mouse("ScrollDown", function()
  local mouse = swayimg.get_mouse_pos()
  local scale = swayimg.viewer.scale
  swayimg.viewer.set_abs_scale(scale - scale / 10, mouse.x, mouse.y)
end)

-- Drag to pan the image.
swayimg.viewer.drag_button = "MouseLeft"
