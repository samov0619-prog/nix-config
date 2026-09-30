{
  lib,
  config,
  pkgs,
  ...
}:
let
  hyprSpaces = pkgs.callPackage ../../../../pkgs/hypr-spaces { };
  semanticSwitcher = pkgs.writeShellApplication {
    name = "hypr-semantic-switcher";
    runtimeInputs = [ pkgs.hyprland pkgs.python3 ];
    text = ''
      exec python3 ${./semantic-switcher.py} "$@"
    '';
  };
  semanticSwitcherTofi = pkgs.writeShellApplication {
    name = "hypr-semantic-switcher-tofi";
    runtimeInputs = [ pkgs.tofi semanticSwitcher ];
    text = ''
      selection=$(hypr-semantic-switcher menu | tofi --prompt-text="Switch: ") || exit 0
      exec hypr-semantic-switcher activate "$selection"
    '';
  };
in
{
  home.packages = [ semanticSwitcher semanticSwitcherTofi ];

  wayland.windowManager.hyprland = {
    enable = true;
    systemd.enable = false;
    package = null;
    portalPackage = null;
    configType = lib.mkIf (lib.versionOlder config.home.stateVersion "26.05") "hyprlang";
  };

  services.hyprpaper = {
    enable = true;
    settings = {
      splash = false;
      wallpaper = {
        monitor = "*";
        path = "${pkgs.hyprland}/share/hypr/wall2.png";
      };
    };
  };

  xdg.configFile."uwsm/env".source =
    "${config.home.sessionVariablesPackage}/etc/profile.d/hm-session-vars.sh";

  xdg.configFile."uwsm/env.d/theme.sh" = {
    text = ''
      # Source theme toggle variables if they exist
      [ -f "$XDG_CONFIG_HOME/uwsm/env-toggle" ] && . "$XDG_CONFIG_HOME/uwsm/env-toggle"
    '';
  };

  xdg.configFile."hypr/scripts/toggle-theme.sh" = {
    source = ./scripts/toggle-theme.sh;
    executable = true;
  };

  xdg.configFile."hypr/hypr-spaces.conf".text = ''
    plugin = ${hyprSpaces}/lib/libhypr-spaces.so
  '';

  xdg.configFile."hypr/scripts/terminal-layout-en.sh" = {
    source = ./scripts/terminal-layout-en.sh;
    executable = true;
  };
}
