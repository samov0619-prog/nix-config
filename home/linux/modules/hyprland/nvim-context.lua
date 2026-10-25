-- Standard site runtime plugin: the user's Neovim configuration stays independent.
local ok, publisher = pcall(function() return dofile("@publisher@").new("nvim") end)
if not ok or not publisher then return end
vim.fn.mkdir(publisher.directory, "p", 448) -- 0700
local function publish()
  if #vim.api.nvim_list_uis() == 0 then return end -- headless tools are not the visible pane
  pcall(publisher.publish, vim.fn.getcwd()) -- effective window/tab-local CWD
end
local group = vim.api.nvim_create_augroup("HyprSpacesContext", { clear = true })
vim.api.nvim_create_autocmd({ "VimEnter", "DirChanged", "WinEnter", "TabEnter", "FocusGained" }, {
  group = group, callback = publish,
})
vim.api.nvim_create_autocmd("VimLeavePre", { group = group, callback = publisher.close })
vim.schedule(publish)
