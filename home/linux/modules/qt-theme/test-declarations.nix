# Selected merged HM attributes only; no activation derivations or package builds.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/modules/qt-theme/test-declarations.nix
let
  flake = builtins.getFlake (toString ../../../..);
  lib = flake.inputs.nixpkgs.lib;
  check =
    name: gui:
    let
      config = flake.homeConfigurations.${name}.config;
      packages = map (package: package.pname or (lib.getName package)) config.home.packages;
      has = package: builtins.elem package packages;
    in
    assert config.qt.enable == gui;
    assert has "nomacs" == gui;
    assert has "qt5ct" == gui;
    assert has "qt6ct" == gui;
    assert has "gnome-themes-extra" == gui;
    assert !(has "swayimg");
    assert !(config.xdg.configFile ? "swayimg/init.lua");
    assert
      !gui
      || (
        config.qt.platformTheme.name == "qtct"
        && config.qt.style.name == null
        && builtins.length config.qt.style.package == 2
        && config.qt.qt5ctSettings == null
        && config.qt.qt6ctSettings == null
        && config.home.sessionVariables.QT_QPA_PLATFORMTHEME == "qt5ct"
        && config.home.sessionVariables.QT_STYLE_OVERRIDE == ""
        && config.systemd.user.sessionVariables.QT_STYLE_OVERRIDE == "\${QT_STYLE_OVERRIDE:+}"
        &&
          lib.hasInfix "QT_STYLE_OVERRIDE=\${QT_STYLE_OVERRIDE:+}\n"
            config.xdg.configFile."environment.d/10-home-manager.conf".text
        && lib.hasInfix "--mode system --initialize-nomacs" config.home.activation.qtAppearance.data
        && !(config.xdg.configFile ? "qt5ct/qt5ct.conf")
        && !(config.xdg.configFile ? "qt6ct/qt6ct.conf")
        && !(config.xdg.configFile ? "nomacs/Image Lounge.conf")
        && lib.hasInfix "unset QT_STYLE_OVERRIDE" config.xdg.configFile."uwsm/env.d/theme.sh".text
        && lib.hasInfix "/bin/nomacs %s" (builtins.head config.programs.yazi.settings.opener.nomacs).run
        && config.xdg.mimeApps.defaultApplications."image/png" == [ "org.nomacs.ImageLounge.desktop" ]
        && config.xdg.mimeApps.defaultApplications."image/jpeg" == [ "org.nomacs.ImageLounge.desktop" ]
        && has "swappy"
        && lib.hasInfix "save_dir=/home/samov/Screenshots" config.xdg.configFile."swappy/config".text
      );
    {
      sharedQtAppearance = gui;
      gtkDarkThemeDeclared = gui;
      nomacsVersion =
        if gui then
          (lib.findFirst (p: (p.pname or "") == "nomacs") null config.home.packages).version
        else
          null;
      swappyPreserved = gui;
    };
in
builtins.mapAttrs check {
  samov-laptop-old = true;
  samov-desktop = true;
  samov-laptop = true;
  samov-server = false;
  samov-mac = false;
}
