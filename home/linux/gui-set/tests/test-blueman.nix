# Selected merged HM settings only; no Bluetooth operations, build or activation.
let
  flake = builtins.getFlake (toString ../../../..);
  lib = flake.inputs.nixpkgs.lib;
  check =
    name: gui:
    let
      config = flake.homeConfigurations.${name}.config;
      settings = config.dconf.settings."org/blueman/general" or { };
    in
    assert
      if gui then
        config.dconf.enable && settings.notification-daemon == false
      else
        !(settings ? notification-daemon);
    {
      nativeBluemanDialogs = gui;
    };
in
lib.mapAttrs check {
  samov-laptop = true;
  samov-laptop-old = true;
  samov-desktop = true;
  samov-server = false;
  samov-mac = false;
}
