{ ... }:
{
  # Avahi owns mDNS; keep resolved available for ordinary and VPN DNS only.
  services.resolved.settings.Resolve.MulticastDNS = false;

  # Resolve LAN devices such as the Raspberry Pi running Zynthian via *.local.
  # Workstations opt in explicitly; this is not a VPS/installer requirement.
  services.avahi = {
    enable = true;
    nssmdns4 = true;
    openFirewall = true;
    # Discover other devices without advertising this workstation's services.
    publish.enable = false;
  };
}
