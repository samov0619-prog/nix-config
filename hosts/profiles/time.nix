{ ... }:
{
  # Opt-in for personal workstations; servers retain upstream defaults.
  # Clock synchronisation and timezone selection are independent policies.
  time.timeZone = "Europe/Moscow";
  services.timesyncd.enable = true;
  services.automatic-timezoned.enable = false;
}
