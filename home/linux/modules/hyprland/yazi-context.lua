local ok, publisher = pcall(function() return dofile("@publisher@").new("yazi") end)
if not ok or not publisher then return end
ya.async(function()
  fs.create("dir_all", Url(publisher.directory))
end)
-- Runs for the active tab on redraw, including tab switches that do not emit
-- `cd`. The publisher writes only on a changed path, never on cursor movement.
Status:children_add(function()
  pcall(publisher.publish, tostring(cx.active.current.cwd))
  return ui.Span("")
end, 9999, Header.RIGHT)
