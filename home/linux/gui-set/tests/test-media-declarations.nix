# Selected merged declarations and MPV wrapper recipe; no builds or media commands.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/gui-set/tests/test-media-declarations.nix
let
  flake = builtins.getFlake (toString ../../../..);
  lib = flake.inputs.nixpkgs.lib;
in
builtins.mapAttrs (
  name: home:
  let
    config = home.config;
    gui = builtins.elem name [
      "samov-laptop-old"
      "samov-desktop"
      "samov-laptop"
    ];
    packages = map lib.getName config.home.packages;
    mpv = config.programs.mpv;
    scripts = mpv.scripts;
    mpvPackages = builtins.filter (
      package: lib.getName package == "mpv-with-scripts"
    ) config.home.packages;
    mediaDefaults = lib.filterAttrs (
      mime: _: lib.hasPrefix "audio/" mime || lib.hasPrefix "video/" mime
    ) config.xdg.mimeApps.defaultApplications;
  in
  assert builtins.elem "playerctl" packages == gui;
  assert mpv.enable == gui;
  assert !config.services.playerctld.enable;
  assert mediaDefaults == { };
  assert
    if gui then
      builtins.length scripts == 1
      && lib.getName (builtins.head scripts) == "mpv-mpris"
      && (builtins.head scripts).scriptName == "mpris.so"
      && lib.hasInfix (builtins.unsafeDiscardStringContext "--script=${builtins.head scripts}/share/mpv/scripts/mpris.so") mpv.finalPackage.buildCommand
      && builtins.length mpvPackages == 1
      && (builtins.head mpvPackages).outPath == mpv.finalPackage.outPath
      && builtins.elem "audacious" packages
      && builtins.elem "pwvucontrol" packages
    else
      scripts == [ ];
  {
    playerctl = gui;
    mprisScripts = map lib.getName scripts;
    wrapperLoadsMpris = gui;
    playerctld = config.services.playerctld.enable;
    inherit mediaDefaults;
  }
) flake.homeConfigurations
