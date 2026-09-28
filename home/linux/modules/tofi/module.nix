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
        terminal = "kitty --";
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
    (lib.mkIf cfg.enable {
      home.packages = [
        (pkgs.writeShellScriptBin "hypr-controls" ''
          #!${pkgs.runtimeShell}

          printf '%s\n' '
          HYPRLAND CONTROLS

          F1                  this help
          Super+M             fullscreen
          Super+F             focus floating window
          Super+Shift+F       focus tiled window
          Super+G             toggle floating
          Super+T             toggle Dwindle split
          Super+P             toggle pseudotile
          Super+,             new Kitty window
          Super+N             new Kitty nvim window
          Super+E             new Yazi window
          Super+Shift+E       sudo Yazi window

          Super+H/J/K/L       focus left/down/up/right
          Super+Arrow         focus left/down/up/right
          Super+Shift+H/J/K/L move active window
          Super+LMB           move window with pointer

          Super+1..0          switch workspace 1..10
          Super+Shift+1..0    move window to workspace 1..10
          Super+S             toggle special workspace
          Super+Shift+S       move window to special workspace
          Super+Mouse wheel   previous/next workspace
          Touchpad 3-finger   switch workspace (laptop)
          ' | tofi --prompt-text='Hyprland controls' >/dev/null || true
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
