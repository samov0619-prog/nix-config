{ config, lib, pkgs, ... }:
let
  cfg = config.samov.profileGc;
  homeDirectory = "/home/${cfg.user}";
  homeManagerProfile = "${homeDirectory}/.local/state/nix/profiles/home-manager";
  nixProfile = "${homeDirectory}/.local/state/nix/profiles/profile";
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

  config.systemd.services.samov-profile-gc = {
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
}
