# Selected package/module declarations only; no derivation is realized.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file pkgs/amnezia-vpn/tests/test-network-declarations.nix
let
  flake = builtins.getFlake (toString ../../..);
  patch = "${flake.outPath}/pkgs/amnezia-vpn/linux-network-readiness.patch";
  lib = flake.inputs.nixpkgs.lib;
  reference = flake.nixosConfigurations.laptop.pkgs.amnezia-vpn;
  check =
    name:
    let
      host = flake.nixosConfigurations.${name};
      package = host.pkgs.amnezia-vpn;
    in
    assert host.config.programs.amnezia-vpn.enable;
    assert toString host.config.programs.amnezia-vpn.package == toString package;
    assert package.src == reference.src;
    assert package.version == "5.0.1.5";
    assert builtins.elem patch (map toString package.patches);
    assert builtins.length package.patches == 2;
    assert builtins.elem "--fuzz=0" package.patchFlags;
    assert lib.hasInfix "linux-connection-state.h" package.postPatch;
    assert lib.hasInfix "test_linux_network.py" package.checkPhase;
    {
      inherit (package) version;
      sharedLinuxReadinessPatch = true;
      nativeUnitCheckWired = true;
    };
in
builtins.listToAttrs (
  map
    (name: {
      inherit name;
      value = check name;
    })
    [
      "laptop"
      "laptop-old"
      "desktop"
    ]
)
