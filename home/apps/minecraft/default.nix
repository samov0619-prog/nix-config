{ pkgs, ... }:
{
  home.packages = with pkgs; [
    freesmlauncher
    packwiz
    jdk_headless
  ];

  minecraft.server = {
    packwizDir = "/home/samov/Projects/minecraft/packwiz/packwiz_fabric_1.21.4";
    serverDir = "/home/samov/Projects/minecraft/server/minecraft_server_fabric_1.21.4";
    memory = "20G";
  };
}
