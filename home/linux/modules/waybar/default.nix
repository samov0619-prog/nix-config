{ ... }:
{
  programs.waybar = {
    enable = true;
  };

  xdg.configFile = {
    "waybar/config.jsonc".source = ./config.jsonc;
    "waybar/style-dark.css".source = ./style-dark.css;
    "waybar/style-light.css".source = ./style-light.css;
    "waybar/style.css".source = ./style.css;

    "waybar/scripts/gp.sh" = {
      source = ./scripts/gp.sh;
      executable = true;
    };
    "waybar/scripts/startup-time.sh" = {
      source = ./scripts/startup-time.sh;
      executable = true;
    };
    "waybar/scripts/check-nix-updates.sh" = {
      source = ./scripts/check-nix-updates.sh;
      executable = true;
    };
    "waybar/scripts/nix-updates-view.sh" = {
      source = ./scripts/nix-updates-view.sh;
      executable = true;
    };
  };
}
