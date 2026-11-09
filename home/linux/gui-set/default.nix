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
    ../modules/nomacs
    ../modules/qt-theme
    ../modules/ardour
    ../modules/tofi
    ../modules/waybar
  ];
  home.packages = with pkgs; [
    rose-pine-hyprcursor
    # GTK3's built-in dark variant needs this named Adwaita-dark alias.
    # Without it gtk-theme=Adwaita-dark silently falls back to light Adwaita.
    gnome-themes-extra
    grim
    slurp
    swappy
    pwvucontrol
    audacious
    playerctl
    wl-clipboard
    freefilesync
    qbittorrent
    libnotify
  ];

  # Existing media keys use playerctl/MPRIS; mpv needs this interface explicitly.
  programs.mpv.scripts = [ pkgs.mpvScripts.mpris ];

  # EasyEffects adds PipeWire effects (e.g. EQ/noise reduction), not basic audio.
  # Disabled until a specific effect is needed and configured deliberately.
  # services.easyeffects.enable = true;
  services.udiskie = {
    enable = true;
    settings.program_options.menu = "smart";
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
