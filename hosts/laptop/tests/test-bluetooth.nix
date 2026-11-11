# Selected package declarations only; no BlueZ or NixOS build.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/tests/test-bluetooth.nix
let
  flake = builtins.getFlake (toString ../../..);
  config = flake.nixosConfigurations.laptop.config;
  upstream = flake.inputs.nixpkgs-unstable.legacyPackages.x86_64-linux.bluez;
  package = config.hardware.bluetooth.package;
in
assert config.hardware.bluetooth.enable;
assert config.services.blueman.enable;
assert toString package == toString upstream;
assert builtins.any (
  command: flake.inputs.nixpkgs.lib.hasPrefix "${package}/libexec/bluetooth/bluetoothd " command
) config.systemd.services.bluetooth.serviceConfig.ExecStart;
assert builtins.elem (toString package) (map toString config.services.dbus.packages);
assert builtins.all
  (
    host:
    toString flake.nixosConfigurations.${host}.config.hardware.bluetooth.package
    == toString flake.inputs.nixpkgs.legacyPackages.x86_64-linux.bluez
  )
  [
    "laptop-old"
    "desktop"
  ];
{
  inherit (package) version;
  pinnedUnstableWithoutLocalPatch = true;
  lenovoOnly = true;
}
