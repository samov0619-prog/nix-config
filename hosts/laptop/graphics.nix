{
  config,
  pkgs,
  pkgsGraphics,
  pkgsKernel,
  ...
}:
{
  # Latest packaged releases, not linux_testing or NVIDIA bleeding_edge/beta.
  # Kernel-only input follows released stable ahead of channel promotion.
  # Reinstantiate the existing module recipes for that kernel (same compiler),
  # preserving the unstable NVIDIA version rather than importing a new stack.
  boot.kernelPackages = pkgsGraphics.linuxPackagesFor pkgsKernel.linux_latest;
  hardware.graphics = {
    enable = true;
    enable32Bit = true;
    # Mesa is dlopened by the stable desktop/apps: keep its libc compatible.
    # The newer unstable Mesa requires GLIBC_2.43, absent from stable glibc 2.42.
    package = pkgs.mesa;
    package32 = pkgs.pkgsi686Linux.mesa;
  };
  services.xserver.videoDrivers = [ "nvidia" ];
  hardware.nvidia = {
    open = true; # Blackwell requires NVIDIA's open kernel modules, not Nouveau.
    modesetting.enable = true;
    package = config.boot.kernelPackages.nvidiaPackages.latest;
    # Live PCI scan: Intel drives the active built-in panel; NVIDIA is opt-in.
    prime = {
      intelBusId = "PCI:0:2:0";
      nvidiaBusId = "PCI:2:0:0";
      offload = {
        enable = true;
        enableOffloadCmd = true;
      };
    };
    # Agreed baseline: keep NVIDIA 615/open's native suspend/VRAM handling and
    # automatic RTD3 on supported notebooks. Do not force finegrained/legacy
    # suspend services; real idle, offload and resume remain installed checks.
    # Do not force Steam or global session variables onto NVIDIA.
  };

  # Replace the existing firmware input, rather than adding a conflicting second
  # linux-firmware tree or discarding other firmware selected by NixOS modules.
  nixpkgs.overlays = [
    (_final: _prev: { linux-firmware = pkgsGraphics.linux-firmware; })
  ];
}
