{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.minecraft.server;

  packwizBootstrap = pkgs.fetchurl {
    url = "https://github.com/packwiz/packwiz-installer-bootstrap/releases/download/v0.0.3/packwiz-installer-bootstrap.jar";
    sha256 = "sha256-qPuyTcYEJ46X9GiOgtPZGjGLmO/AjV2/y8vKtkQ9EWw=";
  };

  fabricServerJar = pkgs.fetchurl {
    url = "https://meta.fabricmc.net/v2/versions/loader/1.21.4/0.17.2/1.1.1/server/jar";
    sha256 = "sha256-vc5/e+BA33fyRDWICwynzfWcuYYyICYI4ewA2z92zT4=";
  };
in
{
  options.minecraft.server = {
    enable = lib.mkEnableOption "User Minecraft Fabric server";

    packwizDir = lib.mkOption {
      type = lib.types.str;
    };

    serverDir = lib.mkOption {
      type = lib.types.str;
    };

    memory = lib.mkOption {
      type = lib.types.str;
      default = "20G";
    };
  };

  config = lib.mkIf cfg.enable {

    ################################
    # user systemd target
    ################################

    systemd.user.targets.minecraft = {
      Unit.Description = "Minecraft user stack";
    };

    ################################
    # packwiz serve
    ################################

    systemd.user.services.packwiz-serve = {
      Unit.Description = "Packwiz HTTP server";

      Service = {
        WorkingDirectory = cfg.packwizDir;
        ExecStart = "${pkgs.packwiz}/bin/packwiz serve --port 8180";
        Restart = "always";
      };

      Install.WantedBy = [ "minecraft.target" ];
    };

    ################################
    # packwiz update
    ################################

    systemd.user.services.minecraft-packwiz-update = {
      Unit.Description = "Update mods via packwiz";

      Unit.After = [ "packwiz-serve.service" ];
      Unit.Requires = [ "packwiz-serve.service" ];

      Service = {
        Type = "oneshot";
        WorkingDirectory = cfg.serverDir;

        ExecStart = ''
          ${pkgs.jdk_headless}/bin/java \
            -jar ${packwizBootstrap} \
            -g -s server \
            http://localhost:8180/pack.toml
        '';
      };

      Install.WantedBy = [ "minecraft.target" ];
    };

    ################################
    # Fabric server
    ################################

    systemd.user.services.minecraft-server = {
      Unit.Description = "Minecraft Fabric Server";

      Unit.After = [ "minecraft-packwiz-update.service" ];
      Unit.Requires = [ "minecraft-packwiz-update.service" ];

      Service = {
        WorkingDirectory = cfg.serverDir;

        ExecStart = ''
          ${pkgs.jdk_headless}/bin/java \
            -Xmx${cfg.memory} \
            -jar ${fabricServerJar} \
            nogui
        '';

        Restart = "always";
      };

      Install.WantedBy = [ "minecraft.target" ];
    };
  };
}
