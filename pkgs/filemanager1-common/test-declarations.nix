# Selected merged declarations only; no package builds or live D-Bus calls.
let
  flake = builtins.getFlake (toString ../..);
  lib = flake.inputs.nixpkgs.lib;
  check =
    name: gui:
    let
      config = flake.homeConfigurations.${name}.config;
      cfg = config.services.filemanager1-common;
      packages = map lib.getName config.home.packages;
    in
    assert builtins.elem "filemanager1-common" packages == gui;
    assert
      !gui
      || (
        cfg.enable
        && cfg.fileManager == "yazi"
        && lib.hasInfix "/bin/kitty --" cfg.terminalCommand
        && lib.hasSuffix "/yazi-wrapper.sh" cfg.wrapperScript
        && builtins.elem "localhost-uri.patch" (map builtins.baseNameOf cfg.package.patches)
        &&
          config.systemd.user.services.filemanager1-dbus.Service.ExecStart == [
            "${cfg.package}/libexec/file_manager_dbus"
          ]
        && lib.hasInfix "SystemdService=filemanager1-dbus.service" (
          config.xdg.dataFile."dbus-1/services/org.freedesktop.FileManager1.service".text
        )
      );
    {
      fileManager1 = gui;
      localhostPatch = gui;
    };
in
lib.mapAttrs check {
  samov-laptop-old = true;
  samov-desktop = true;
  samov-laptop = true;
  samov-server = false;
  samov-mac = false;
}
