{ pkgs, ... }:
{
  home.packages = with pkgs; [
    xray
    adbfs-rootless
    android-tools
    btop
  ];

  programs.fish.shellAliases = {
    phone-mount = "mkdir -p ~/mnt/phone && adbfs ~/mnt/phone";
    phone-unmount = "fusermount3 -u ~/mnt/phone";
  };

}
