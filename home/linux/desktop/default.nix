{ ... }:
{
  imports = [
    ../core-set
    ../gui-set
  ];
  xdg.configFile."hypr/hyprland.conf".source = ./hyprland.conf;
  xdg.configFile."waybar/config.jsonc".source = ./waybar-config.jsonc;
}
