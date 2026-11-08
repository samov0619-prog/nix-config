{ ... }:
{
  # Mason owns editor tools; Nix supplies their Python/npm prerequisites.
  # Reuse the global CLI modules so ad-hoc commands and Mason use the same packages.
  # Keep this opt-in: the lean server imports only the base Neovim module.
  imports = [
    ./neovim.nix
    ../node.nix
    ../python.nix
  ];
}
