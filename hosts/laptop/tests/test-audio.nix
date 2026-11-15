# Selected declarations only; no package or NixOS build.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/tests/test-audio.nix
let
  flake = builtins.getFlake (toString ../../..);
  host = flake.nixosConfigurations.laptop;
  config = host.config;
  stable = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  package = config.services.pipewire.package;
  patch = "${flake.outPath}/hosts/laptop/pipewire-x11-idempotent.patch";
  same = a: b: toString a == toString b;
  policy = config.services.pipewire.wireplumber.extraConfig."60-lenovo-audio-defaults";
in
assert config.services.pipewire.enable;
assert config.services.pipewire.alsa.enable;
assert config.services.pipewire.alsa.support32Bit;
assert config.services.pipewire.pulse.enable;
assert config.services.pipewire.jack.enable;
assert config.security.rtkit.enable;
assert package.version == stable.pipewire.version;
assert package.src == stable.pipewire.src;
assert map toString package.patches == (map toString stable.pipewire.patches) ++ [ patch ];
assert same host.pkgs.pipewire stable.pipewire;
assert same config.services.pipewire.wireplumber.package stable.wireplumber;
assert builtins.elem (toString package) (map toString config.systemd.packages);
assert builtins.elem (toString package) (map toString config.environment.systemPackages);
# Battery policy explicitly enables UPower/Hibernate; audio must preserve it.
assert config.services.upower.enable;
assert policy."wireplumber.settings"."bluetooth.autoswitch-to-headset-profile" == false;
assert
  policy."monitor.alsa.rules" == [
    {
      matches = [
        { "node.name" = "alsa_input.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__Mic1__source"; }
      ];
      actions.update-props."priority.session" = 2500;
    }
  ];
# Output defaults must use stock priorities, not compensate for a broken rule.
assert !(policy ? "monitor.bluez.rules");
assert builtins.all
  (
    name:
    same flake.nixosConfigurations.${name}.config.services.pipewire.package stable.pipewire
    && !(
      flake.nixosConfigurations.${name}.config.services.pipewire.wireplumber.extraConfig
        ? "60-lenovo-audio-defaults"
    )
  )
  [
    "laptop-old"
    "desktop"
  ];
{
  inherit (package) version;
  stableSourceAndUpstreamPatchesPreserved = true;
  lenovoServiceOnly = true;
  clientsAndWirePlumberPackagesUnchanged = true;
  lenovoNativeAudioDefaults = true;
  stockOutputPriorities = true;
  audioFeaturesPreserved = true;
}
