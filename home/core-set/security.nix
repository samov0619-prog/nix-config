{ ... }:
{
  programs.gpg.enable = true;
  services.gpg-agent = {
    enable = true;
    defaultCacheTtl = 3600;
    maxCacheTtl = 3600;
    defaultCacheTtlSsh = 3600;
    maxCacheTtlSsh = 3600;

    # Дефолт false → true:
    # Не разрешать pinentry сохранять парольную фразу GPG
    # во внешнем Secret Service / password manager.
    # Внутренний кэш gpg-agent продолжает работать.
    noAllowExternalCache = true;
  };

  programs.password-store.enable = true;
}
