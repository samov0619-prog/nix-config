{ ... }:
let
  layouts = import ../disko/layouts.nix;
in
layouts.mkEfiExt4Swap {
  # Live Lenovo: this PCI path points to the UMIS 1 TB NVMe, not the USB installer.
  # Recheck model/capacity/path immediately before any destructive Disko command.
  device = "/dev/disk/by-path/pci-0000:01:00.0-nvme-1";
  # Agreed for the 32 GiB Lenovo: 48 GiB, with early installed-system resume tests.
  # Capacity alone does not guarantee hibernation; unencrypted root/swap are agreed.
  # ext4 is explicitly agreed for Lenovo; no Btrfs snapshot policy is needed.
  swapSize = "48G";
}
