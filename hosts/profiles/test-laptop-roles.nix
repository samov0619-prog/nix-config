# Host ownership/composition and selected attributes only; no builds or activation.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/profiles/test-laptop-roles.nix
let
  flake = builtins.getFlake (toString ../..);
  lib = flake.inputs.nixpkgs.lib;
  composition = (import ../../flake.nix).outputs (
    flake.inputs
    // {
      self = composition;
      nixpkgs = flake.inputs.nixpkgs // {
        lib = lib // {
          nixosSystem = args: args;
        };
      };
      home-manager = flake.inputs.home-manager // {
        lib.homeManagerConfiguration = args: args;
      };
    }
  );
  systems = composition.nixosConfigurations;
  homes = composition.homeConfigurations;
  acer = flake.nixosConfigurations.laptop-old.config;
  lenovo = flake.nixosConfigurations.laptop.config;
  disk = (import ../laptop/disko.nix { }).disko.devices.disk.main;
in
assert !(systems ? laptop-next);
assert !(homes ? samov-laptop-next);
assert builtins.elem ../laptop-old systems.laptop-old.modules;
assert !(builtins.elem ../laptop systems.laptop-old.modules);
assert builtins.elem ../laptop systems.laptop.modules;
assert !(builtins.elem ../laptop-old systems.laptop.modules);
assert builtins.length systems.laptop.modules == builtins.length systems.laptop-old.modules + 1;
assert builtins.elem ../../home/linux/laptop-old homes.samov-laptop-old.modules;
assert builtins.elem ../../home/linux/laptop homes.samov-laptop.modules;
assert !(builtins.elem ../../home/users/samov/state-26.05.nix homes.samov-laptop-old.modules);
assert builtins.elem ../../home/users/samov/state-26.05.nix homes.samov-laptop.modules;
assert builtins.elem ../../home/apps/minecraft homes.samov-laptop-old.modules;
assert !(builtins.elem ../../home/apps/minecraft homes.samov-laptop.modules);
assert acer.networking.hostName == "laptop-old";
assert acer.system.stateVersion == "25.11";
assert acer.boot.resumeDevice == "/dev/disk/by-uuid/161d4aca-e781-4585-b223-3584ec052444";
assert builtins.elem "resume_offset=6955008" acer.boot.kernelParams;
assert acer.hardware.uinput.enable;
assert acer.zramSwap.enable;
assert lenovo.networking.hostName == "laptop";
assert lenovo.system.stateVersion == "26.05";
assert !lenovo.hardware.uinput.enable;
assert !lenovo.zramSwap.enable;
assert !(lib.any (parameter: lib.hasPrefix "resume_offset=" parameter) lenovo.boot.kernelParams);
assert disk.device == "/dev/disk/by-path/pci-0000:01:00.0-nvme-1";
assert lenovo.fileSystems."/".fsType == "ext4";
assert lenovo.fileSystems."/boot".fsType == "vfat";
assert builtins.length lenovo.swapDevices == 1;
assert (builtins.head lenovo.swapDevices).device == lenovo.boot.resumeDevice;
assert flake.homeConfigurations.samov-laptop-old.config.home.stateVersion == "25.11";
assert flake.homeConfigurations.samov-laptop.config.home.stateVersion == "26.05";
assert lib.any (
  entry: !entry.assertion && lib.hasInfix "not install-ready" entry.message
) lenovo.assertions;
{
  acerKeepsLegacyHardwareAndStateVersion = true;
  lenovoOwnsLaptopNamesWithSeparateHardwareAndStateVersion = true;
  lenovoUsesObservedDiskAndPartitionResume = true;
  noPrematureMinecraftInstanceOnLenovo = true;
  installGuardPresent = true;
}
