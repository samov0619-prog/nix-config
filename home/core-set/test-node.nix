# Shared Node selection, not a full HM build or Node/npm runtime test.
# nix eval --impure --json --offline --option allow-import-from-derivation false --file home/core-set/test-node.nix
let
  flake = builtins.getFlake (toString ../..);
in
map
  (
    system:
    let
      pkgs = flake.inputs.nixpkgs.legacyPackages.${system};
      node = import ./node.nix { inherit pkgs; };
    in
    assert map (p: p.outPath) node.home.packages == [ pkgs.nodejs_latest.outPath ];
    assert !(node ? options);
    {
      inherit system;
      sharedNodeLatestOnly = true;
      version = pkgs.nodejs_latest.version;
    }
  )
  [
    "x86_64-linux"
    "aarch64-darwin"
  ]
