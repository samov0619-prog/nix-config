{
  lib,
  ...
}:
{
  # Generic drivers for common VPS hypervisors. Confirm with `lsblk` and the
  # rescue environment before a real install; add provider-specific modules here.
  boot.initrd.availableKernelModules = [
    "virtio_pci"
    "virtio_blk"
    "virtio_scsi"
    "ahci"
    "nvme"
    "sd_mod"
  ];
  nixpkgs.hostPlatform = lib.mkDefault "x86_64-linux";
}
