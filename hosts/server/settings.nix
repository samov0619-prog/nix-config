# VPS-specific values. Replace every null before enabling the corresponding service.
{
  # Confirmed in the provider rescue environment with `lsblk`.
  diskDevice = "/dev/vda";
  domain = null;
  acmeEmail = null;
  publicEndpoint = "94.103.3.166";
  wanInterface = "ens3";
  awgPort = 51820;
  sftpAuthorizedKey = null;
}
