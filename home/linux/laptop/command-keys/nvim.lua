-- Installed as a site plugin; the manually maintained Neovim repo stays untouched.
local function map(mode, key, rhs, desc)
  vim.keymap.set(mode, key, rhs, { silent = true, desc = desc })
end
for _, pair in ipairs({ { 'c', 'с' }, { 'v', 'м' }, { 'x', 'ч' }, { 'a', 'ф' }, { 'z', 'я' } }) do
  for _, key in ipairs(pair) do
    local chord = '<D-' .. key .. '>'
    if pair[1] == 'c' then
      map('n', chord, '"+yy', 'Command: copy line')
      map('x', chord, '"+y', 'Command: copy selection')
    elseif pair[1] == 'x' then
      map('n', chord, '"+dd', 'Command: cut line')
      map('x', chord, '"+d', 'Command: cut selection')
    elseif pair[1] == 'v' then
      map('n', chord, '"+p', 'Command: paste')
      map('x', chord, '"+P', 'Command: replace selection')
      map('i', chord, '<C-r><C-o>+', 'Command: paste')
      map('c', chord, '<C-r>+', 'Command: paste')
      map('t', chord, function() vim.api.nvim_paste(vim.fn.getreg('+'), true, -1) end, 'Command: terminal paste')
    elseif pair[1] == 'a' then
      map({ 'n', 'x' }, chord, '<Esc>ggVG', 'Command: select buffer')
      map('i', chord, '<Esc>ggVG', 'Command: select buffer')
    elseif pair[1] == 'z' then
      map({ 'n', 'x' }, chord, '<Esc>u', 'Command: undo')
      map('i', chord, '<C-g>u<C-o>u', 'Command: undo')
    end
  end
end
for _, key in ipairs({ 'z', 'я' }) do
  map({ 'n', 'x' }, '<D-S-' .. key .. '>', '<Esc><C-r>', 'Command: redo')
  map('i', '<D-S-' .. key .. '>', '<C-g>u<C-o><C-r>', 'Command: redo')
end
