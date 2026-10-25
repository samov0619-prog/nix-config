-- Small atomic publisher shared by the optional Neovim and Yazi integrations.
-- Records are accepted only for a foreground PID with matching process starttime
-- and Kitty pane ID. A crashed application's leftover file cannot label a shell.
local M = {}

function M.new(app)
  local runtime, pane = os.getenv("XDG_RUNTIME_DIR"), os.getenv("KITTY_WINDOW_ID")
  if not runtime or not pane or not pane:match("^%d+$") then return end
  local stat = io.open("/proc/self/stat", "r")
  if not stat then return end
  local text = stat:read("*a")
  stat:close()
  local pid, tail = text:match("^(%d+) %(.+%) (.*)$")
  if not pid then return end
  local fields = {}
  for field in tail:gmatch("%S+") do fields[#fields + 1] = field end
  local start = fields[20]
  if not start then return end
  local directory = runtime .. "/hypr-spaces/apps"
  local path, previous = directory .. "/" .. pid .. ".json", nil
  local function quote(value)
    return '"' .. tostring(value):gsub('[%z\1-\31\\"]', function(c)
      return string.format("\\u%04x", string.byte(c))
    end) .. '"'
  end
  return {
    directory = directory,
    publish = function(cwd, title)
      if not cwd then return end
      local payload = '{"app":' .. quote(app) .. ',"pane":' .. quote(pane)
        .. ',"start":' .. quote(start) .. ',"cwd":' .. quote(cwd)
        .. ',"title":' .. quote(title or "") .. '}'
      if payload == previous then return end
      local file = io.open(path .. ".tmp", "w")
      if not file then return end
      local ok = file:write(payload)
      file:close()
      if ok and os.rename(path .. ".tmp", path) then previous = payload end
    end,
    close = function()
      os.remove(path)
      os.remove(path .. ".tmp")
    end,
  }
end

return M
