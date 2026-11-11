# Selected declarations only; no builds or live Waybar/GTK checks.
let
  flake = builtins.getFlake (toString ../../../../..);
  lib = flake.inputs.nixpkgs.lib;
  check =
    name: gui:
    let
      config = flake.homeConfigurations.${name}.config;
      lua = config.programs.yazi.initLua;
      hasWorker = config.xdg.configFile ? "waybar/scripts/disk-status";
    in
    assert config.programs.yazi.freeSpaceStatus.enable == !gui;
    assert lib.hasInfix " FREE " lua == !gui;
    assert hasWorker == gui;
    assert (!gui) || (lib.hasInfix "dofile(" lua);
    {
      waybarDiskWorker = hasWorker;
      legacyYaziFreeSpace = !gui;
      yaziContextPreserved = if gui then true else null;
    };
in
lib.mapAttrs check {
  samov-laptop-old = true;
  samov-desktop = true;
  samov-laptop = true;
  samov-server = false;
  samov-mac = false;
}
