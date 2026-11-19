# Shared HM core-set registers this function on Linux and Darwin.
# Use native Nix platform packages, not a specific NixOS host's package set.
# For another checkout, set an absolute path in Fish config, for example:
# set -gx NSH_FLAKE "$HOME/Projects/nix-config"
# The flake must provide nixpkgs and nixpkgs-unstable inputs; default: ~/nix-config.
set -l input nixpkgs

switch "$argv[1]"
    case unstable -u --unstable
        set input nixpkgs-unstable
        set -e argv[1]
    case stable -s --stable
        set -e argv[1]
end

if test (count $argv) -eq 0
    echo 'Usage: nsh [stable|unstable] PACKAGE [PACKAGE ...]'
    return 2
end

set -l expr '
    let
      configuredFlake = builtins.getEnv "NSH_FLAKE";
      flake = builtins.getFlake (
        if configuredFlake != "" then configuredFlake
        else builtins.getEnv "HOME" + "/nix-config"
      );
    in flake.inputs.'$input'.legacyPackages.${builtins.currentSystem}
'

nix shell --impure --expr "$expr" $argv \
    --command (status fish-path) --interactive
