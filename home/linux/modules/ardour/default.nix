{ pkgs, ... }:
{
  # Keep the upstream application; only its desktop/CLI launcher is wrapped.
  home.packages = [ (pkgs.callPackage ./package.nix { }) ];
}
