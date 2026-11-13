-- Exercise the installed site plugin without loading personal plugins or clipboard.
local source = assert(arg[1], 'plugin path required')
dofile(source)
local function press(key)
  vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes(key, true, false, true), 'xt', false)
end
vim.bo.undolevels = -1
vim.api.nvim_buf_set_lines(0, 0, -1, false, { 'alpha', 'beta' })
vim.bo.undolevels = 1000
vim.cmd('normal! ggA!')
press('<D-z>')
assert(vim.api.nvim_get_current_line() == 'alpha', 'Command undo')
press('<D-S-z>')
assert(vim.api.nvim_get_current_line() == 'alpha!', 'Command redo')
press('<D-a>')
assert(vim.fn.mode() == 'V', 'Command select buffer')
assert(vim.fn.line('v') == 1 and vim.fn.line('.') == 2, 'whole-buffer selection')
press('<Esc>')
for _, mode in ipairs({ 'n', 'x', 'i' }) do
  assert(vim.fn.maparg('<D-z>', mode) ~= '', 'missing native undo')
end
assert(vim.fn.maparg('<C-z>', 'n') == '', 'Ctrl-Z must stay untouched')
assert(vim.fn.maparg('<D-z>', 't') == '', 'no undo guessing in nested terminals')
print('Neovim actual mappings: undo/redo/select pass; clipboard/UI not tested')
vim.cmd('qa!')
