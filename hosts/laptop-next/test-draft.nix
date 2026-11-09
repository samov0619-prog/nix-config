# Lightweight declaration fixtures, not a complete NixOS/HM evaluation.
# nix eval --impure --json --offline --file hosts/laptop-next/test-draft.nix
let
  root = ../..;
  flake = builtins.getFlake (toString root);
  lib = flake.inputs.nixpkgs.lib;
  pkgs = {
    xray = "xray";
    amnezia-vpn.version = "5.0.1.5";
    iptables = "iptables";
    gawk = "gawk";
    stdenv.cc.cc.lib = "libstdc++";
    zlib = "zlib";
    openssl = "openssl";
    curl = "curl";
    glib = "glib";
    brightnessctl = "brightnessctl";
    nerd-fonts.noto = "noto";
    nerd-fonts.droid-sans-mono = "droid";
    freesmlauncher = "freesm";
    packwiz = "packwiz";
    jdk_headless = "jdk";
    nomacs = "/fixture/stable-nomacs";
    waybar.overrideAttrs =
      f:
      f {
        patches = [ "upstream.patch" ];
        postPatch = "upstream-hook\n";
      };
  };
  host = import ./default.nix {
    inherit lib pkgs;
    pkgsUnstable.amnezia-vpn.version = "5.0.3.0";
  };
  home = import ../../home/linux/laptop-next/default.nix { inherit pkgs; };
  sharedGui = import ../../home/linux/gui-set/default.nix {
    inherit pkgs;
    config.home.homeDirectory = "/fixture/home";
  };
  viewer = import ../../home/linux/modules/nomacs/default.nix { inherit lib pkgs; };
  pkgsGraphics = {
    linuxPackages_latest = {
      kernel = "unstable-latest-kernel";
      nvidiaPackages.latest = "matching-nvidia-latest";
    };
    mesa = "unstable-mesa-64";
    pkgsi686Linux.mesa = "unstable-mesa-32";
    linux-firmware = "unstable-firmware";
  };
  graphics = import ./graphics.nix {
    inherit pkgsGraphics;
    config.boot.kernelPackages = pkgsGraphics.linuxPackages_latest;
  };
  firmwareOverrides = (builtins.head graphics.nixpkgs.overlays) { } { };
  disk = (import ./disko.nix { }).disko.devices.disk.main;
  partitions = disk.content.partitions;
  gc = import ../profiles/gc.nix {
    inherit lib pkgs;
    config.samov.profileGc = {
      user = "samov";
      homeManager.keep = host.samov.profileGc.homeManager.keep;
    };
  };
in
assert disk.device == "/dev/disk/by-id/REPLACE_ME";
assert partitions.root.content.type == "filesystem";
assert partitions.root.content.format == "ext4";
assert partitions.root.content.mountpoint == "/";
assert partitions.swap.size == "48G";
assert partitions.swap.content.type == "swap";
assert partitions.swap.content.resumeDevice;
assert host.services.power-profiles-daemon.enable;
assert builtins.elem ./graphics.nix host.imports;
assert graphics.boot.kernelPackages == pkgsGraphics.linuxPackages_latest;
assert graphics.hardware.graphics.enable;
assert graphics.hardware.graphics.enable32Bit;
assert graphics.hardware.graphics.package == pkgsGraphics.mesa;
assert graphics.hardware.graphics.package32 == pkgsGraphics.pkgsi686Linux.mesa;
assert graphics.hardware.nvidia.open;
assert graphics.hardware.nvidia.modesetting.enable;
assert graphics.services.xserver.videoDrivers == [ "nvidia" ];
assert graphics.hardware.nvidia.package == graphics.boot.kernelPackages.nvidiaPackages.latest;
assert !(graphics.hardware.nvidia ? prime);
assert !(graphics.hardware.nvidia ? powerManagement);
assert lib.attrNames firmwareOverrides == [ "linux-firmware" ];
assert firmwareOverrides.linux-firmware == pkgsGraphics.linux-firmware;
assert host.hardware.enableRedistributableFirmware;
assert !((host.powerManagement or { }) ? cpuFreqGovernor);
assert !(host.services ? thermald);
assert !(host ? zramSwap);
assert host.nix.gc.automatic;
assert host.nix.gc.dates == "weekly";
assert host.nix.gc.delete_generations == "+10";
assert host.samov.profileGc.homeManager.keep == 10;
assert lib.hasInfix "--delete-generations +10" gc.config.systemd.services.samov-profile-gc.script;
assert gc.config.systemd.services.samov-profile-gc.before == [ "nix-gc.service" ];
assert !(host.boot ? resumeDevice);
assert !(host.hardware ? uinput);
assert host.services.getty.autologinUser == "samov";
assert host.services.getty.autologinOnce;
assert host.users.mutableUsers;
assert host.users.users.samov.initialPassword == "changeme";
assert host.security.sudo.wheelNeedsPassword;
assert !(host.services ? fprintd);
assert !(host.programs ? hyprlock);
assert !(home.programs ? hyprlock);
assert !((home.services or { }) ? hypridle);
assert !(host.nix.settings ? trusted-users);
assert host.users.users.samov.extraGroups == [ "wheel" ];
assert lib.all (a: !a.assertion) host.assertions;
assert host.system.stateVersion == "26.05";
assert home.wayland.windowManager.hyprland.configType == "hyprlang";
assert
  home.programs.waybar.package.patches == [
    "upstream.patch"
    ../../home/linux/laptop-next/waybar/power-profile-tooltip.patch
  ];
assert lib.hasPrefix "upstream-hook\n" home.programs.waybar.package.postPatch;
assert lib.hasInfix "power-profile-cycle.hpp" home.programs.waybar.package.postPatch;
assert !(home ? voiceDictate);
assert !(home ? minecraft);
assert
  home.home.packages == [
    "freesm"
    "packwiz"
    "jdk"
  ];
assert !(builtins.elem ../../home/linux/modules/xremap home.imports);
assert builtins.elem ../../home/linux/gui-set home.imports;
assert builtins.elem ../../home/linux/modules/nomacs sharedGui.imports;
assert !(builtins.pathExists ../../home/linux/modules/swayimg/default.nix);
assert !(builtins.pathExists ../../home/linux/modules/swayimg/swayimg.lua);
assert !(sharedGui ? qt);
assert builtins.elem ../../home/linux/modules/qt-theme sharedGui.imports;
assert !(home ? disabledModules);
assert viewer.home.packages == [ pkgs.nomacs ];
assert
  viewer.programs.yazi.settings.opener.nomacs == [
    {
      run = "/fixture/stable-nomacs/bin/nomacs %s";
      orphan = true;
      desc = "View and edit images with nomacs";
      for = "linux";
    }
  ];
assert
  viewer.programs.yazi.settings.open.prepend_rules == [
    {
      mime = "image/*";
      use = [
        "nomacs"
        "open"
      ];
    }
  ];
assert viewer.xdg.mimeApps.defaultApplications."image/png" == [ "org.nomacs.ImageLounge.desktop" ];
assert viewer.xdg.mimeApps.defaultApplications."image/jpeg" == [ "org.nomacs.ImageLounge.desktop" ];
assert !(viewer.xdg.mimeApps.defaultApplications ? "image/svg+xml");
assert !(viewer.xdg ? configFile);
{
  lenovoDeclarations = true;
  lenovoUnstableReleaseGraphicsDeclarations = true;
  noAcerHardwareOrExtraPrivileges = true;
  requestedBootstrapAutologinAndSudoDeclarations = true;
  noUnpreparedMinecraftInstance = true;
  installGuardPresent = true;
  lenovoWaybarOverridePreservesUpstreamHooks = true;
  sharedLinuxGuiStableNomacsWithYaziAndMimeAssociations = true;
  unencryptedExt4And48GiBSwapDeclarations = true;
  zramDisabledAndWeeklyTenGenerationRetention = true;
}
