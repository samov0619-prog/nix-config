# Archived, not imported: udiskie handles removable disks in the active profiles.
# To restore, import this module alongside ../tofi and explicitly enable
# programs.tofi.mountmenu.enable. The original menu implementation is preserved.
{
  config,
  pkgs,
  lib,
  ...
}:
let
  cfg = config.programs.tofi;
in
{
  options.programs.tofi.mountmenu.enable = lib.mkEnableOption "tofi-based mount menu";

  config = lib.mkIf (cfg.enable && cfg.mountmenu.enable) {
    home.packages = [
      pkgs.util-linux
      (pkgs.writeShellScriptBin "tofi-mountmenu" ''
        #!${pkgs.runtimeShell}
        set -eu

        # Получаем список разделов с файловой системой, кроме /
        entries=$(
          lsblk -pnlo NAME,LABEL,FSTYPE,MOUNTPOINT,SIZE,TRAN \
          | awk '
              $3 != "" && $4 != "/" {
                label = ($2 != "" ? $2 : "no-label")
                status = ($4 != "" ? "mounted" : "unmounted")
                tran = ($6 != "" ? $6 : "disk")
                printf "%s (%s) %s %s [%s]\n", $1, label, $3, $5, status
              }
            '
        )

        [ -n "$entries" ] || exit 0

        choice=$(printf "%s\n" "$entries" | tofi --prompt-text "Mount: ") || exit 0

        dev=$(printf "%s" "$choice" | awk '{print $1}')

        mountpoint=$(lsblk -no MOUNTPOINT "$dev")

        if [ -n "$mountpoint" ]; then
          udisksctl unmount -b "$dev"
        else
          udisksctl mount -b "$dev"
        fi
      '')
    ];
  };
}
