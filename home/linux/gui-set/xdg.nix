{ ... }:
{
  xdg.mimeApps = {
    enable = true;

    defaultApplications = {
      "text/html" = [ "firefox.desktop" ];
      "application/xhtml+xml" = [ "firefox.desktop" ];
      "x-scheme-handler/http" = [ "firefox.desktop" ];
      "x-scheme-handler/https" = [ "firefox.desktop" ];
      "x-scheme-handler/about" = [ "firefox.desktop" ];
      "x-scheme-handler/unknown" = [ "firefox.desktop" ];

      "text/plain" = [ "nvim.desktop" ];

      "x-scheme-handler/tg" = [ "firefox.desktop" ];
      "x-scheme-handler/tonsite" = [ "firefox.desktop" ];
    };
  };

  xdg.desktopEntries.yazi-xdg = {
    name = "Yazi (XDG)";
    terminal = false;
    exec = "alacritty -e yazi %f";
    type = "Application";
    mimeType = [ "inode/directory" ];
  };
}
