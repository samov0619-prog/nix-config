{ ... }:
{
  imports = [
    ../core-set
    ../gui-set
    ../../modules/voice-dictate
  ];
  xdg.configFile."hypr/hyprland.conf".source = ./hyprland.conf;
  xdg.configFile."waybar/config.jsonc".source = ./waybar-config.jsonc;
}
