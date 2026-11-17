{ lib, pkgs, ... }:
let
  # Match the MCP server pinned in Aina; install only its bundled Blender add-on.
  blenderMcpVersion = "2.3.0";
  blenderMcpWheel = pkgs.fetchurl {
    url = "https://files.pythonhosted.org/packages/d4/27/dff438e59b46bc93cebb2558c5e994c821227482d9a22d32814fdc388558/mcp_for_blender-${blenderMcpVersion}-py3-none-any.whl";
    hash = "sha256-1CD+U4KnIgFi2ajtPwdA+hnOg62H8wyJIki7fFJUthg=";
  };
  blenderMcpAddon =
    pkgs.runCommand "blender-mcp-addon-${blenderMcpVersion}"
      {
        nativeBuildInputs = [ pkgs.unzip ];
      }
      ''
        mkdir -p "$out"
        unzip -p ${blenderMcpWheel} blender_mcp/bundled/addon.py > "$out/blender_mcp.py"
      '';
  blenderConfigVersion = lib.versions.majorMinor pkgs.blender.version;
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
    ./handy
    ./command-keys
  ];

  # Keep the agreed raw configuration workflow on fresh HM 26.05 as well.
  wayland.windowManager.hyprland.configType = "hyprlang";
  # Only Lenovo uses this override; existing profiles retain stock Waybar.
  programs.waybar.package = import ./waybar/package.nix { waybar = pkgs.waybar; };
  # Manage one add-on, not the scripts directory or user preferences. No auto-enable.
  xdg.configFile."blender/${blenderConfigVersion}/scripts/addons/blender_mcp.py" = {
    source = "${blenderMcpAddon}/blender_mcp.py";
    force = false;
  };
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
    Super+Shift+R      Handy: start / stop dictation
    Super+Shift+T      Handy: cancel recording / recognition
  '';

  # Keep the apps, but do not activate an unprepared world/backup watcher.
  home.packages = with pkgs; [
    touchpad
    gpuMonitor
    freesmlauncher
    packwiz
    jdk_headless
  ];

}
