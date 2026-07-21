{ pkgs, ... }:
{
  home.packages = with pkgs; [
    ripgrep
    fd
    nixfmt
    nixd
    git-filter-repo
    go
    gcc
    nodejs
    python3
    unzip
    gnumake
    tree-sitter
    socat
    devenv
  ];
}
