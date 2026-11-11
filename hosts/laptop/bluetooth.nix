{ pkgsUnstable, ... }:
{
  # Pinned unstable already includes the empty-default-list fix; no local patch.
  # Only this daemon/tool package changes, not Blueman or other hosts.
  hardware.bluetooth.package = pkgsUnstable.bluez;
}
