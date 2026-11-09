{ lib, ... }:
let
  # XDG uses full MIME names; Yazi's built-in archive rule strips x-/vnd.
  # Include compressed tar types and aliases used by desktop applications.
  archiveMimeTypes = [
    "application/zip"
    "application/x-zip"
    "application/x-zip-compressed"
    "application/x-7z-compressed"
    "application/vnd.rar"
    "application/x-rar"
    "application/x-rar-compressed"
    "application/x-tar"
    "application/x-gtar"
    "application/gzip"
    "application/x-gzip"
    "application/x-xz"
    "application/zstd"
    "application/x-bzip"
    "application/x-bzip1"
    "application/x-bzip2"
    "application/bzip2"
    "application/x-lzma"
    "application/x-compress"
    "application/x-archive"
    "application/x-cpio"
    "application/x-arj"
    "application/x-xar"
    "application/vnd.ms-cab-compressed"
    "application/x-compressed-tar"
    "application/x-bzip-compressed-tar"
    "application/x-bzip1-compressed-tar"
    "application/x-bzip2-compressed-tar"
    "application/x-lzma-compressed-tar"
    "application/x-xz-compressed-tar"
    "application/x-zstd-compressed-tar"
    "application/x-tarz"
    "application/x-cpio-compressed"
  ];
in
{
  xdg.mimeApps = {
    enable = true;

    defaultApplications = (lib.genAttrs archiveMimeTypes (_: [ "yazi-xdg.desktop" ])) // {
      "text/html" = [ "google-chrome.desktop" ];
      "application/xhtml+xml" = [ "google-chrome.desktop" ];
      "x-scheme-handler/http" = [ "google-chrome.desktop" ];
      "x-scheme-handler/https" = [ "google-chrome.desktop" ];
      "x-scheme-handler/about" = [ "google-chrome.desktop" ];
      "x-scheme-handler/unknown" = [ "google-chrome.desktop" ];

      "text/plain" = [ "nvim-xdg.desktop" ];
      "inode/directory" = [ "yazi-xdg.desktop" ];

      "x-scheme-handler/tg" = [ "google-chrome.desktop" ];
      "x-scheme-handler/tonsite" = [ "google-chrome.desktop" ];
    };
  };

  # xdg-open's generic launcher ignores Terminal=true. Own the terminal here
  # without replacing Neovim's upstream entry or adding another menu item.
  xdg.desktopEntries.nvim-xdg = {
    name = "Neovim (Kitty)";
    icon = "nvim";
    noDisplay = true;
    terminal = false;
    exec = "kitty -- nvim -- %F";
    type = "Application";
    mimeType = [ "text/plain" ];
  };

  xdg.desktopEntries.yazi-xdg = {
    name = "Yazi (XDG)";
    terminal = false;
    exec = "kitty -- yazi %f";
    type = "Application";
    mimeType = [ "inode/directory" ] ++ archiveMimeTypes;
  };
}
