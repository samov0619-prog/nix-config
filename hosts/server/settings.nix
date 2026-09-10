# VPS-specific values. Replace every REPLACE_ME value before installation and
# every null before enabling the corresponding service.
let
  # Use one public key for samov SSH administration and profile-download SFTP.
  operatorAuthorizedKey = null;
in
{
  # The placeholder is deliberately not a device, so Disko cannot target a
  # real disk until preflight generates local settings.
  diskDevice = "/dev/REPLACE_ME";
  # A 3 GiB VPS needs disk-backed headroom for large Tree-sitter parser builds.
  # Set null only when RAM is sufficient without swap.
  swapMiB = 2048;
  domain = null;
  acmeEmail = null;
  publicEndpoint = null;
  network = {
    ipv4 = {
      # static: fixed provider values, required by the current VPS. dhcp: let
      # the provider assign IPv4; use only when its DHCP setup is verified.
      mode = "static";
      # Documentation-only IPv4 values keep the skeleton evaluable. They must
      # never be activated on a real server.
      interface = "REPLACE_ME";
      address = "192.0.2.2";
      prefixLength = 24;
      gateway = "192.0.2.1";
      # DNS for the VPS itself: Nix downloads, filter updates, Git, and ACME.
      # VPN clients use AdGuard at 10.66.0.1 instead.
      nameservers = [
        # Quad9 with malware blocking, then Cloudflare as an independent fallback.
        "9.9.9.9"
        "1.1.1.1"
      ];
    };

    # Leave null when the preflight has no global IPv6/default route.
    # For a global WAN IPv6 without a provider-routed client prefix, use:
    # ipv6 = {
    #   wanAddress = "2001:db8:100::2";
    #   wanPrefixLength = 64;
    #   gateway = "fe80::1";
    #   vpnNetwork = "fd42:1234:5678:1";
    #   vpnPrefixLength = 64;
    #   egress = "nat66";
    # };
    ipv6 = null;
  };
  awgPort = 51820;
  inherit operatorAuthorizedKey;
  sftpAuthorizedKey = operatorAuthorizedKey;
}
