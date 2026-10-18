{
  pkgs,
  config,
  ...
}:
{
  imports = [
    ./xdg.nix
    ./security.nix
    ../modules/filemanager1-common
    ../modules/hyprland
    ../modules/swayimg
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
    freefilesync
    qbittorrent
    libnotify
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
  services.mako = {
    enable = true;
    settings.default-timeout = 60000;
  };
  services.filemanager1-common = {
    enable = true;
    # fileManager = "yazi"; # или ranger/nnn/lf/custom
    # если custom: wrapperScript = "/home/samov/.local/bin/my-wrapper.sh";
    # terminalCommand при необходимости переопредели
  };

  home.sessionVariables = {
    NIX_FLAKE = "${config.home.homeDirectory}/nix-config";
  };

  services.pass-secret-service.enable = true;
}
