{ ... }:
let
  layouts = import ../disko/layouts.nix;
in
layouts.mkEfiExt4Swap {
  # Replace after booting the target NixOS installer and checking `lsblk`.
  device = "/dev/disk/by-id/REPLACE_ME";
  # Agreed for the 32 GiB Lenovo: 48 GiB, with early installed-system resume tests.
  # Capacity alone does not guarantee hibernation; unencrypted root/swap are agreed.
  # ext4 is explicitly agreed for Lenovo; no Btrfs snapshot policy is needed.
  swapSize = "48G";
}
