{ config, lib, pkgs, ... }:
let
  cfg = config.samov.profileGc;
  homeDirectory = "/home/${cfg.user}";
  homeManagerProfile = "${homeDirectory}/.local/state/nix/profiles/home-manager";
  nixProfile = "${homeDirectory}/.local/state/nix/profiles/profile";
  nixGcRun = pkgs.writeShellApplication {
    name = "nix-gc-run";
    runtimeInputs = with pkgs; [ coreutils systemd ];
    text = ''
      set -euo pipefail

      /run/wrappers/bin/sudo -v
      /run/wrappers/bin/sudo journalctl --follow --lines=0 --no-pager --output=cat \
        --unit=samov-profile-gc.service \
        --unit=nix-gc.service &
      journal_pid=$!

      cleanup() {
        kill "$journal_pid" 2>/dev/null || true
        wait "$journal_pid" 2>/dev/null || true
      }
      trap cleanup EXIT INT TERM

      # Let journalctl subscribe before starting the cleanup services.
      sleep 0.1
      /run/wrappers/bin/sudo systemctl start nix-gc.service
    '';
  };
in
{
  options.samov.profileGc = {
    user = lib.mkOption {
      type = lib.types.str;
      default = "samov";
      description = "User whose XDG Nix profiles are pruned before store GC.";
    };

    homeManager.keep = lib.mkOption {
      type = lib.types.ints.positive;
      default = 5;
      description = "Number of Home Manager generations to retain.";
    };
  };

  config = {
    environment.systemPackages = [ nixGcRun ];

    systemd.services.samov-profile-gc = {
      description = "Prune ${cfg.user}'s Home Manager and Nix profile generations";
      wantedBy = [ "nix-gc.service" ];
      before = [ "nix-gc.service" ];
      path = [ pkgs.nix ];
      serviceConfig = {
        Type = "oneshot";
        User = cfg.user;
      };
      script = ''
        if [ -L "${homeManagerProfile}" ]; then
          nix-env --profile "${homeManagerProfile}" --delete-generations +${toString cfg.homeManager.keep}
        fi

        if [ -e "${nixProfile}/manifest.json" ]; then
          # nix profile has no "keep N" API. Its history only rolls back the
          # bootstrap CLI, while Home Manager rollbacks use the profile above.
          nix profile wipe-history --profile "${nixProfile}"
        fi
      '';
    };
  };
}
