# VPS-specific values. Replace every null before enabling the corresponding service.
{
  # Set from `lsblk` in the provider rescue environment before nixos-anywhere.
  diskDevice = "/dev/disk/by-id/REPLACE_ME";
  domain = null;
  acmeEmail = null;
  publicEndpoint = null;
  wanInterface = "eth0";
  awgPort = 51820;
  sftpAuthorizedKey = null;
}
