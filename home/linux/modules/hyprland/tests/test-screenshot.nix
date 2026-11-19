# Selected merged declarations; no builds, activation or display access.
let
  flake = builtins.getFlake (toString ../../../../..);
  lib = flake.inputs.nixpkgs.lib;
  check =
    name: gui:
    let
      config = flake.homeConfigurations.${name}.config;
      packages = map lib.getName config.home.packages;
      slurpPackage = lib.findFirst (package: lib.getName package == "slurp") null config.home.packages;
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
        && builtins.length (builtins.filter (name: name == "slurp") packages) == 1
        # getFlake copies local paths into the store; compare the actual patch bytes.
        && lib.any (
          patch:
          builtins.readFile patch
          == builtins.readFile ../../../../../pkgs/slurp-cursor-shape/cursor-shape.patch
        ) slurpPackage.patches
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
