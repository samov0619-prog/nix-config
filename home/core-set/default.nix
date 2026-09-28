{ ... }:
{
  imports = [
    ./devtools
    ./nix-flake-update-verify.nix
    ./packages.nix
    ./security.nix
    ./shell.nix
  ];

  programs.rclone = {
    enable = true;
  };
}
