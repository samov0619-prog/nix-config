# VPS-specific values. Replace every null before enabling the corresponding service.
{
  # Confirmed in the provider rescue environment with `lsblk`.
  diskDevice = "/dev/vda";
  domain = null;
  acmeEmail = null;
  publicEndpoint = "94.103.3.166";
  wanInterface = "ens3";
  wanAddress = "94.103.3.166";
  wanPrefixLength = 24;
  wanGateway = "94.103.3.1";
  nameservers = [
    "9.9.9.9"
    "1.1.1.1"
  ];
  awgPort = 51820;
  sftpAuthorizedKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINTAdj6jWH+V9+USI7Gq4efjABJr9nmQ06lJozBBXHPe samov0619.s.rutest";
}
