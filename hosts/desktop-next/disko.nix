{ ... }:
let
  layouts = import ../disko/layouts.nix;
in
layouts.mkEfiExt4 {
  # TODO before use: inspect `lsblk -f` and `efibootmgr -v`. This EFI template
  # must be replaced with a BIOS-capable layout if the target is not UEFI.
  device = "/dev/disk/by-id/REPLACE_ME";
}
