# Selected merged runtime-PM declarations only; no build, IFD or GPU access.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/tests/test-nvidia-runtime-pm.nix
let
  flake = builtins.getFlake (toString ../../..);
  lib = flake.inputs.nixpkgs.lib;
  target = flake.nixosConfigurations.laptop;
  cfg = target.config;
  # Compare against the previous native-default policy on the same inputs/modules.
  baseline =
    (target.extendModules {
      modules = [
        { hardware.nvidia.powerManagement.finegrained = lib.mkForce false; }
      ];
    }).config;
  params = cfg.hardware.nvidia.moduleParams;
  oldParams = baseline.hardware.nvidia.moduleParams;
  nvidiaParams = params.nvidia or { };
  oldNvidiaParams = oldParams.nvidia or { };
  nvidiaRules = lib.filter (lib.hasInfix ''ATTR{vendor}=="0x10de"'') (
    lib.splitString "\n" cfg.services.udev.extraRules
  );
  controlRules = lib.filter (lib.hasInfix "ATTR{power/control}=") nvidiaRules;
  runtimeRules = [
    ''ACTION=="bind", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x030000", TEST=="power/control", ATTR{power/control}="auto"''
    ''ACTION=="bind", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x030200", TEST=="power/control", ATTR{power/control}="auto"''
    ''ACTION=="unbind", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x030000", TEST=="power/control", ATTR{power/control}="on"''
    ''ACTION=="unbind", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x030200", TEST=="power/control", ATTR{power/control}="on"''
  ];
in
assert cfg.hardware.nvidia.powerManagement.finegrained;
assert !baseline.hardware.nvidia.powerManagement.finegrained;
assert nvidiaParams.NVreg_DynamicPowerManagement == "0x02";
assert lib.hasInfix "options nvidia NVreg_DynamicPowerManagement=0x02" cfg.boot.extraModprobeConfig;
assert !(oldNvidiaParams ? NVreg_DynamicPowerManagement);
assert builtins.removeAttrs nvidiaParams [ "NVreg_DynamicPowerManagement" ] == oldNvidiaParams;
assert builtins.removeAttrs params [ "nvidia" ] == builtins.removeAttrs oldParams [ "nvidia" ];
assert
  builtins.removeAttrs cfg.hardware.nvidia.powerManagement [ "finegrained" ]
  == builtins.removeAttrs baseline.hardware.nvidia.powerManagement [ "finegrained" ];
assert !cfg.hardware.nvidia.powerManagement.enable;
assert cfg.hardware.nvidia.open;
assert cfg.hardware.nvidia.prime.offload.enable;
assert controlRules == runtimeRules;
assert !(lib.any (lib.hasInfix ''ATTR{remove}="1"'') nvidiaRules);
assert !(cfg.systemd.services ? nvidia-suspend);
assert !(cfg.systemd.services ? nvidia-hibernate);
assert !(cfg.systemd.services ? nvidia-resume);
assert !(nvidiaParams ? NVreg_PreserveVideoMemoryAllocations);
assert !(nvidiaParams ? NVreg_UseKernelSuspendNotifiers);
assert !(nvidiaParams ? NVreg_EnableS0ixPowerManagement);
{
  approvedFinegrainedRtd3Parameter = true;
  parameterReachesGeneratedModprobeConfig = true;
  nativeGpuBindUnbindRuntimePmRules = true;
  noNvidiaAudioOrUsbRemovalRules = true;
  otherModuleParametersAndSuspendPolicyMatchBaseline = true;
  noLegacySuspendUnitsOrS0ixOverride = true;
  mergedDeclarationsOnlyNotHardwareAcceptance = true;
}
