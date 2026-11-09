# Selected merged declarations only; no Kitty/HM builds.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file home/modules/kitty/test-declarations.nix
let
  flake = builtins.getFlake (toString ../../..);
  lib = flake.inputs.nixpkgs.lib;
  check =
    name: kind:
    let
      config = flake.homeConfigurations.${name}.config;
      packages = builtins.filter (p: (p.pname or "") == "kitty") config.home.packages;
      fixed =
        p:
        builtins.any (path: builtins.baseNameOf path == "auto-theme-background-images.patch") (
          p.patches or [ ]
        );
    in
    assert builtins.length packages == (if kind == "absent" then 0 else 1);
    assert builtins.all (p: fixed p == (kind == "fixed")) packages;
    {
      kittyAutoThemeFix = kind == "fixed";
      version = if kind != "absent" then (builtins.head packages).version else null;
    };
in
lib.mapAttrs check {
  samov-laptop = "fixed";
  samov-desktop = "fixed";
  samov-laptop-next = "fixed";
  samov-server = "absent";
  samov-mac = "stock";
}
