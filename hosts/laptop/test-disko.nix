# Real locked Disko config generation with a small NixOS-option fixture.
# No scripts are built/run; no disks are inspected, formatted or mounted.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/test-disko.nix
let
  flake = builtins.getFlake (toString ../..);
  lib = flake.inputs.nixpkgs.lib;
  declarations = import ./disko.nix { };
  disko = import "${flake.inputs.disko}/default.nix" { inherit lib; };
  cfg =
    (lib.evalModules {
      modules = [
        {
          options = {
            boot.resumeDevice = lib.mkOption { type = lib.types.str; };
            fileSystems = lib.mkOption { type = lib.types.attrsOf lib.types.raw; };
            swapDevices = lib.mkOption { type = lib.types.listOf lib.types.raw; };
          };
        }
        (disko.config declarations)
      ];
    }).config;
  disk = declarations.disko.devices.disk.main;
  swap = lib.head cfg.swapDevices;
in
assert disk.device == "/dev/disk/by-path/pci-0000:01:00.0-nvme-1";
assert disk.content.partitions.ESP.size == "512M";
assert disk.content.partitions.swap.size == "48G";
assert
  builtins.attrNames cfg.fileSystems == [
    "/"
    "/boot"
  ];
assert cfg.fileSystems."/".fsType == "ext4";
assert cfg.fileSystems."/".device == "/dev/disk/by-partlabel/disk-main-root";
assert cfg.fileSystems."/boot".fsType == "vfat";
assert cfg.fileSystems."/boot".device == "/dev/disk/by-partlabel/disk-main-ESP";
assert cfg.fileSystems."/boot".options == [ "umask=0077" ];
assert lib.length cfg.swapDevices == 1;
assert swap.device == "/dev/disk/by-partlabel/disk-main-swap";
assert !swap.randomEncryption.enable;
assert cfg.boot.resumeDevice == swap.device;
{
  lockedDiskoGeneratesExpectedStorageAndResumeConfig = true;
  disk = disk.device;
  resume = cfg.boot.resumeDevice;
  filesystemTypes = lib.mapAttrs (_: value: value.fsType) cfg.fileSystems;
  swapSize = disk.content.partitions.swap.size;
}
