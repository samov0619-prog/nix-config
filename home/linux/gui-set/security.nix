{ pkgs, ... }:
{
  services.gpg-agent.pinentry.package = pkgs.pinentry-qt;
  # One agent tied to the UWSM graphical session, not a second exec-once launch.
  services.hyprpolkitagent.enable = true;
}
