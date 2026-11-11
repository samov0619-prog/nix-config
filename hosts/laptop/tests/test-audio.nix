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
assert !config.services.upower.enable;
assert builtins.all
  (name: same flake.nixosConfigurations.${name}.config.services.pipewire.package stable.pipewire)
  [
    "laptop-old"
    "desktop"
  ];
{
  inherit (package) version;
  stableSourceAndUpstreamPatchesPreserved = true;
  lenovoServiceOnly = true;
  clientsAndWirePlumberUnchanged = true;
  audioFeaturesPreserved = true;
}
