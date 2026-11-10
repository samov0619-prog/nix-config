# Selected merged declarations; no builds, activation or display access.
let
  flake = builtins.getFlake (toString ../../../../..);
  lib = flake.inputs.nixpkgs.lib;
  check =
    name: gui:
    let
      config = flake.homeConfigurations.${name}.config;
      packages = map lib.getName config.home.packages;
      helperCount = builtins.length (
        builtins.filter (package: package == "hypr-screenshot-region") packages
      );
    in
    assert helperCount == (if gui then 1 else 0);
    assert
      !gui
      || (
        lib.hasInfix "bind = , PRINT, exec, hypr-screenshot-region" (
          builtins.readFile config.xdg.configFile."hypr/hyprland.conf".source
        )
        &&
          config.xdg.configFile."swappy/config".text == ''
            [Default]
            save_dir=${config.home.homeDirectory}/Screenshots
          ''
        && config.home.file."Screenshots/.keep".text == ""
        && lib.all (package: builtins.elem package packages) [
          "grim"
          "slurp"
          "swappy"
          "wl-clipboard"
        ]
      );
    {
      screenshotHelper = gui;
      manualSwappyWorkflowPreserved = if gui then true else null;
    };
in
lib.mapAttrs check {
  samov-laptop-old = true;
  samov-desktop = true;
  samov-laptop = true;
  samov-server = false;
  samov-mac = false;
}
