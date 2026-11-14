{ flake }:
let
  c = flake.nixosConfigurations.laptop.config;
  h = flake.homeConfigurations.samov-laptop.config;
  rules = import ./rules.nix;
  s = c.systemd.services.lenovo-xremap.serviceConfig;
  b = h.systemd.user.services.lenovo-xremap-bridge.Service;
  lib = flake.inputs.nixpkgs.lib;
  bar = builtins.readFile ../hyprland.conf;
  gui = builtins.head rules.keymap;
  find = builtins.elemAt rules.keymap 1;
  checks = {
    isolatedUser = s.User == "lenovo-xremap" && s.User != "root";
    noRawUserGroups =
      !(lib.any (
        g:
        builtins.elem g [
          "input"
          "uinput"
          "lenovo-keyboard"
        ]
      ) c.users.users.samov.extraGroups);
    daemonDoesNotHaveInputGroup = !(builtins.elem "input" s.SupplementaryGroups);
    noRootCapabilities = s.CapabilityBoundingSet == "" && s.NoNewPrivileges;
    onlyLeftModifiers =
      rules.modmap == [
        {
          name = "Lenovo left modifiers only";
          remap = {
            Alt_L = "Super_L";
            Super_L = "Alt_L";
          };
        }
      ];
    noTypingDelay = rules.keypress_delay_ms == 0 && rules.throttle_ms == 0;
    allowlistOnly =
      rules.keymap != [ ]
      && builtins.all (rule: rule.application ? only && !(rule.application ? not)) rules.keymap;
    launchDisabled =
      lib.hasInfix "--allow-launch=false" s.ExecStart
      && lib.all (cmd: lib.hasInfix "--allow-launch=false" cmd) b.ExecStart;
    splitBackends =
      lib.hasInfix "--desktop=socket" s.ExecStart
      && lib.all (cmd: lib.hasInfix "--bridge --desktop=hypr" cmd) b.ExecStart;
    noGlobalKeyboardXkbSwap = !(lib.hasInfix "swap_lalt_lwin" (builtins.readFile ../hyprland.conf));
    noRussianCopyConflict = !(lib.hasInfix "bind = $mainMod, С," (builtins.readFile ../hyprland.conf));
    noRussianRedoConflict =
      !(lib.hasInfix "bind = $mainMod SHIFT, Я," (builtins.readFile ../hyprland.conf));
    manualNvimPreserved =
      !(h.xdg.configFile ? "nvim/init.lua")
      && h.xdg.dataFile ? "nvim/site/plugin/lenovo-command-keys.lua";
    kittyNativeRouting = lib.hasInfix "kitten command_keys.py shift+z" h.programs.kittyExtraConfig;
    guiFind =
      builtins.length rules.keymap == 2
      && find.application == gui.application
      && find.remap == { "Super-f" = "Ctrl-f"; };
    exactFindModifiers = find.exact_match;
    noWindowFocusBindings = !(lib.hasInfix "focuswindow," bar);
    noRussianShiftFLauncher = !(lib.hasInfix "bind = $mainMod SHIFT, А," bar);
  };
in
assert lib.assertMsg (builtins.all (x: x) (
  builtins.attrValues checks
)) "Lenovo Command key declarations failed";
checks
