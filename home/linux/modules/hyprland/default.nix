{
  lib,
  config,
  pkgs,
  ...
}:
let
  hyprSpaces = pkgs.callPackage ../../../../pkgs/hypr-spaces { };
  onionbell = pkgs.callPackage ../../../../pkgs/onionbell { };
  # With package = null, NixOS supplies pkgs.hyprland from the same flake input.
  hyprlandPackage =
    if config.wayland.windowManager.hyprland.package == null then
      pkgs.hyprland
    else
      config.wayland.windowManager.hyprland.package;
  # Upstream #15502 adds libcanberra for native bell playback. Inspect package
  # dependencies instead of guessing the first release version; catches backports.
  hyprlandHasNativeBell = lib.any (
    dependency: lib.getName dependency == "libcanberra"
  ) (hyprlandPackage.buildInputs or [ ]);
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
  warnings = lib.optional hyprlandHasNativeBell ''
    ONIONBELL CLEANUP: Hyprland ${hyprlandPackage.version} now has libcanberra,
    the native system bell backend added by https://github.com/hyprwm/Hyprland/pull/15502.
    After applying the NixOS update and starting a new Hyprland session, stop
    onionbell with `systemctl --user stop onionbell.service` and test `printf '\a'` in Kitty.
    If native sound works, remove onionbell from home.packages, its xdg.configFile
    and systemd.user.services entries, this check, and pkgs/onionbell; then apply
    Home Manager. Otherwise restart onionbell.service while investigating.
  '';

  home.packages = [
    semanticSwitcher
    semanticSwitcherTofi
    onionbell
  ];

  # Hyprland 0.55/0.56 publishes system bell events without playing a sound.
  # Use an upstream event listener for all xdg-system-bell-v1 clients.
  xdg.configFile."onionbell/config.toml".source = (pkgs.formats.toml { }).generate "onionbell.toml" {
    sound = "${pkgs.sound-theme-freedesktop}/share/sounds/freedesktop/stereo/bell.oga";
  };

  systemd.user.services.onionbell = {
    Unit = {
      Description = "Hyprland system bell audio";
      PartOf = [ "graphical-session.target" ];
      After = [
        "graphical-session.target"
        "pipewire.service"
        "wireplumber.service"
      ];
      ConditionEnvironment = "HYPRLAND_INSTANCE_SIGNATURE";
    };
    Service = {
      ExecStart = lib.getExe onionbell;
      Restart = "on-failure";
      RestartSec = 2;
    };
    Install.WantedBy = [ "graphical-session.target" ];
  };

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

  home.file."Screenshots/.keep".text = "";

  xdg.configFile."swappy/config".text = ''
    [Default]
    save_dir=${config.home.homeDirectory}/Screenshots
  '';

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
