{
  lib,
  pkgs,
  ...
}:
let
  serverSettings = import ./settings.nix;
in
{
  imports = [
    ./hardware.nix
    ./disko.nix
    ./vpn.nix
    ./adguard.nix
    ./proxy.nix
    ./sftp.nix
  ];

  _module.args = { inherit serverSettings; };

  # First installation: set the disk and service values in settings.nix, boot
  # the provider rescue system, then run nixos-anywhere with `.#server`.
  # `root@<vps-ip>` is only needed to reach that remote rescue machine.
  boot.loader.grub = {
    enable = true;
    efiSupport = true;
    efiInstallAsRemovable = true;
    # The hybrid Disko layout contains both BIOS and EFI boot partitions.
    device = serverSettings.diskDevice;
  };

  time.timeZone = "Europe/Moscow";

  networking = {
    hostName = "hommy";
    useDHCP = true;
    firewall = {
      enable = true;
      allowedTCPPorts = [ 17431 ];
      interfaces.awg0 = {
        allowedTCPPorts = [ 53 ];
        allowedUDPPorts = [ 53 ];
      };
    };
  };

  nix = {
    gc = {
      automatic = true;
      dates = "weekly";
      options = "--delete-older-than 14d";
      delete_generations = "+5";
    };
    settings = {
      experimental-features = [
        "nix-command"
        "flakes"
      ];
      trusted-users = [
        "root"
        "samov"
      ];
    };
  };

  users.users.samov = {
    isNormalUser = true;
    extraGroups = [ "wheel" ];
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINTAdj6jWH+V9+USI7Gq4efjABJr9nmQ06lJozBBXHPe samov0619.s.rutest"
    ];
  };

  services.openssh = {
    enable = true;
    ports = [ 17431 ];
    settings = {
      PasswordAuthentication = false;
      KbdInteractiveAuthentication = false;
      PermitRootLogin = "prohibit-password";
    };
  };

  programs = {
    bash.enable = true;
    nix-ld = {
      enable = true;
      libraries = with pkgs; [
        stdenv.cc.cc.lib
        zlib
        openssl
        curl
      ];
    };
  };

  # Make remote terminals such as Kitty usable without missing-terminfo errors.
  environment.enableAllTerminfo = true;

  # Fresh VPS: no state from the 25.11-era configuration exists to preserve.
  system.stateVersion = "26.05";
}
