{ ... }:
{
  programs.gpg.enable = true;
  services.gpg-agent = {
    enable = true;
    defaultCacheTtl = 3600;
    maxCacheTtl = 3600;
    defaultCacheTtlSsh = 3600;
    maxCacheTtlSsh = 3600;
  };

  programs.password-store.enable = true;
}
