-- Run: nvim --headless -u NONE -l home/linux/modules/hyprland/tests/workspace-context.lua
local root = vim.fn.getcwd() .. "/home/linux/modules/hyprland/"
local temporary = vim.fn.tempname()
vim.fn.mkdir(temporary, "p", 448)
vim.env.XDG_RUNTIME_DIR = temporary
vim.env.KITTY_WINDOW_ID = "42"
local path = temporary .. "/hypr-spaces/apps/" .. vim.fn.getpid() .. ".json"
local function record()
  return vim.json.decode(table.concat(vim.fn.readfile(path), "\n"))
end
local function source(name)
  local text = table.concat(vim.fn.readfile(root .. name), "\n")
  text = text:gsub("@publisher@", function() return root .. "app-context.lua" end)
  assert(loadstring(text, "@" .. name))()
end
local function run()
  local listUIs = vim.api.nvim_list_uis
  vim.api.nvim_list_uis = function() return { {} } end
  source("nvim-context.lua")
  vim.wait(20)
  local initial = record()
  assert(initial.app == "nvim" and initial.pane == "42" and initial.start:match("^%d+$"))
  assert(initial.cwd == vim.fn.getcwd())
  vim.cmd("lcd " .. vim.fn.fnameescape(temporary))
  assert(record().cwd == temporary)
  vim.cmd("tabnew")
  vim.cmd("tcd /tmp")
  assert(record().cwd == "/tmp")
  vim.cmd("tabprevious")
  assert(record().cwd == temporary) -- Return to the window-local CWD.
  vim.api.nvim_list_uis = listUIs
  vim.api.nvim_exec_autocmds("VimLeavePre", { group = "HyprSpacesContext" })
  assert(vim.fn.filereadable(path) == 0)
  vim.api.nvim_del_augroup_by_name("HyprSpacesContext")

  local redraw
  _G.ya = { async = function(callback) callback() end }
  _G.fs = { create = function(_, directory) vim.fn.mkdir(directory, "p", 448) end }
  _G.Url = function(value) return value end
  _G.Header = { RIGHT = 1 }
  _G.Status = { children_add = function(_, callback) redraw = callback end }
  _G.ui = { Span = function(value) return value end }
  _G.cx = { active = { current = { cwd = "/some/active directory/кириллица" } } }
  source("yazi-context.lua")
  redraw()
  assert(record().app == "yazi" and record().cwd == cx.active.current.cwd)
  cx.active = { current = { cwd = "/different/tab" } }
  redraw() -- Switching tabs without a `cd` event must update the title.
  assert(record().cwd == "/different/tab")
  cx.active.current.cwd = '/path/with "quotes"\nand newline'
  redraw()
  assert(record().cwd == cx.active.current.cwd)
end
local ok, err = pcall(run)
vim.fn.delete(temporary, "rf")
if not ok then error(err) end
print("Neovim local CWD, Yazi active tab and publisher lifecycle: passed")
vim.cmd("qa!")
