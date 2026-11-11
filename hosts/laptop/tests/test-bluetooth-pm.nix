# Selected merged declarations only; no kernel/module/system build or IFD.
# Use path: so newly created local patch files are included before Git staging.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/tests/test-bluetooth-pm.nix
let
  flake = builtins.getFlake ("path:" + toString ../../..);
  lib = flake.inputs.nixpkgs.lib;
  cfg = flake.nixosConfigurations.laptop.config;
  upstream = flake.inputs.nixpkgs-unstable.legacyPackages.x86_64-linux;
  upstreamKernel = flake.inputs.nixpkgs-kernel.legacyPackages.x86_64-linux.linux_latest;
  kernel = cfg.boot.kernelPackages.kernel;
  patches = [
    "btintel-pcie-refresh-dstate"
    "btintel-pcie-pm-flow"
  ];
  selected = lib.filter (p: builtins.elem p.name patches) cfg.boot.kernelPatches;
  files = map (name: "${flake.outPath}/hosts/laptop/${name}.patch") patches;
  kernelFiles = map (p: toString (p.patch or p)) kernel.patches;
in
assert map (p: p.name) selected == patches;
assert map (p: toString p.patch) selected == files;
# NixOS inserts kernelPatches before the package's final randstruct patch.
# Check both ordered subsequences, not an assumed end-of-list concatenation.
assert lib.filter (p: builtins.elem p files) kernelFiles == files;
assert
  lib.filter (p: !(builtins.elem p files)) kernelFiles
  == map (p: toString (p.patch or p)) upstreamKernel.patches;
assert kernel.version == upstreamKernel.version;
assert !(lib.hasInfix "-rc" kernel.version);
assert lib.versionAtLeast kernel.version
  flake.inputs.nixpkgs.legacyPackages.x86_64-linux.linuxPackages_latest.kernel.version;
assert kernel.src.outPath == upstreamKernel.src.outPath;
assert cfg.boot.kernelPackages.stdenv.drvPath == kernel.stdenv.drvPath;
assert cfg.hardware.nvidia.package.open.stdenv.drvPath == kernel.stdenv.drvPath;
assert builtins.elem "SYSSRC=${kernel.dev}/lib/modules/${kernel.modDirVersion}/source"
  cfg.hardware.nvidia.package.open.makeFlags;
assert builtins.elem "SYSOUT=${kernel.dev}/lib/modules/${kernel.modDirVersion}/build"
  cfg.hardware.nvidia.package.open.makeFlags;
assert cfg.hardware.nvidia.package.drvPath == cfg.boot.kernelPackages.nvidiaPackages.latest.drvPath;
assert
  cfg.hardware.nvidia.package.version == upstream.linuxPackages_latest.nvidiaPackages.latest.version;
assert cfg.hardware.nvidia.open;
assert cfg.hardware.nvidia.prime.offload.enable;
assert cfg.hardware.bluetooth.package.outPath == upstream.bluez.outPath;
assert cfg.services.blueman.enable;
assert lib.any (lib.hasPrefix "BTINTEL PM CLEANUP:") cfg.warnings;
assert lib.all
  (
    name:
    lib.all (
      p: !(builtins.elem p.name patches)
    ) flake.nixosConfigurations.${name}.config.boot.kernelPatches
  )
  [
    "laptop-old"
    "desktop"
  ];
{
  inherit (kernel) version;
  namedPatchesReachSelectedKernel = true;
  kernelSourceVersionAndExistingPatchesPreserved = true;
  matchingNvidiaAndBluezSelectionPreserved = true;
  nvidiaOpenUsesSelectedKernelAndCompiler = true;
  releasedKernelNotOlderThanExistingStableLatest = true;
  lenovoOnly = true;
  updateRemovalReminderPresent = true;
}
