{ config, lib, ... }:
{
  options.programs.yazi.freeSpaceStatus.enable = lib.mkOption {
    type = lib.types.bool;
    default = true;
    description = "Show the legacy free-space status when no Waybar replacement is configured.";
  };

  config.programs.yazi.initLua = lib.mkIf config.programs.yazi.freeSpaceStatus.enable ''
    -- show disk in status bar
    Status:children_add(function()
        local command = "df -kh .|awk '!/^Filesystem/{printf \" %s FREE \", $(NF-2)}'"
        local info = ui.Span(io.popen(command):read('*a')):fg("green")
        return info
    end, 1500, Header.RIGHT)
  '';
}
