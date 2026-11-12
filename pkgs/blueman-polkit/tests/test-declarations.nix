# Selected system package declarations; no builds, activation or external settings.
let
  flake = builtins.getFlake (toString ../../..);
  lib = flake.inputs.nixpkgs.lib;
  upstream = flake.inputs.nixpkgs.legacyPackages.x86_64-linux.blueman;
  check =
    host: enabled:
    let
      system = flake.nixosConfigurations.${host};
      config = system.config;
      package = system.pkgs.blueman;
      fromPackages = packages: builtins.filter (p: lib.getName p == "blueman") packages;
      installed = fromPackages config.environment.systemPackages;
      dbus = fromPackages config.services.dbus.packages;
      units = fromPackages config.systemd.packages;
    in
    assert config.services.blueman.enable == enabled;
    assert package.src.outPath == upstream.src.outPath;
    assert package.version == upstream.version;
    assert
      if enabled then
        builtins.elem "polkit" (map lib.getName package.buildInputs)
        && builtins.elem "--enable-polkit" package.configureFlags
        && lib.all (flag: builtins.elem flag package.configureFlags) upstream.configureFlags
        && package.doInstallCheck
        && lib.hasInfix "verify.py" package.installCheckPhase
        && lib.hasInfix "test_notification_timeout.py" package.installCheckPhase
        && lib.any (patch: baseNameOf (toString patch) == "notification-timeout.patch") package.patches
        && builtins.length installed == 1
        && (builtins.head installed).outPath == package.outPath
        && builtins.length dbus == 1
        && (builtins.head dbus).outPath == package.outPath
        && builtins.length units == 1
        && (builtins.head units).outPath == package.outPath
        && config.security.polkit.enable
        && config.security.polkit.adminIdentities == [ "unix-group:wheel" ]
        && !(lib.hasInfix "org.blueman" config.security.polkit.extraConfig)
      else
        package.outPath == upstream.outPath && installed == [ ];
    {
      upstreamVersion = package.version;
      polkitBuildSupport = enabled;
      packageRegistrationsMatch = true;
    };
in
{
  laptop-old = check "laptop-old" true;
  laptop = check "laptop" true;
  desktop = check "desktop" false;
  desktopTemplate = check "desktop-next" false;
}
