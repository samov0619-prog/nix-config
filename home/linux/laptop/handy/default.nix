{
  config,
  lib,
  pkgs,
  pkgsUnstable,
  ...
}:
let
  driverFile = "/run/opengl-driver/share/vulkan/icd.d/intel_icd.x86_64.json";
  # Keep the upstream package/wrappers. Restrict every launch (including the
  # launcher and CLI IPC actions), not the whole graphical session, to Intel.
  handy = pkgs.symlinkJoin {
    name = "handy-${pkgsUnstable.handy.version}";
    inherit (pkgsUnstable.handy) version meta;
    paths = [ pkgsUnstable.handy ];
    nativeBuildInputs = [ pkgs.makeWrapper ];
    postBuild = ''
      wrapProgram "$out/bin/handy" \
        --set VK_DRIVER_FILES ${lib.escapeShellArg driverFile} \
        --prefix PATH : ${lib.makeBinPath [ pkgs.wtype ]}
    '';
    passthru.unwrapped = pkgsUnstable.handy;
  };
  parakeetTdtV3Q4 = pkgs.fetchurl {
    url = "https://huggingface.co/handy-computer/parakeet-tdt-0.6b-v3-gguf/resolve/85ac09ea12fc4b1112fa76810059364bc6adc9de/parakeet-tdt-0.6b-v3-Q4_K_M.gguf";
    hash = "sha256-toVXvh48QCB/18S9nWPx0zFrlj8VMlv7DMFqi7D/0YE=";
  };
  initialSettings = pkgs.writeText "handy-initial-settings.json" (
    builtins.toJSON (import ./initial-settings.nix)
  );
  settingsDir = "${config.xdg.dataHome}/com.pais.handy";
in
{
  home.packages = [
    handy
    pkgs.wtype
  ];
  xdg.dataFile."com.pais.handy/models/parakeet-tdt-0.6b-v3-Q4_K_M.gguf".source = parakeetTdtV3Q4;

  # Tauri owns a writable store, including migrations and GUI preferences.
  # Seed only: no forced symlink, merge hook, secrets in the store, or clobbering
  # existing settings (even dangling symlinks). See README for one-time adoption.
  home.activation.handyInitialSettings =
    lib.hm.dag.entryBetween [ "reloadSystemd" ] [ "writeBoundary" ]
      ''
        if [ ! -e ${lib.escapeShellArg "${settingsDir}/settings_store.json"} ] && \
           [ ! -L ${lib.escapeShellArg "${settingsDir}/settings_store.json"} ]; then
          run mkdir -p ${lib.escapeShellArg settingsDir}
          run install -m 600 ${initialSettings} ${lib.escapeShellArg "${settingsDir}/settings_store.json"}
        fi
      '';

  # Same graphical-session lifecycle as Handy v0.9.8's upstream HM module;
  # ordinary HM systemd declarations avoid another flake input/source import.
  # App-managed XDG autostart is off: there must be only one launch mechanism.
  systemd.user.services.handy = {
    Unit = {
      Description = "Handy local dictation (Parakeet Q4, Intel Vulkan)";
      After = [ "graphical-session.target" ];
      PartOf = [ "graphical-session.target" ];
      ConditionEnvironment = "HYPRLAND_INSTANCE_SIGNATURE";
    };
    Service = {
      ExecStart = "${lib.getExe handy} --start-hidden";
      Restart = "on-failure";
      RestartSec = 5;
    };
    Install.WantedBy = [ "graphical-session.target" ];
  };
}
