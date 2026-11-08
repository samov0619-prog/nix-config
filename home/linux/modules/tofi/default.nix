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
    # Disk mounting uses udiskie; the optional mount menu is archived next to tofi/.
  };
}
