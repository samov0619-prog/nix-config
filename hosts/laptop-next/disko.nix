{ ... }:
let
  layouts = import ../disko/layouts.nix;
in
layouts.mkEfiExt4Swap {
  # Replace after booting the target NixOS installer and checking `lsblk`.
  device = "/dev/disk/by-id/REPLACE_ME";
  # Agreed for the 32 GiB Lenovo: 48 GiB, with early installed-system resume tests.
  # Capacity alone does not guarantee hibernation; encryption is still undecided.
  swapSize = "48G";
}
