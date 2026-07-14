{ pkgs, ... }:
{
  home.packages = with pkgs; [
    ripgrep
    fd
    nixfmt
    nixd
    git-filter-repo
    ueberzugpp
    packwiz
    go
    gcc
    nodejs
    python3
    unzip
    gnumake
    tree-sitter
    devenv
    socat
  ];
}
