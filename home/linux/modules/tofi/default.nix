{
  ...
}:
{
  imports = [
    ./module.nix
  ];

  programs.tofi = {
    enable = true;
    passmenu.enable = true;
    sessionmenu.enable = true;
    mountmenu.enable = true;
  };
}
