{ ... }:
{
  imports = [
    ../modules/alacritty
    ../modules/kitty
  ];

  programs.firefox.enable = true;
  programs.mpv.enable = true;
}
