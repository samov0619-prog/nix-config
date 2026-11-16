{ pkgs, ... }:
{
  home.packages = with pkgs; [
    jq
    ripgrep
    fd
    unzip
    socat
  ];
}
