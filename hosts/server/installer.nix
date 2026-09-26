{ lib, modulesPath, ... }:
let
  serverSettings = import ./settings.nix;
  ipv4 = serverSettings.network.ipv4;
  ipv6 = serverSettings.network.ipv6;
  ipv6Enabled = ipv6 != null;
in
{
  imports = [
    (modulesPath + "/installer/cd-dvd/installation-cd-minimal.nix")
    ./hardware.nix
  ];

  system.stateVersion = "26.05";

  boot.zfs.forceImportRoot = false;

  networking = {
    hostName = "server-installer";
    useDHCP = ipv4.mode == "dhcp";
    # The stock installer enables NetworkManager; use only the NixOS network
    # configuration generated from preflight settings.
    networkmanager.enable = lib.mkForce false;
    interfaces.${ipv4.interface} = {
      ipv4.addresses = lib.optionals (ipv4.mode == "static") [
        {
          address = ipv4.address;
          prefixLength = ipv4.prefixLength;
        }
      ];
    }
    // lib.optionalAttrs ipv6Enabled {
      ipv6.addresses = [
        {
          address = ipv6.wanAddress;
          prefixLength = ipv6.wanPrefixLength;
        }
      ];
    };
    firewall = {
      enable = true;
      allowedTCPPorts = [ 22 ];
    };
  }
  // lib.optionalAttrs (ipv4.mode == "static") {
    defaultGateway = {
      address = ipv4.gateway;
      interface = ipv4.interface;
    };
    nameservers = ipv4.nameservers;
  }
  // lib.optionalAttrs ipv6Enabled {
    defaultGateway6 = {
      address = ipv6.gateway;
      interface = ipv4.interface;
    };
  };

  services.openssh = {
    enable = true;
    settings = {
      PasswordAuthentication = false;
      KbdInteractiveAuthentication = false;
      PermitRootLogin = "prohibit-password";
    };
  };

  users.users.root.openssh.authorizedKeys.keys = [ serverSettings.operatorAuthorizedKey ];

  assertions = [
    {
      assertion = builtins.elem ipv4.mode [
        "static"
        "dhcp"
      ];
      message = "server-installer network.ipv4.mode must be static or dhcp";
    }
    {
      assertion = builtins.isString serverSettings.operatorAuthorizedKey;
      message = "server-installer requires a complete operatorAuthorizedKey in hosts/server/settings.nix";
    }
  ];
}
