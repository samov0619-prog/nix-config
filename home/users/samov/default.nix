{
  lib,
  pkgs,
  username,
  ...
}:

{
  home.username = username;
  home.homeDirectory = if pkgs.stdenv.isDarwin then "/Users/${username}" else "/home/${username}";
  # Keep legacy hosts stable; fresh hosts import a version-specific override.
  home.stateVersion = lib.mkDefault "25.11";

  programs.home-manager.enable = true;
}
