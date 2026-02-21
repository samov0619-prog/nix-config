{ ... }:
{
  imports = [
    ./devtools
    ./packages.nix
    ./security.nix
    ./shell.nix
  ];

  programs.rclone = {
    enable = true;
  };
}
