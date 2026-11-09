{ lib, pkgs, ... }:
let
  applyTheme = pkgs.writeShellApplication {
    name = "qt-theme-apply";
    runtimeInputs = [
      pkgs.python3
      pkgs.dconf
    ];
    text = ''
      exec python3 ${./apply.py} "$@"
    '';
  };
in
{
  qt = {
    enable = true;
    # HM's qt5ct name is also accepted by the Qt6 plugin.
    platformTheme.name = "qtct";
    style.package = with pkgs; [
      adwaita-qt
      adwaita-qt6
    ];
    # Do not set style.name: a fixed override bypasses the live proxy style.
  };

  # Clear the old F11 override when a new login/session imports HM variables.
  home.sessionVariables.QT_STYLE_OVERRIDE = "";
  systemd.user.sessionVariables.QT_STYLE_OVERRIDE = "";
  home.packages = [ applyTheme ];

  # Mutable qtct files are intentional: its native directory watcher reloads
  # atomic updates. Only the declared appearance keys are managed, not fonts,
  # shortcuts, recent files or the rest of each application's preferences.
  home.activation.qtAppearance = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    run ${applyTheme}/bin/qt-theme-apply --mode system --initialize-nomacs
  '';
}
