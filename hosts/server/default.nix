{
  lib,
  pkgs,
  ...
}:
let
  serverSettings = import ./settings.nix;
  network = serverSettings.network;
  ipv4 = network.ipv4;
  ipv6 = network.ipv6;
  ipv6Enabled = ipv6 != null;
  samovProfiles = [
    "/home/samov/.local/state/nix/profiles/home-manager"
    "/home/samov/.local/state/nix/profiles/profile"
  ];
  serverPreflight = pkgs.writeShellApplication {
    name = "server-preflight";
    runtimeInputs = [
      pkgs.iproute2
      pkgs.util-linux
    ];
    text = builtins.readFile ./preflight.sh;
  };
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

  # Disko leaves root ext4 as the remaining disk space. NixOS creates this
  # swapfile declaratively, avoiding parser-build OOM on the small VPS.
  swapDevices = lib.optional (serverSettings.swapMiB != null) {
    device = "/swapfile";
    size = serverSettings.swapMiB;
  };

  time.timeZone = "Europe/Moscow";

  networking = {
    hostName = "hommy";
    useDHCP = ipv4.mode == "dhcp";
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
      allowedTCPPorts = [ 17431 ];
      interfaces.awg0 = {
        allowedTCPPorts = [ 53 ];
        allowedUDPPorts = [ 53 ];
      };
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

  assertions = [
    {
      assertion = builtins.elem ipv4.mode [
        "static"
        "dhcp"
      ];
      message = "server network.ipv4.mode must be static or dhcp";
    }
    {
      assertion =
        ipv4 ? interface
        && (
          ipv4.mode != "static"
          || (ipv4 ? address && ipv4 ? prefixLength && ipv4 ? gateway && ipv4 ? nameservers)
        );
      message = "IPv4 requires an interface; static mode also requires address, prefixLength, gateway, and nameservers";
    }
    {
      assertion = serverSettings.swapMiB == null || serverSettings.swapMiB > 0;
      message = "swapMiB must be null or a positive MiB value";
    }
    {
      assertion =
        !ipv6Enabled
        || (
          ipv6 ? wanAddress
          && ipv6 ? wanPrefixLength
          && ipv6 ? gateway
          && ipv6 ? vpnNetwork
          && ipv6 ? vpnPrefixLength
          && ipv6 ? egress
          && builtins.elem ipv6.egress [
            "nat66"
            "routed"
          ]
          && !lib.hasPrefix "fe80:" ipv6.wanAddress
        );
      message = "IPv6 requires a global WAN address, gateway, VPN prefix, and nat66 or routed egress";
    }
  ];

  nix = {
    gc = {
      # nix-gc-env applies this retention to system, user, and Home Manager
      # profiles. Two generations fit the VPS disk while preserving rollback.
      automatic = true;
      dates = "daily";
      options = "--delete-older-than 7d";
      delete_generations = "+2";
    };
    settings = {
      # Deduplicate identical files across store paths as they are added.
      # This saved 531 MiB on the current 20 GiB VPS during the first run.
      auto-optimise-store = true;
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

  # nix-gc-env cleans profiles below /nix/var/nix/profiles. Home Manager and
  # nix profile use per-user paths, so clean them as samov before the store GC.
  systemd.services.samov-profile-gc = {
    description = "Remove old samov Nix profile generations";
    wantedBy = [ "nix-gc.service" ];
    before = [ "nix-gc.service" ];
    path = [ pkgs.nix ];
    serviceConfig = {
      Type = "oneshot";
      User = "samov";
    };
    script = ''
      for profile in ${lib.escapeShellArgs samovProfiles}; do
        if [ -L "$profile" ]; then
          nix-env --profile "$profile" --delete-generations +2
        fi
      done
    '';
  };

  users.users.samov = {
    isNormalUser = true;
    shell = pkgs.fish;
    extraGroups = [ "wheel" ];
    openssh.authorizedKeys.keys = lib.optional (
      serverSettings.operatorAuthorizedKey != null
    ) serverSettings.operatorAuthorizedKey;
  };

  security.sudo.extraRules = [
    {
      users = [ "samov" ];
      commands = [
        {
          command = "ALL";
          options = [ "NOPASSWD" ];
        }
      ];
    }
  ];

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
    fish.enable = true;
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
  environment.systemPackages = [ serverPreflight ];

  boot.kernel.sysctl = {
    "net.ipv4.ip_forward" = 1;
  }
  // lib.optionalAttrs ipv6Enabled {
    "net.ipv6.conf.all.forwarding" = 1;
  };

  # Fresh VPS: no state from the 25.11-era configuration exists to preserve.
  system.stateVersion = "26.05";
}
