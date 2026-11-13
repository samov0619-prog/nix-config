{
  pkgs,
  lib,
  xremap-flake,
  ...
}:
let
  bridge = xremap-flake.packages.${pkgs.stdenv.hostPlatform.system}.xremap-hypr;
  binding = key: run: {
    on = key;
    inherit run;
  };
  esc = builtins.fromJSON ''"\u001b"'';
in
{
  systemd.user.services.lenovo-xremap-bridge = {
    Unit = {
      Description = "Window context for isolated Lenovo xremap (no evdev access)";
      PartOf = [ "graphical-session.target" ];
      After = [ "graphical-session.target" ];
      ConditionEnvironment = "HYPRLAND_INSTANCE_SIGNATURE";
    };
    Service = {
      ExecStart = "${lib.getExe bridge} --bridge --desktop=hypr --allow-launch=false --no-window-logging";
      Restart = "on-failure";
      RestartSec = 2;
      NoNewPrivileges = true;
      Environment = "RUST_LOG=warn";
    };
    Install.WantedBy = [ "graphical-session.target" ];
  };
  xdg.configFile."kitty/command_keys.py".source = ./kitty_keys.py;
  programs.kittyExtraConfig =
    lib.concatMapStringsSep "\n"
      (key: "map --allow-fallback=ascii super+${key} kitten command_keys.py ${key}")
      [
        "c"
        "v"
        "x"
        "a"
        "z"
        "shift+z"
      ];
  # Alacritty has no Kitty kitten/foreground router: clipboard stays terminal-native.
  programs.alacritty.settings.keyboard.bindings = [
    {
      key = "C";
      mods = "Super";
      action = "Copy";
    }
    {
      key = "V";
      mods = "Super";
      action = "Paste";
    }
    {
      key = "X";
      mods = "Super";
      chars = "${esc}[120;9u";
    }
    {
      key = "A";
      mods = "Super";
      chars = "${esc}[97;9u";
    }
    {
      key = "Z";
      mods = "Super";
      chars = "${esc}[122;9u";
    }
    {
      key = "Z";
      mods = "Super|Shift";
      chars = "${esc}[122;10u";
    }
  ];
  programs.fish.interactiveShellInit = lib.mkAfter (builtins.readFile ./fish.fish);
  xdg.dataFile."nvim/site/plugin/lenovo-command-keys.lua".source = ./nvim.lua;
  programs.yazi.keymap = {
    mgr.prepend_keymap = [
      (binding "<D-c>" "yank")
      (binding "<D-x>" "yank --cut")
      (binding "<D-v>" "paste")
      (binding "<D-a>" "toggle_all --state=on")
    ];
    input.prepend_keymap = [
      (binding "<D-c>" "yank")
      (binding "<D-x>" "delete --cut")
      (binding "<D-v>" "paste")
      (binding "<D-a>" [
        "move bol"
        "visual"
        "move eol"
      ])
      (binding "<D-z>" "undo")
      (binding "<D-S-z>" "redo")
    ];
  };
  programs.tofi.controls.shortcuts = lib.mkAfter ''
    Left Alt           Command/Super; left Windows key becomes Alt
    Super+C/V/X/A      copy / paste / cut / select all (app-specific)
    Super+Z/Shift+Z    undo / redo (no filesystem undo in Yazi)
  '';
}
