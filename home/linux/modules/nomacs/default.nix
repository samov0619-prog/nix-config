{ lib, pkgs, ... }:
let
  # Match the stable package's org.nomacs.ImageLounge.desktop associations.
  imageMimeTypes = [
    "image/avif"
    "image/bmp"
    "image/gif"
    "image/heic"
    "image/heif"
    "image/jpeg"
    "image/jxl"
    "image/png"
    "image/tiff"
    "image/webp"
    "image/x-eps"
    "image/x-ico"
    "image/x-portable-bitmap"
    "image/x-portable-graymap"
    "image/x-portable-pixmap"
    "image/x-xbitmap"
    "image/x-xpixmap"
  ];
in
{
  # Stable nomacs: unstable currently selects an upstream Beta release.
  home.packages = [ pkgs.nomacs ];

  programs.yazi.settings = {
    opener.nomacs = [
      {
        run = "${pkgs.nomacs}/bin/nomacs %s";
        orphan = true;
        desc = "View and edit images with nomacs";
        for = "linux";
      }
    ];
    open.prepend_rules = [
      {
        mime = "image/*";
        use = [
          "nomacs"
          "open"
        ];
      }
    ];
  };

  xdg.mimeApps.defaultApplications = lib.genAttrs imageMimeTypes (_: [
    "org.nomacs.ImageLounge.desktop"
  ]);
}
