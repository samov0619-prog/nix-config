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
  disk = (import ./disko.nix { }).disko.devices.disk.main;
  partitions = disk.content.partitions;
in
assert disk.device == "/dev/disk/by-id/REPLACE_ME";
assert partitions.root.content.type == "filesystem";
assert partitions.root.content.format == "ext4";
assert partitions.root.content.mountpoint == "/";
assert partitions.swap.size == "48G";
assert partitions.swap.content.type == "swap";
assert partitions.swap.content.resumeDevice;
assert host.services.power-profiles-daemon.enable;
assert host.hardware.nvidia.open;
assert !((host.powerManagement or { }) ? cpuFreqGovernor);
assert !(host.services ? thermald);
assert !(host ? zramSwap);
assert !(host.boot ? resumeDevice);
assert !(host.hardware ? uinput);
assert !(host.services ? getty);
assert !(host.users.users.samov ? initialPassword);
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
{
  lenovoDeclarations = true;
  noAcerHardwareOrLoginOverrides = true;
  noUnpreparedMinecraftInstance = true;
  installGuardPresent = true;
  lenovoWaybarOverridePreservesUpstreamHooks = true;
  unencryptedExt4And48GiBSwapDeclarations = true;
}
