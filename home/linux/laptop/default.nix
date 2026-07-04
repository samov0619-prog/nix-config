{
  ...
}:
{
  imports = [
    ../core-set
    ../gui-set
  ];

  programs.alacritty.settings.font.size = 11;
  xdg.configFile."hypr/hyprland.conf".source = ./hyprland.conf;
}
