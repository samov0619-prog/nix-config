{
  config,
  pkgsGraphics,
  ...
}:
{
  # Latest packaged releases, not linux_testing or NVIDIA bleeding_edge/beta.
  # Kernel and its NVIDIA module come from the same unstable package set.
  boot.kernelPackages = pkgsGraphics.linuxPackages_latest;
  hardware.graphics = {
    enable = true;
    enable32Bit = true;
    package = pkgsGraphics.mesa;
    package32 = pkgsGraphics.pkgsi686Linux.mesa;
  };
  services.xserver.videoDrivers = [ "nvidia" ];
  hardware.nvidia = {
    open = true; # Blackwell requires NVIDIA's open kernel modules, not Nouveau.
    modesetting.enable = true;
    package = config.boot.kernelPackages.nvidiaPackages.latest;
    # PRIME/Bus IDs and power-management policy still need target inventory.
  };

  # Replace the existing firmware input, rather than adding a conflicting second
  # linux-firmware tree or discarding other firmware selected by NixOS modules.
  nixpkgs.overlays = [
    (_final: _prev: { linux-firmware = pkgsGraphics.linux-firmware; })
  ];
}
