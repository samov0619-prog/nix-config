{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.filemanager1-common;

  # Generate config file content
  configFile = pkgs.writeText "filemanager1-config" ''
    cmd=${cfg.wrapperScript}
  '';
in
{
  options.services.filemanager1-common = {
    enable = lib.mkEnableOption "org.freedesktop.FileManager1 D-Bus service";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.filemanager1-common;
      defaultText = lib.literalExpression "pkgs.filemanager1-common";
      description = ''
        The filemanager1-common package to use.
      '';
    };

    fileManager = lib.mkOption {
      type = lib.types.enum [
        "yazi"
        "ranger"
        "nnn"
        "lf"
        "custom"
      ];
      default = "yazi";
      description = ''
        Which terminal file manager to use.
        Set to "custom" to use a custom wrapper script.
      '';
    };

    wrapperScript = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = ''
        Path to the wrapper script that will be executed by the D-Bus service.
        This is automatically set based on the fileManager option unless
        fileManager is set to "custom".
      '';
    };

    terminalCommand = lib.mkOption {
      type = lib.types.str;
      default = "${pkgs.alacritty}/bin/alacritty -e";
      defaultText = lib.literalExpression ''"''${pkgs.alacritty}/bin/alacritty -e"'';
      example = lib.literalExpression ''
        # Для alacritty:
        "''${pkgs.alacritty}/bin/alacritty -e"

        # Для kitty:
        "''${pkgs.kitty}/bin/kitty -e"
        # или (новые версии):
        "''${pkgs.kitty}/bin/kitty --"

        # Для wezterm:
        "''${pkgs.wezterm}/bin/wezterm start --"

        # Для foot:
        "''${pkgs.foot}/bin/foot -e"
      '';
      description = ''
        Terminal emulator command including the execution flag.

        IMPORTANT: This should include the flag needed to execute commands:
        - alacritty uses -e
        - kitty uses -e or -- (depending on version)
        - wezterm uses -- after "start"
        - foot uses -e

        The wrapper script has been patched to NOT add a hardcoded separator,
        so you have full control over the command execution syntax.
      '';
    };
  };

  # Config only applies on Linux (D-Bus/systemd dependency)
  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = cfg.fileManager != "custom" || cfg.wrapperScript != null;
        message = "fileManager=custom requires services.filemanager1-common.wrapperScript to be set";
      }
    ];
    # Automatically set wrapper script based on fileManager choice
    services.filemanager1-common.wrapperScript = lib.mkDefault (
      if cfg.fileManager == "yazi" then
        "${cfg.package}/share/org.freedesktop.FileManager1.common/yazi-wrapper.sh"
      else if cfg.fileManager == "ranger" then
        "${cfg.package}/share/org.freedesktop.FileManager1.common/ranger-wrapper.sh"
      else if cfg.fileManager == "nnn" then
        "${cfg.package}/share/org.freedesktop.FileManager1.common/nnn-wrapper.sh"
      else if cfg.fileManager == "lf" then
        "${cfg.package}/share/org.freedesktop.FileManager1.common/lf-wrapper.sh"
      else
        null
    );

    # Install the package
    home.packages = [ cfg.package ];

    # Create config directory and file
    xdg.configFile."org.freedesktop.FileManager1.common/config".source = configFile;

    # Set up systemd user service
    systemd.user.services.filemanager1-dbus = {
      Unit = {
        Description = "FileManager1 D-Bus Service";
        PartOf = [ "graphical-session.target" ];
        After = [ "graphical-session.target" ];
      };

      Service = {
        Type = "dbus";
        BusName = "org.freedesktop.FileManager1";
        ExecStart = "${cfg.package}/libexec/file_manager_dbus";
        Environment = [
          "TERMCMD=${lib.escapeShellArg cfg.terminalCommand}"
        ];
        Restart = "on-failure";
        RestartSec = 5;
      };

      Install = {
        WantedBy = [ "graphical-session.target" ];
      };
    };

    # Install D-Bus service activation file
    xdg.dataFile."dbus-1/services/org.freedesktop.FileManager1.service".text = ''
      [D-BUS Service]
      Name=org.freedesktop.FileManager1
        Exec=${cfg.package}/libexec/file_manager_dbus
        SystemdService=filemanager1-dbus.service
    '';
  };
}
