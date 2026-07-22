{ serverSettings, ... }:
let
  layouts = import ../disko/layouts.nix;
in
layouts.mkHybridExt4 {
  # Set settings.nix diskDevice from `lsblk` in the VPS rescue environment.
  device = serverSettings.diskDevice;
}
