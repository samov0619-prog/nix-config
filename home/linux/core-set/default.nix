{ pkgs, ... }:
{
  home.packages = with pkgs; [
    xray
  ];
}
