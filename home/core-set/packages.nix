{ pkgs, ... }:
{
  home.packages = with pkgs; [
    ripgrep
    fd
    nixfmt-rfc-style
    nixd
    git-filter-repo
    ueberzugpp
    packwiz
    go
    gcc
  ];
}
