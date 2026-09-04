# VPS-specific values. Replace every null before enabling the corresponding service.
{
  # Confirmed in the provider rescue environment with `lsblk`.
  diskDevice = "/dev/vda";
  # A 3 GiB VPS needs disk-backed headroom for large Tree-sitter parser builds.
  # Set null only when RAM is sufficient without swap.
  swapMiB = 2048;
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
      # DNS for the VPS itself: Nix downloads, filter updates, Git, and ACME.
      # VPN clients use AdGuard at 10.66.0.1 instead.
      nameservers = [
        # Quad9 with malware blocking, then Cloudflare as an independent fallback.
        "9.9.9.9"
        "1.1.1.1"
      ];
    };

    # null: IPv4-only; profiles block IPv6 until the VPS can route it.
    # An attrset enables dual-stack after the provider supplies global IPv6;
    # choose nat66 or routed egress as documented in SERVER_AI_INSTRUCTIONS.md.
    # This location currently has only link-local IPv6, so it stays null.
    ipv6 = null;
    # When preflight confirms a global IPv6 address and route, replace null:
    # ipv6 = {
    #   wanAddress = "2001:db8:100::2";
    #   wanPrefixLength = 64;
    #   gateway = "fe80::1";
    #   vpnNetwork = "fd42:1234:5678:1";
    #   vpnPrefixLength = 64;
    #   egress = "nat66"; # Use "routed" only for a provider-routed prefix.
    # };
  };
  awgPort = 51820;
  # its not bad practice keep acc name on comment
  sftpAuthorizedKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINTAdj6jWH+V9+USI7Gq4efjABJr9nmQ06lJozBBXHPe samov0619.s.rutest";
}
