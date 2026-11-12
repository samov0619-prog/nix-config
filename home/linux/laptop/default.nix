{ pkgs, ... }:
let
  gpuStatus = pkgs.writeShellScriptBin "waybar-gpu-status" ''
    exec ${pkgs.python3}/bin/python3 ${./waybar/gpu-status.py} "$@"
  '';
  touchpad = pkgs.writeShellScriptBin "lenovo-touchpad" ''
    exec ${pkgs.python3}/bin/python3 ${./touchpad.py} --hyprctl ${pkgs.hyprland}/bin/hyprctl "$@"
  '';
  gpuMonitor = pkgs.writeShellScriptBin "gpu-monitor" ''
    exec ${pkgs.python3}/bin/python3 ${./gpu-monitor.py} "$@"
  '';
  waybarTheme =
    variant:
    pkgs.writeText "lenovo-waybar-${variant}.css" (
      # Inline the shared import so this generated store file has no relative URL.
      builtins.replaceStrings
        [ ''@import url("./style.css");'' ]
        [ (builtins.readFile ../modules/waybar/style.css) ]
        (builtins.readFile (../modules/waybar + "/style-${variant}.css"))
      + builtins.readFile (./waybar + "/palette-${variant}.css")
      + builtins.readFile ./waybar/appearance.css
    );
in
{
  imports = [
    ../core-set
    ../gui-set
    ../../modules/voice-dictate
  ];

  # Keep the agreed raw configuration workflow on fresh HM 26.05 as well.
  wayland.windowManager.hyprland.configType = "hyprlang";
  # Only Lenovo uses this override; existing profiles retain stock Waybar.
  programs.waybar.package = import ./waybar/package.nix { waybar = pkgs.waybar; };
  xdg.configFile."hypr/hyprland.conf".source = ./hyprland.conf;
  xdg.configFile."waybar/config.jsonc".source = ./waybar-config.jsonc;
  xdg.configFile."waybar/style-dark.css".source = waybarTheme "dark";
  xdg.configFile."waybar/style-light.css".source = waybarTheme "light";
  xdg.configFile."waybar/scripts/gpu-status".source = "${gpuStatus}/bin/waybar-gpu-status";

  programs.tofi.controls.shortcuts = ''
    Fn+F1              this help
    F8 (touchpad)      toggle touchpad (enabled again on config reload)
    F9 (star)          agent todo in Neovim
    F10                select screenshot region, edit in Swappy
    Fn+F11             toggle light/dark theme
    Super+Shift+LMB    resize floating window / tiled split
    Super+Ctrl+T       current Dwindle split 50/50 (not whole layout)
  '';

  # Keep the apps, but do not activate an unprepared world/backup watcher.
  home.packages = with pkgs; [
    touchpad
    gpuMonitor
    freesmlauncher
    packwiz
    jdk_headless
  ];

  # No xremap/keycap remapping on Lenovo. Voice remains available on CPU until
  # target GPU enumeration establishes a backend; never inherit Acer's -dev 1.
}
