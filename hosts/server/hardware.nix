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
    "virtio_net"
    "virtio_scsi"
    "ahci"
    "nvme"
    "sd_mod"
  ];
  boot.initrd.kernelModules = [
    "virtio_pci"
    "virtio_net"
  ];
  nixpkgs.hostPlatform = lib.mkDefault "x86_64-linux";
}
