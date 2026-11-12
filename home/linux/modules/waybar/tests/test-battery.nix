# Shared GUI timing and actual wrapper recipe; no build, live battery or audio access.
let
  f = builtins.getFlake (toString ../../../../..);
  lib = f.inputs.nixpkgs.lib;
  key = "waybar/scripts/battery-notify";
  fixture = import ../default.nix {
    config = { };
    inherit lib;
    pkgs = {
      bash = "/fixture/bash";
      libnotify = "/fixture/notify";
      pipewire = "/fixture/pipewire";
      sound-theme-freedesktop = "/fixture/sounds";
      callPackage =
        path: args:
        assert path == ../../notifications/package.nix;
        assert args == { };
        "/fixture/close";
      writeShellScriptBin =
        name: text:
        assert name == "waybar-battery-notify";
        assert lib.hasInfix (builtins.unsafeDiscardStringContext "${../scripts/battery-notify.sh}") text;
        assert lib.hasInfix "/fixture/notify/bin/notify-send" text;
        assert lib.hasInfix "/fixture/pipewire/bin/pw-play" text;
        assert lib.hasInfix "/fixture/sounds/share/sounds/freedesktop/stereo/dialog-warning.oga" text;
        assert lib.hasInfix "/fixture/close/bin/notification-close" text;
        assert lib.hasInfix ''"$@"'' text;
        "/fixture/${name}";
    };
  };
  check =
    host:
    let
      cfg = f.homeConfigurations."samov-${host}".config;
      bar = builtins.readFile cfg.xdg.configFile."waybar/config.jsonc".source;
    in
    assert cfg.services.mako.settings.default-timeout == 15000;
    assert (cfg.services.mako.settings.ignore-timeout or false) == false;
    assert builtins.elem "notification-close" (map lib.getName cfg.home.packages);
    assert cfg.xdg.configFile ? ${key};
    assert
      host == "desktop"
      || (lib.all (event: lib.hasInfix event bar) [
        ''"on-discharging-warning": "~/.config/waybar/scripts/battery-notify warning"''
        ''"on-discharging-critical": "~/.config/waybar/scripts/battery-notify critical"''
        ''"on-charging-critical": "~/.config/waybar/scripts/battery-notify clear"''
        ''"on-charging-warning": "~/.config/waybar/scripts/battery-notify clear"''
        ''"on-charging-normal": "~/.config/waybar/scripts/battery-notify clear"''
        ''"on-charging-full": "~/.config/waybar/scripts/battery-notify full"''
        ''"normal": 99, "full": 100''
        (if host == "laptop" then ''"warning": 15, "critical": 2'' else ''"warning": 30, "critical": 15'')
      ]);
    true;
in
assert
  fixture.xdg.configFile.${key}.source == "/fixture/waybar-battery-notify/bin/waybar-battery-notify";
assert lib.all check [
  "laptop"
  "laptop-old"
  "desktop"
];
assert lib.all (name: !f.homeConfigurations.${name}.config.services.mako.enable) [
  "samov-mac"
  "samov-server"
];
{
  sharedGuiFifteenSecondDefault = true;
  explicitApplicationTimeoutsPreserved = true;
  nativeBatteryEventsCoverAllChargingLevels = true;
  existingHostBatteryThresholdsPreserved = true;
  noNewMacOrServerNotificationDaemon = true;
}
