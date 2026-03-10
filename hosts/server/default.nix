{ ... }:
{
  imports = [ ./hardware.nix ];

  boot.loader.grub.enable = true;
  boot.loader.grub.device = "/dev/sda";

  time.timeZone = "Europe/Moscow";

  networking = {
    hostName = "hommy";
    useDHCP = true;
    firewall = {
      enable = true;
      allowedTCPPorts = [
        22
        443
        25565
      ];
    };
  };

  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];

  users.users.samov = {
    isNormalUser = true;
    extraGroups = [ "wheel" ];
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIONlBwdPsaKnSQk2Fb3570EOQNJ65nscEZ0i2XLSKOsg samov0619.s@gmail.com"
    ];
  };

  services.openssh = {
    enable = true;
    settings = {
      PasswordAuthentication = false;
      PermitRootLogin = "prohibit-password";
    };
  };

  programs.bash.enable = true;

  system.stateVersion = "25.11";
}
