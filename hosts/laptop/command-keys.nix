{
  config,
  lib,
  pkgs,
  xremap-flake,
  ...
}:
let
  package = xremap-flake.packages.${pkgs.stdenv.hostPlatform.system}.xremap-socket;
  rules = (pkgs.formats.yaml { }).generate "lenovo-command-keys.yml" (
    import ../../home/linux/laptop/command-keys/rules.nix
  );
in
{
  # Dedicated UID: no raw-input permissions for samov, not even via input/uinput.
  hardware.uinput.enable = true;
  users.groups.lenovo-keyboard = { };
  users.groups.xremap-context = { };
  users.users.lenovo-xremap = {
    isSystemUser = true;
    group = "lenovo-keyboard";
    extraGroups = [
      "uinput"
      "xremap-context"
    ];
  };
  users.users.samov.extraGroups = [ "xremap-context" ];
  assertions = [
    {
      assertion = config.users.users.samov.uid == null || config.users.users.samov.uid == 1000;
      message = "Lenovo xremap bridge directory must follow samov's UID (live UID: 1000).";
    }
  ];
  # Measured name/phys/bus, not the transient event0 number. Do not grant input.*.
  services.udev.extraRules = ''
    SUBSYSTEM=="input", KERNEL=="event*", ATTRS{name}=="AT Translated Set 2 keyboard", ATTRS{phys}=="isa0060/serio0/input0", ATTRS{id/bustype}=="0011", GROUP="lenovo-keyboard", MODE="0660"
  '';
  systemd.tmpfiles.rules = [
    "d /run/xremap 0755 root root -"
    "d /run/xremap/1000 2770 lenovo-xremap xremap-context -"
  ];
  systemd.services.lenovo-xremap = {
    description = "Lenovo keyboard remapper (isolated input owner)";
    wantedBy = [ "multi-user.target" ];
    after = [
      "systemd-tmpfiles-setup.service"
      "systemd-udevd.service"
      "dbus.service"
    ];
    serviceConfig = {
      User = "lenovo-xremap";
      Group = "lenovo-keyboard";
      SupplementaryGroups = [
        "uinput"
        "xremap-context"
      ];
      ExecStart = "${lib.getExe package} --desktop=socket --device 'AT Translated Set 2 keyboard' --watch=device --allow-launch=false --no-window-logging ${rules}";
      Restart = "on-failure";
      RestartSec = 2;
      Environment = "RUST_LOG=warn";
      NoNewPrivileges = true;
      CapabilityBoundingSet = "";
      PrivateNetwork = true;
      PrivateTmp = true;
      ProtectSystem = "strict";
      ProtectHome = true;
      ReadWritePaths = [ "/run/xremap/1000" ];
      DevicePolicy = "closed";
      # Cgroup input class allows enumeration/hotplug; DAC restricts physical access.
      DeviceAllow = [
        "char-input rw"
        "/dev/uinput rw"
      ];
      RestrictAddressFamilies = [ "AF_UNIX" ];
      ProtectKernelTunables = true;
      ProtectKernelModules = true;
      ProtectKernelLogs = true;
      ProtectControlGroups = true;
      RestrictSUIDSGID = true;
      LockPersonality = true;
      MemoryDenyWriteExecute = true;
      UMask = "0077";
    };
  };
}
