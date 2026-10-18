{
  pkgsUnstable,
  ...
}:
{
  # Swayimg is a Wayland-only viewer, so this module is Linux-only and is
  # imported from home/linux/gui-set. macOS uses the default system viewer for
  # images instead (see the comment in home/core-set/shell.nix).
  home.packages = [ pkgsUnstable.swayimg ];

  xdg.configFile."swayimg/init.lua".source = ./swayimg.lua;

  programs.yazi.settings = {
    opener.swayimg = [
      {
        run = "${pkgsUnstable.swayimg}/bin/swayimg %s";
        orphan = true;
        desc = "View images with swayimg";
        for = "linux";
      }
    ];

    open.prepend_rules = [
      {
        mime = "image/*";
        use = [
          "swayimg"
          "open"
        ];
      }
    ];
  };
}
