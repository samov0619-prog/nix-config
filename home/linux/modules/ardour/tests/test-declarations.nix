# Selected merged declarations; no package builds or Ardour launch.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/modules/ardour/tests/test-declarations.nix
let
  flake = builtins.getFlake (toString ../../../../..);
  lib = flake.inputs.nixpkgs.lib;
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  wrapped = pkgs.callPackage ../package.nix { };
in
assert wrapped.unwrapped.outPath == pkgs.ardour.outPath;
assert wrapped.major == lib.versions.major pkgs.ardour.version;
assert lib.hasInfix "--major ${wrapped.major}" wrapped.launcher.text;
assert lib.hasInfix
  (builtins.unsafeDiscardStringContext "${pkgs.ardour}/bin/${pkgs.ardour.meta.mainProgram}")
  wrapped.launcher.text;
assert lib.hasInfix ''"$@"'' wrapped.launcher.text;
builtins.mapAttrs (
  name: home:
  let
    packages = map lib.getName home.config.home.packages;
    wrappers = builtins.filter (p: lib.getName p == "ardour-system-theme") home.config.home.packages;
    gui = builtins.elem name [
      "samov-laptop-old"
      "samov-desktop"
      "samov-laptop"
    ];
  in
  assert builtins.length wrappers == (if gui then 1 else 0);
  assert !gui || (builtins.head wrappers).outPath == wrapped.outPath;
  assert !(builtins.elem "ardour" packages);
  assert !gui || builtins.elem "audacious" packages;
  assert !gui || builtins.elem "pwvucontrol" packages;
  {
    startupThemeWrapper = gui;
    upstreamUnchanged = true;
  }
) flake.homeConfigurations
