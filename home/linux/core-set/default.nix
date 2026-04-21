{ pkgs, ... }:
{
  home.packages = with pkgs; [
    xray
    adbfs-rootless
    android-tools
    btop
  ];

  programs.fish.shellAliases = {
    phone-mount = "mkdir -p ~/mnt/phone && adbfs ~/mnt/phone";
    phone-unmount = "fusermount3 -u ~/mnt/phone";
  };

  systemd.user.services.hm-gc = {
    Unit.Description = "Home Manager GC — keep last 5 generations";
    Service = {
      Type = "oneshot";
      ExecStart = pkgs.writeShellScript "hm-gc" ''
        ${pkgs.nix}/bin/nix-env \
          --profile $HOME/.local/state/nix/profiles/home-manager \
          --delete-generations +5
        ${pkgs.nix}/bin/nix-collect-garbage
      '';
    };
  };

  systemd.user.timers.hm-gc = {
    Unit.Description = "Home Manager GC timer";
    Timer = {
      OnCalendar = "weekly";
      Persistent = true;
    };
    Install.WantedBy = [ "timers.target" ];
  };
}
