{ ... }:
let
  layouts = import ../disko/layouts.nix;
in
layouts.mkEfiExt4Swap {
  # Replace after booting the target NixOS installer and checking `lsblk`.
  device = "/dev/disk/by-id/REPLACE_ME";
  # Set to at least the RAM size when hibernation is required.
  swapSize = "REPLACE_ME";
}
