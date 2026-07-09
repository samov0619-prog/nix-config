{ lib, config, ... }:
{
  imports = [
    ../modules/alacritty
    ../modules/kitty
  ];

  programs.firefox = {
    enable = true;
    configPath = lib.mkIf (lib.versionOlder config.home.stateVersion "26.05") ".mozilla/firefox";
  };
  programs.mpv.enable = true;
}
