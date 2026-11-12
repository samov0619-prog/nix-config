{
  config,
  lib,
  pkgs,
  ...
}:
let
  closeNotification = pkgs.callPackage ../notifications/package.nix { };
  batteryNotify = pkgs.writeShellScriptBin "waybar-battery-notify" ''
    exec ${pkgs.bash}/bin/bash ${./scripts/battery-notify.sh} \
      ${pkgs.libnotify}/bin/notify-send \
      ${pkgs.pipewire}/bin/pw-play \
      ${pkgs.sound-theme-freedesktop}/share/sounds/freedesktop/stereo/dialog-warning.oga \
      ${closeNotification}/bin/notification-close "$@"
  '';
  diskStatus = pkgs.writeShellScriptBin "waybar-disk-status" ''
    exec ${pkgs.python3}/bin/python3 ${./scripts/disk-status.py} \
      --path ${lib.escapeShellArg config.home.homeDirectory}
  '';
in
{
  # These GUI profiles receive the replacement at the same time as this opt-out.
  programs.yazi.freeSpaceStatus.enable = false;

  programs.waybar = {
    enable = true;
  };

  xdg.configFile = {
    "waybar/style-dark.css".source = ./style-dark.css;
    "waybar/style-light.css".source = ./style-light.css;
    "waybar/style.css".source = ./style.css;
    "waybar/scripts/disk-status".source = "${diskStatus}/bin/waybar-disk-status";
    "waybar/scripts/battery-notify".source = "${batteryNotify}/bin/waybar-battery-notify";

    "waybar/scripts/gp.sh" = {
      source = ./scripts/gp.sh;
      executable = true;
    };
    "waybar/scripts/startup-time.sh" = {
      source = ./scripts/startup-time.sh;
      executable = true;
    };
    "waybar/scripts/check-nix-updates.sh" = {
      source = ./scripts/check-nix-updates.sh;
      executable = true;
    };
    "waybar/scripts/nix-updates-view.sh" = {
      source = ./scripts/nix-updates-view.sh;
      executable = true;
    };
  };
}
