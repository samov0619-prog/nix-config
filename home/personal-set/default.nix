{ pkgs, ... }:
{
  imports = [
    ../modules/minecraft/server
  ];

  home.packages = with pkgs; [
    blender
    freesmlauncher
    jdk_headless
  ];

  minecraft.server = {
    enable = true;

    packwizDir = "/home/samov/Projects/minecraft/packwiz/packwiz_fabric_1.21.4";
    serverDir = "/home/samov/Projects/minecraft/server/minecraft_server_fabric_1.21.4";

    memory = "20G";
  };

  systemd.user.paths.ftb-backups-fabric-1214 = {
    Unit = {
      Description = "Watch Minecraft 1.21.4 Fabric Backups folder for changes";
    };
    Path = {
      PathModified = "/home/samov/Projects/minecraft/server/minecraft_server_fabric_1.21.4/backups/";
    };
    Install = {
      WantedBy = [ "default.target" ];
    };
  };

  systemd.user.services.ftb-backups-fabric-1214 = {
    Unit = {
      Description = "Sync Minecraft 1.21.4 Fabric Backups to Google Drive";
    };
    Service = {
      Type = "oneshot";
      ExecStart = "${pkgs.rclone}/bin/rclone sync /home/samov/Projects/minecraft/server/minecraft_server_fabric_1.21.4/backups/ gd-backups:minecraft_backups_fabric_1.21.4 --bwlimit 2200k --quiet";
    };
  };
}
