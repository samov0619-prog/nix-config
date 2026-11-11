# Selected merged declarations only: no builds, battery discharge or PM actions.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/test-battery.nix
let
  flake = builtins.getFlake (toString ../..);
  lib = flake.inputs.nixpkgs.lib;
  target = flake.nixosConfigurations.laptop;
  cfg = target.config;
  baseline =
    (target.extendModules {
      modules = [ { services.upower.enable = lib.mkForce false; } ];
    }).config;
  upower = cfg.services.upower;
  ini = cfg.environment.etc."UPower/UPower.conf".text;
  bar = builtins.readFile ../../home/linux/laptop/waybar-config.jsonc;
  # Compare defined storage policy fields, not the optional unset label option.
  swapPolicy =
    config:
    map (swap: {
      inherit (swap) device priority;
      randomEncryption = swap.randomEncryption.enable;
    }) config.swapDevices;
in
assert upower.enable;
assert upower.usePercentageForPolicy;
assert upower.percentageLow == 15;
assert upower.percentageCritical == 5;
assert upower.percentageAction == 2;
assert upower.criticalPowerAction == "Hibernate";
assert !upower.allowRiskyCriticalPowerAction;
assert lib.all (line: lib.hasInfix line ini) [
  "UsePercentageForPolicy=true"
  "PercentageLow=15"
  "PercentageCritical=5"
  "PercentageAction=2"
  "CriticalPowerAction=Hibernate"
];
assert lib.hasInfix ''"states": { "warning": 15, "critical": 2 }'' bar;
assert !(lib.hasInfix "hibernate" bar);
assert cfg.services.power-profiles-daemon == baseline.services.power-profiles-daemon;
assert cfg.services.logind.settings == baseline.services.logind.settings;
assert cfg.boot.resumeDevice == baseline.boot.resumeDevice;
assert swapPolicy cfg == swapPolicy baseline;
assert cfg.hardware.nvidia.moduleParams == baseline.hardware.nvidia.moduleParams;
assert lib.all (host: !flake.nixosConfigurations.${host}.config.services.upower.enable) [
  "laptop-old"
  "desktop"
];
{
  lenovoNativeHibernateAtTwoPercent = true;
  warningAndGeneratedConfigurationMatch = true;
  existingPowerAndResumePolicyPreserved = true;
  declarationsOnlyNotLowBatteryAcceptance = true;
}
