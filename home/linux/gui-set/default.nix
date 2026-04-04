{
  pkgs,
  lib,
  config,
  ...
}:
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
    dragon-drop
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

  home.sessionVariables = {
    NIX_FLAKE = "${config.home.homeDirectory}/nix-config";
  };

  programs.yazi.keymap.mgr.prepend_keymap = lib.mkAfter [
    {
      on = [ "<c-n>" ];
      run = "shell -- dragon-drop -x -i -T %h";
      desc = "Dragon-drop";
    }
  ];

  services.pass-secret-service.enable = true;
}
