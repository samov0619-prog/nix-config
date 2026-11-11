# Selected merged HM declarations only; no builds or compositor changes.
# nix eval --impure --offline --json --file home/linux/laptop/test-hotkeys.nix
let
  f = builtins.getFlake (toString ../../..);
  lib = f.inputs.nixpkgs.lib;
  configs = lib.genAttrs [ "laptop" "laptop-old" "desktop" ] (
    host: f.homeConfigurations."samov-${host}".config
  );
  helpPackage = config: lib.findFirst (p: lib.getName p == "hypr-controls") null config.home.packages;
  touchpadPackage =
    config: lib.findFirst (p: lib.getName p == "lenovo-touchpad") null config.home.packages;
  laptop = configs.laptop;
in
assert touchpadPackage laptop != null;
assert lib.hasInfix "touchpad.py" (touchpadPackage laptop).text;
assert lib.hasInfix "--hyprctl" (touchpadPackage laptop).text;
assert
  builtins.readFile laptop.xdg.configFile."hypr/hyprland.conf".source
  == builtins.readFile ./hyprland.conf;
assert lib.hasInfix "Fn+F1" (helpPackage laptop).text;
assert lib.hasInfix "Fn+F11" (helpPackage laptop).text;
assert lib.hasInfix "F9 (star)" (helpPackage laptop).text;
assert lib.hasInfix "F8 (touchpad)" (helpPackage laptop).text;
assert !lib.hasInfix "F3                  agent todo" (helpPackage laptop).text;
assert lib.all
  (
    host:
    touchpadPackage configs.${host} == null
    && lib.hasInfix "F3                  agent todo" (helpPackage configs.${host}).text
    && lib.hasInfix "Super+F11" (helpPackage configs.${host}).text
  )
  [
    "laptop-old"
    "desktop"
  ];
{
  lenovoHelperAndHostAccurateHelp = true;
  otherHostsKeepTheirShortcuts = true;
  declarationsOnlyNotLiveKeys = true;
}
