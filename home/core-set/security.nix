{ ... }:
{
  programs.gpg.enable = true;
  services.gpg-agent.enable = true;

  programs.password-store.enable = true;
}
