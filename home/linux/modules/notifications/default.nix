{ pkgs, ... }:
{
  services.mako = {
    enable = true;
    settings.default-timeout = 15000;
  };
  home.packages = [ (pkgs.callPackage ./package.nix { }) ];
}
