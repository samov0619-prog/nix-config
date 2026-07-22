{ ... }:
{
  imports = [
    ./disko.nix
  ];

  # Add future laptop-specific GPU, input, audio, user, and desktop settings
  # here. Do not import the current laptop host configuration.

  boot.loader.grub = {
    enable = true;
    efiSupport = true;
    efiInstallAsRemovable = true;
    device = "nodev";
  };

  nix.gc = {
    automatic = true;
    dates = "weekly";
    delete_generations = "+5";
  };

  # Fresh host: replace the placeholder disk and swap size in disko.nix first.
  # Local installer use needs no IP: see ../disko/README.md.
  system.stateVersion = "26.05";
}
