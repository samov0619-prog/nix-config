{
  config,
  pkgs,
  pkgsGraphics,
  pkgsKernel,
  ...
}:
let
  upstreamNvidia = config.boot.kernelPackages.nvidiaPackages.latest;
in
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
    # PR #1512, head 369378dc1552: Linux 7.3 kthreads resolve paths in nullfs.
    # Replace only the open module, not the userspace derivation or kernel.
    # Retain the removal harness; see docs/backports/README.md.
    package = upstreamNvidia // {
      open = upstreamNvidia.open.overrideAttrs (old: {
        patches = (old.patches or [ ]) ++ [ ./nvidia-init-root.patch ];
      });
    };
    # Live PCI scan: Intel drives the active built-in panel; NVIDIA is opt-in.
    prime = {
      intelBusId = "PCI:0:2:0";
      nvidiaBusId = "PCI:2:0:0";
      offload = {
        enable = true;
        enableOffloadCmd = true;
      };
    };
    # Approved RTD3 opt-in; 0x03's wording can mask a failed support check.
    # Native NixOS sets 0x02 and runtime-PM udev rules, without old device removals.
    powerManagement.finegrained = true;
    # Keep NVIDIA 615/open's native suspend/VRAM handling; no legacy suspend units
    # or forced S0ix. Real idle, offload wake and resume still require acceptance.
    # Do not force Steam or global session variables onto NVIDIA.
  };

  # Replace the existing firmware input, rather than adding a conflicting second
  # linux-firmware tree or discarding other firmware selected by NixOS modules.
  nixpkgs.overlays = [
    (_final: _prev: { linux-firmware = pkgsGraphics.linux-firmware; })
  ];
}
