# Selected declarations and derivations only; no builds or VPN/network operations.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file pkgs/installer-vpn/test-declarations.nix
let
  inputs = (builtins.getFlake (toString ../..)).inputs;
  outputs = (import ../../flake.nix).outputs (inputs // { self = outputs; });
  pkgs = inputs.nixpkgs.legacyPackages.x86_64-linux;
  helper = outputs.packages.x86_64-linux.installer-vpn;
  # The original inline client definition, before extracting the shared pin.
  originalBackend = pkgs.amneziawg-go.overrideAttrs (
    finalAttrs: _: {
      version = "3.1.20260814";
      src = pkgs.fetchFromGitHub {
        owner = "amnezia-vpn";
        repo = "amneziawg-go";
        tag = "v${finalAttrs.version}";
        hash = "sha256-HMmbKd1wYzotB+GAZ8GulyJmX7+XUnXOEerab0OCPO8=";
      };
      vendorHash = "sha256-Y2dCwlKMVLrkzDcNKyCPxFJwMbCA2mQKkakvzwbamCY=";
    }
  );
  serverTools = pkgs.callPackage ../amneziawg-3.1/tools.nix { };
in
assert outputs.apps.x86_64-linux.installer-vpn.program == "${helper}/bin/installer-vpn";
assert outputs.apps.x86_64-linux.installer-vpn.type == "app";
assert !(outputs.packages.aarch64-darwin ? installer-vpn);
assert helper.backend.drvPath == originalBackend.drvPath;
assert helper.tools.drvPath == serverTools.drvPath;
assert helper.tools.version == "3.1.20260812";
assert helper.backend.version == "3.1.20260814";
assert helper.drvPath != "";
assert helper.quick.drvPath != "";
{
  linuxAppEvaluatesWithoutServerSettingsOrInstallGuard = true;
  sharedBackendPreservesOriginalClientDerivation = true;
  serverToolsAreUnmodified = true;
  backend = helper.backend.version;
  tools = helper.tools.version;
}
