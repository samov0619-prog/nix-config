{ pkgs, ... }:
{
  services.mako = {
    enable = true;
    settings.default-timeout = 15000;
  };
  home.packages = [ (pkgs.callPackage ./package.nix { }) ];

  programs.fish.interactiveShellInit = ''
    function __nix_config_notify_nixos_switch --on-event fish_postexec
      set -l switch_status $status

      # Only a direct foreground switch: compound commands/pipelines can report
      # another command's status, and background jobs have not finished yet.
      if not string match --quiet --regex -- '^\s*(sudo\s+)?nixos-rebuild\s+switch(?:\s|$)' "$argv[1]"
        return $switch_status
      end
      if string match --quiet --regex -- '[;&|\n]|(?:^|\s)(?:--help|-h|--dry-run)(?:\s|$)' "$argv[1]"
        return $switch_status
      end

      if test $switch_status -eq 0
        ${pkgs.libnotify}/bin/notify-send --app-name=NixOS \
          'NixOS' 'System configuration built and activated'
      else
        ${pkgs.libnotify}/bin/notify-send --app-name=NixOS --urgency=critical \
          'NixOS' "Switch finished with errors (exit code $switch_status). See terminal output."
      end
      if test $status -ne 0
        echo 'nixos-rebuild: could not send desktop notification' >&2
      end

      return $switch_status
    end
  '';
}
