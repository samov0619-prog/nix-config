{
  config,
  ...
}:
{
  wayland.windowManager.hyprland = {
    enable = true;
    systemd.enable = false;
    package = null;
    portalPackage = null;
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
}
