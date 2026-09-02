# VPS-specific values. Replace every null before enabling the corresponding service.
{
  # Confirmed in the provider rescue environment with `lsblk`.
  diskDevice = "/dev/vda";
  domain = null;
  acmeEmail = null;
  publicEndpoint = "94.103.3.166";
  network = {
    ipv4 = {
      # static: fixed provider values, required by the current VPS. dhcp: let
      # the provider assign IPv4; use only when its DHCP setup is verified.
      mode = "static";
      interface = "ens3";
      address = "94.103.3.166";
      prefixLength = 24;
      gateway = "94.103.3.1";
      nameservers = [
        "9.9.9.9"
        "1.1.1.1"
      ];
    };

    # null: IPv4-only; IPv6 can bypass a full IPv4 tunnel on dual-stack clients.
    # An attrset enables dual-stack after the provider supplies global IPv6;
    # choose nat66 or routed egress as documented in SERVER_AI_INSTRUCTIONS.md.
    # This location currently has only link-local IPv6, so it stays null.
    ipv6 = null;
  };
  awgPort = 51820;
  sftpAuthorizedKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINTAdj6jWH+V9+USI7Gq4efjABJr9nmQ06lJozBBXHPe samov0619.s.rutest";
}
