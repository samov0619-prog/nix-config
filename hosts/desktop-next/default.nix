{ ... }:
{
  imports = [
    ./disko.nix
  ];

  # Add future desktop-specific GPU, audio, user, and desktop settings here.
  # Do not import the current desktop host configuration.

  # Confirm BIOS vs EFI before use; this template currently assumes UEFI.
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

  system.stateVersion = "26.05";
}
