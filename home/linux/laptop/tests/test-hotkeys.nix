# Selected merged HM declarations only; no builds or compositor changes.
# nix eval --impure --offline --json --file home/linux/laptop/tests/test-hotkeys.nix
let
  f = builtins.getFlake (toString ../../../..);
  lib = f.inputs.nixpkgs.lib;
  configs = lib.genAttrs [ "laptop" "laptop-old" "desktop" ] (
    host: f.homeConfigurations."samov-${host}".config
  );
  helpPackage = config: lib.findFirst (p: lib.getName p == "hypr-controls") null config.home.packages;
  touchpadPackage =
    config: lib.findFirst (p: lib.getName p == "lenovo-touchpad") null config.home.packages;
  laptop = configs.laptop;
  bar = builtins.readFile ../hyprland.conf;
in
assert touchpadPackage laptop != null;
assert lib.hasInfix "touchpad.py" (touchpadPackage laptop).text;
assert lib.hasInfix "--hyprctl" (touchpadPackage laptop).text;
assert
  builtins.readFile laptop.xdg.configFile."hypr/hyprland.conf".source
  == builtins.readFile ../hyprland.conf;
assert lib.hasInfix "Fn+F1" (helpPackage laptop).text;
assert lib.hasInfix "Fn+F11" (helpPackage laptop).text;
assert lib.hasInfix "F9 (star)" (helpPackage laptop).text;
assert lib.hasInfix "F8 (touchpad)" (helpPackage laptop).text;
assert !lib.hasInfix "F3                  agent todo" (helpPackage laptop).text;
assert lib.hasInfix "bindm = $mainMod SHIFT, mouse:272, resizewindow" bar;
assert lib.hasInfix "bindm = $mainMod, mouse:272, movewindow" bar;
assert lib.hasInfix "bind = $mainMod CTRL, T, layoutmsg, splitratio 1 exact" bar;
assert lib.hasInfix "Super+Shift+LMB" (helpPackage laptop).text;
assert lib.hasInfix "not whole layout" (helpPackage laptop).text;
assert !lib.hasInfix "focus floating window" (helpPackage laptop).text;
assert !lib.hasInfix "focus tiled window" (helpPackage laptop).text;
assert lib.hasInfix "native Ctrl+F action" (helpPackage laptop).text;
assert !lib.hasInfix "focuswindow," bar;
assert !lib.hasInfix "bind = $mainMod SHIFT, А," bar;
assert lib.all
  (
    host:
    touchpadPackage configs.${host} == null
    && lib.hasInfix "F3                  agent todo" (helpPackage configs.${host}).text
    && lib.hasInfix "Super+F11" (helpPackage configs.${host}).text
    && lib.hasInfix "Super+F             focus floating window" (helpPackage configs.${host}).text
    && lib.hasInfix "Super+Shift+F       focus tiled window" (helpPackage configs.${host}).text
    && lib.hasInfix "bind = $mainMod, F, focuswindow, floating" (
      builtins.readFile configs.${host}.xdg.configFile."hypr/hyprland.conf".source
    )
    && lib.hasInfix "bind = $mainMod SHIFT, F, focuswindow, tiled" (
      builtins.readFile configs.${host}.xdg.configFile."hypr/hyprland.conf".source
    )
    && configs.${host}.programs.kittyExtraConfig == ""
    && !lib.hasInfix "Super+Shift+LMB" (helpPackage configs.${host}).text
    && !lib.hasInfix "resizewindow" (
      builtins.readFile configs.${host}.xdg.configFile."hypr/hyprland.conf".source
    )
  )
  [
    "laptop-old"
    "desktop"
  ];
{
  lenovoHelperAndHostAccurateHelp = true;
  nativeMouseResizeAndLocalSplitReset = true;
  otherHostsKeepTheirShortcuts = true;
  guiFindHelpWithoutWindowFocusBindings = true;
  declarationsOnlyNotLiveKeys = true;
}
