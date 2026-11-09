# Selected merged NixOS attributes, without builds, IFD or live GPU checks.
# nix eval --impure --json --offline --option allow-import-from-derivation false --file hosts/laptop-next/test-graphics.nix
let
  flake = builtins.getFlake (toString ../..);
  lib = flake.inputs.nixpkgs.lib;
  system = "x86_64-linux";
  unstable = import flake.inputs.nixpkgs-unstable {
    inherit system;
    config.allowUnfree = true;
  };
  stable = import flake.inputs.nixpkgs {
    inherit system;
    config.allowUnfree = true;
  };
  target = flake.nixosConfigurations.laptop-next;
  cfg = target.config;
  # The option's apply function turns this list into a compressed buildEnv.
  # Inspect merged definitions before apply, without realizing that environment.
  firmwareInputs = lib.concatLists target.options.hardware.firmware.definitions;
  linuxFirmware = lib.filter (p: (p.pname or "") == "linux-firmware") firmwareInputs;
  firmwarePaths = map (p: p.drvPath) firmwareInputs;
  existingFirmware = lib.genAttrs [ "laptop" "desktop" ] (
    host:
    let
      package = flake.nixosConfigurations.${host}.pkgs.linux-firmware;
    in
    assert package.drvPath == stable.linux-firmware.drvPath;
    package.version
  );
in
assert cfg.boot.kernelPackages.kernel.version == unstable.linuxPackages_latest.kernel.version;
assert
  cfg.boot.kernelPackages.kernel.src.outPath == unstable.linuxPackages_latest.kernel.src.outPath;
assert cfg.hardware.nvidia.package.drvPath == cfg.boot.kernelPackages.nvidiaPackages.latest.drvPath;
assert
  cfg.hardware.nvidia.package.version == unstable.linuxPackages_latest.nvidiaPackages.latest.version;
assert cfg.hardware.nvidia.package.open.drvPath != "";
assert cfg.hardware.nvidia.open;
assert !cfg.hardware.nvidia.prime.offload.enable;
assert !cfg.hardware.nvidia.prime.sync.enable;
assert !cfg.hardware.nvidia.prime.reverseSync.enable;
assert !cfg.hardware.nvidia.powerManagement.enable;
assert cfg.hardware.graphics.enable32Bit;
assert cfg.hardware.graphics.package.drvPath == unstable.mesa.drvPath;
assert cfg.hardware.graphics.package32.drvPath == unstable.pkgsi686Linux.mesa.drvPath;
assert lib.length linuxFirmware == 1;
assert (lib.head linuxFirmware).drvPath == unstable.linux-firmware.drvPath;
assert lib.elem target.pkgs.sof-firmware.drvPath firmwarePaths;
assert lib.elem target.pkgs.wireless-regdb.drvPath firmwarePaths;
assert lib.any (a: lib.hasInfix "not install-ready" a.message && !a.assertion) cfg.assertions;
{
  kernel = cfg.boot.kernelPackages.kernel.version;
  nvidia = cfg.hardware.nvidia.package.version;
  mesa64 = cfg.hardware.graphics.package.version;
  mesa32 = cfg.hardware.graphics.package32.version;
  firmware = (lib.head linuxFirmware).version;
  inherit existingFirmware;
  selectedMergedGraphicsAttributes = true;
  openModuleDerivationEvaluates = true;
  installGuardPresent = true;
}
