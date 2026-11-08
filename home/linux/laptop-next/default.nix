{ pkgs, ... }:
{
  imports = [
    ../core-set
    ../gui-set
    ../../modules/voice-dictate
  ];

  # Keep the agreed raw configuration workflow on fresh HM 26.05 as well.
  wayland.windowManager.hyprland.configType = "hyprlang";
  xdg.configFile."hypr/hyprland.conf".source = ./hyprland.conf;
  xdg.configFile."waybar/config.jsonc".source = ./waybar-config.jsonc;

  # Keep the apps, but do not activate an unprepared world/backup watcher.
  home.packages = with pkgs; [
    freesmlauncher
    packwiz
    jdk_headless
  ];

  # No xremap/keycap remapping on Lenovo. Voice remains available on CPU until
  # target GPU enumeration establishes a backend; never inherit Acer's -dev 1.
}
