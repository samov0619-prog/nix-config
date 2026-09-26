{ lib, ... }:
{
  options.samov.profileGc = {
    homeManager.keep = lib.mkOption {
      type = lib.types.ints.positive;
      default = 5;
      description = "Number of Home Manager generations to retain.";
    };

    nixProfile.keepCurrentOnly = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Keep only the current modern nix profile generation.";
    };

    schedule = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = "Future platform scheduler calendar expression.";
    };
  };

  # macOS has no NixOS nix-gc.service. When samov-mac gains scheduled GC,
  # implement launchd.agents.samov-profile-gc from these options: prune the
  # Home Manager profile, run nix profile wipe-history, then nix-collect-garbage.
  # Keep this module declarative-only until the Mac profile has a chosen schedule.
}
