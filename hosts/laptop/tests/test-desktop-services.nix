# Selected declarations only; no realization or portal method calls.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/tests/test-desktop-services.nix
let
  flake = builtins.getFlake (toString ../../..);
  stable = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  unstable = flake.inputs.nixpkgs-unstable.legacyPackages.x86_64-linux;
  host = flake.nixosConfigurations.laptop;
  config = host.config;
  portal = host.pkgs.xdg-desktop-portal;
  same = a: b: toString a == toString b;
  paths = packages: builtins.sort builtins.lessThan (map toString packages);
  corePortals =
    packages: paths (builtins.filter (package: (package.pname or "") == "xdg-desktop-portal") packages);
in
assert same portal unstable.xdg-desktop-portal;
assert config.xdg.portal.enable;
assert config.xdg.portal.config == { };
assert !config.xdg.portal.wlr.enable;
assert
  paths config.xdg.portal.extraPortals == paths [
    stable.xdg-desktop-portal-gtk
    stable.xdg-desktop-portal-hyprland
  ];
assert map toString config.xdg.portal.configPackages == [ (toString host.pkgs.hyprland) ];
assert corePortals config.services.dbus.packages == [ (toString portal) ];
assert corePortals config.systemd.packages == [ (toString portal) ];
assert same host.pkgs.glib stable.glib;
assert same config.hardware.graphics.package stable.mesa;
assert !config.services.upower.enable;
assert builtins.all
  (name: same flake.nixosConfigurations.${name}.pkgs.xdg-desktop-portal stable.xdg-desktop-portal)
  [
    "laptop-old"
    "desktop"
    "desktop-next"
  ];
{
  version = portal.version;
  pinnedUnstableMainPortal = true;
  nativeRoutingAndStableLibrariesPreserved = true;
  otherWorkstationsUnchanged = true;
  upowerStillDisabled = true;
}
