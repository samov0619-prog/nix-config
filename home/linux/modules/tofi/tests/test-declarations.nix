# Selected launcher declarations and wrapper recipe; no builds or GUI commands.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/modules/tofi/tests/test-declarations.nix
let
  flake = builtins.getFlake (toString ../../../../..);
  lib = flake.inputs.nixpkgs.lib;
  check =
    name: gui:
    let
      home = flake.homeConfigurations.${name};
      config = home.config;
      pkgs = home.pkgs;
      launchers = builtins.filter (package: lib.getName package == "tofi-launch") config.home.packages;
      launcher = builtins.head launchers;
      recipe = ''
        #!${pkgs.runtimeShell}
        exec ${pkgs.python3}/bin/python3 ${../launch.py} \
          --glib ${lib.getLib pkgs.glib}/lib/libglib-2.0.so.0 \
          --tofi ${lib.getExe' config.programs.tofi.package "tofi-drun"} \
          --uwsm ${lib.getExe pkgs.uwsm}

      '';
    in
    assert builtins.length launchers == (if gui then 1 else 0);
    assert config.programs.tofi.enable == gui;
    assert
      if gui then
        launcher.text == recipe
        && config.programs.tofi.settings.terminal == "kitty --"
        && config.programs.tofi.passmenu.enable
        && config.programs.tofi.sessionmenu.enable
        && lib.hasInfix "$menu = tofi-launch\n" (
          builtins.readFile config.xdg.configFile."hypr/hyprland.conf".source
        )
      else
        true;
    {
      launcher = gui;
      explicitDependencies = gui;
      terminal = if gui then config.programs.tofi.settings.terminal else null;
    };
in
lib.mapAttrs check {
  samov-laptop-old = true;
  samov-desktop = true;
  samov-laptop = true;
  samov-server = false;
  samov-mac = false;
}
