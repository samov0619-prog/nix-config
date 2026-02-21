{ pkgs, ... }:
{
  imports = [
    ./xdg.nix
    ./security.nix
    ../modules/filemanager1-common
    ../modules/hyprland
    ../modules/tofi
    ../modules/waybar
  ];
  home.packages = with pkgs; [
    rose-pine-hyprcursor
    grim
    slurp
    swappy
    pwvucontrol
    ardour
    audacious
    wl-clipboard
  ];

  qt = {
    enable = true;
    platformTheme.name = "adwaita";
  };

  services.easyeffects.enable = true;
  services.udiskie = {
    enable = true;
    settings = {
      menu = "nested";
    };
  };
  services.mako.enable = true;
  services.filemanager1-common = {
    enable = true;
    # fileManager = "yazi"; # или ranger/nnn/lf/custom
    # если custom: wrapperScript = "/home/samov/.local/bin/my-wrapper.sh";
    # terminalCommand при необходимости переопредели
  };
}
