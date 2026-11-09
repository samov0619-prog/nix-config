# Selected merged HM attributes only; no package realization or secret-file reads.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file home/core-set/test-fish-local-env.nix
let
  flake = builtins.getFlake (toString ../..);
  lib = flake.inputs.nixpkgs.lib;
in
builtins.mapAttrs (
  _: home:
  let
    config = home.config;
    relativeConfig = lib.removePrefix (config.home.homeDirectory + "/") config.xdg.configHome;
    targets = map (file: file.target) (builtins.attrValues config.home.file);
    # No managed leaf or whole-directory symlink may own the personal file.
    forbidden =
      lib.concatMap
        (root: [
          root
          (root + "/fish")
          (root + "/fish/local-env.fish")
        ])
        [
          relativeConfig
          config.xdg.configHome
        ];
  in
  assert config.programs.fish.enable;
  assert lib.hasInfix ''source "$__fish_config_dir/local-env.fish"''
    config.programs.fish.interactiveShellInit;
  assert !(lib.hasInfix "llm-secrets/env" config.programs.fish.interactiveShellInit);
  assert !(lib.hasInfix "local-env.fish" config.programs.fish.shellInit);
  assert !(lib.any (target: builtins.elem target forbidden) targets);
  {
    interactiveHookPresent = true;
    oldLoaderAbsent = true;
    personalFileUnmanaged = true;
  }
) flake.homeConfigurations
