# No builds/IFD: check module delivery and compare with the exact unpatched set.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/tests/test-nvidia-backport.nix
let
  flake = builtins.getFlake (toString ../../..);
  lib = flake.inputs.nixpkgs.lib;
  cfg = flake.nixosConfigurations.laptop.config;
  original = cfg.boot.kernelPackages.nvidiaPackages.latest;
  selected = cfg.hardware.nvidia.package;
  baseline =
    (flake.nixosConfigurations.laptop.extendModules {
      modules = [ { hardware.nvidia.package = lib.mkForce original; } ];
    }).config;
  patch = "${flake.outPath}/hosts/laptop/nvidia-init-root.patch";
in
assert selected.drvPath == original.drvPath;
assert selected.outPath == original.outPath;
assert selected.open.drvPath != original.open.drvPath;
assert selected.open.src.outPath == original.open.src.outPath;
assert
  map toString selected.open.patches == (map toString (original.open.patches or [ ])) ++ [ patch ];
assert cfg.boot.kernelPackages.kernel.drvPath == baseline.boot.kernelPackages.kernel.drvPath;
assert cfg.hardware.nvidia.moduleParams == baseline.hardware.nvidia.moduleParams;
assert cfg.hardware.nvidia.powerManagement == baseline.hardware.nvidia.powerManagement;
assert builtins.elem selected.open.drvPath (map (p: p.drvPath) cfg.boot.extraModulePackages);
assert !(builtins.elem original.open.drvPath (map (p: p.drvPath) cfg.boot.extraModulePackages));
assert lib.all
  (
    host:
    let
      c = flake.nixosConfigurations.${host}.config;
    in
    !(builtins.elem "nvidia-init-root.patch" (
      map builtins.baseNameOf (c.hardware.nvidia.package.open.patches or [ ])
    ))
  )
  [
    "laptop-old"
    "desktop"
  ];
{
  kernel = cfg.boot.kernelPackages.kernel.outPath;
  userspace = selected.outPath;
  originalModule = original.open.outPath;
  patchedModule = selected.open.outPath;
  source = selected.open.src.outPath;
  moduleOnlyWithUnchangedKernelUserspaceAndSleepPolicy = true;
  selectedOpenModuleDeliveredThroughExtraModulePackages = true;
}
