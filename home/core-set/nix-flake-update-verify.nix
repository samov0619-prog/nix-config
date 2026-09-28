{ pkgs, ... }:
let
  nixFlakeUpdateVerify = pkgs.writeShellApplication {
    name = "nix-flake-update-verify";
    runtimeInputs = with pkgs; [
      coreutils
      git
      nix
    ];
    text = ''
      set -euo pipefail

      usage() {
        cat <<'EOF'
      Usage: nix-flake-update-verify --hosts HOST (--input INPUT | --no-update)

      Hosts: laptop, desktop, server, server-installer, mac, all
      Inputs: nixpkgs, nixpkgs-unstable, home-manager, browser-previews,
              disko, freesm, nix-gc-env, xremap-flake, all

      --hosts HOST   Verify one host, or every host supported by this platform.
      --input INPUT  Update one root input, or all inputs, before building.
      --no-update    Build against the existing flake.lock.
      EOF
      }

      host=""
      input=""
      no_update=false
      while [ "$#" -gt 0 ]; do
        case "$1" in
          --help | -h)
            usage
            exit 0
            ;;
          --hosts | --input)
            option="$1"
            shift
            if [ "$#" -eq 0 ]; then
              usage >&2
              exit 2
            fi
            case "$option" in
              --hosts) host="$1" ;;
              --input) input="$1" ;;
            esac
            ;;
          --no-update) no_update=true ;;
          *)
            usage >&2
            exit 2
            ;;
        esac
        shift
      done

      if [ -z "$host" ] || { [ -z "$input" ] && [ "$no_update" = false ]; } || { [ -n "$input" ] && [ "$no_update" = true ]; }; then
        usage >&2
        exit 2
      fi

      case "$(uname -s)" in
        Linux)
          supported_hosts="laptop desktop server server-installer"
          ;;
        Darwin)
          supported_hosts="mac"
          ;;
        *)
          printf '%s\n' "FAILED: phase=arguments; input=$input; host=$host; output=none; exit=2" >&2
          printf '%s\n' "This platform is unsupported." >&2
          exit 2
          ;;
      esac

      if [ "$host" = all ]; then
        hosts="$supported_hosts"
      elif case " $supported_hosts " in *" $host "*) true ;; *) false ;; esac; then
        hosts="$host"
      else
        printf '%s\n' "FAILED: phase=arguments; input=$input; host=$host; output=none; exit=2" >&2
        printf '%s\n' "This host must be verified on its supported platform." >&2
        exit 2
      fi

      if ! repo="$(git rev-parse --show-toplevel)"; then
        printf '%s\n' "FAILED: phase=repository; input=$input; host=$host; output=none; exit=1" >&2
        exit 1
      fi
      cd "$repo"

      if [ "$no_update" = true ]; then
        input=locked
      else
        case "$input" in
          nixpkgs | nixpkgs-unstable | home-manager | browser-previews | disko | freesm | nix-gc-env | xremap-flake)
            if nix flake update "$input"; then
              :
            else
              status=$?
              printf '%s\n' "FAILED: phase=update; input=$input; host=$host; output=flake.lock; exit=$status" >&2
              exit "$status"
            fi
            ;;
          all)
            if nix flake update; then
              :
            else
              status=$?
              printf '%s\n' "FAILED: phase=update; input=all; host=$host; output=flake.lock; exit=$status" >&2
              exit "$status"
            fi
            ;;
          *)
            printf '%s\n' "FAILED: phase=arguments; input=$input; host=$host; output=flake.lock; exit=2" >&2
            printf '%s\n' "Unknown root input: $input" >&2
            exit 2
            ;;
        esac
      fi

      build_target() {
        target_host="$1"
        output="$2"
        installable="$3"
        if nix build --no-link "$installable"; then
          :
        else
          status=$?
          printf '%s\n' "FAILED: phase=build; input=$input; host=$target_host; output=$output; exit=$status" >&2
          exit "$status"
        fi
      }

      for target_host in $hosts; do
        case "$target_host" in
          laptop | desktop | server)
            build_target "$target_host" nixos ".#nixosConfigurations.$target_host.config.system.build.toplevel"
            build_target "$target_host" home-manager ".#homeConfigurations.samov-$target_host.activationPackage"
            ;;
          server-installer)
            build_target "$target_host" nixos .#nixosConfigurations.server-installer.config.system.build.toplevel
            ;;
          mac)
            build_target mac home-manager .#homeConfigurations.samov-mac.activationPackage
            ;;
        esac
      done

      printf '%s\n' "Verified host: $host"
      printf '%s\n' "Lock input: $input"
    '';
  };
in
{
  home.packages = [ nixFlakeUpdateVerify ];

  home.file.".config/fish/completions/nix-flake-update-verify.fish".text = ''
    complete -c nix-flake-update-verify -f
    complete -c nix-flake-update-verify -l hosts -r -a 'laptop desktop server server-installer mac all' -d 'Host to verify'
    complete -c nix-flake-update-verify -l input -r -a 'nixpkgs nixpkgs-unstable home-manager browser-previews disko freesm nix-gc-env xremap-flake all' -d 'Root input to update'
    complete -c nix-flake-update-verify -l no-update -d 'Build the existing lock file'
    complete -c nix-flake-update-verify -s h -l help -d 'Show usage'
  '';
}
