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
    exec = "kitty -- yazi %f";
    type = "Application";
    mimeType = [ "inode/directory" ] ++ archiveMimeTypes;
  };
}
