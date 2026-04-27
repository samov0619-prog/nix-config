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
  options.programs.tofi = {
    passmenu.enable = lib.mkEnableOption "tofi-passmenu (rg + tofi + pass)";
    sessionmenu.enable = lib.mkEnableOption "tofi-based power menu";
    mountmenu.enable = lib.mkEnableOption "tofi-based mount menu";
  };

  config = lib.mkMerge [
    {
      assertions = [
        {
          assertion = cfg.sessionmenu.enable -> pkgs.stdenv.isLinux;
          message = "programs.tofi.sessionmenu works only on Linux (systemd)";
        }
      ];
    }
    (lib.mkIf cfg.enable {
      programs.tofi.settings = {
        font = "NotoSans Nerd Font";
        font-size = 12;
        font-variations = "Medium";
        width = "40%";
        height = "70%";
        outline-width = 0;
        border-width = 0;
        terminal = "alacritty -e";
      };
    })
    (lib.mkIf (cfg.enable && cfg.passmenu.enable) {
      home.packages = [
        pkgs.pass
        pkgs.ripgrep
        pkgs.wtype

        (pkgs.writeShellScriptBin "tofi-passmenu" ''
          #!${pkgs.runtimeShell}

          PASSWORD_STORE_DIR="''${PASSWORD_STORE_DIR:-$HOME/.password-store}"
          rg --files --glob '*.gpg' "$PASSWORD_STORE_DIR" \
          | sed "s|$PASSWORD_STORE_DIR/||; s|\.gpg$||" \
          | sort \
          | tofi --prompt-text="🔑 pass: " --fuzzy-match=true \
          | xargs -r -d '\n' pass show \
          | head -n1 \
          | wtype -
        '')
      ];
    })
    (lib.mkIf (cfg.enable && cfg.sessionmenu.enable) {
      home.packages = [
        (pkgs.writeShellScriptBin "tofi-sessionmenu" ''
          #!${pkgs.runtimeShell}
          if ! command -v systemctl >/dev/null; then
            notify-send "tofi-sessionmenu" \
              "systemctl not found; this menu requires systemd"
            exit 1
          fi

          choice=$(
            printf "Poweroff\nReboot\n" \
            | tofi --prompt-text="󰐥"
          ) || exit 0

          case "$choice" in
          Poweroff) systemctl poweroff ;;
          Reboot) systemctl reboot ;;
          *) exit 0 ;;
          esac
        '')
      ];
    })
    (lib.mkIf (cfg.enable && cfg.mountmenu.enable) {
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
    })
  ];
}
