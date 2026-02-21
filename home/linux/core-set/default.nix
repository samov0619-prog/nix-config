{
  config,
  pkgs,
  lib,
  ...
}:
{
  home.packages = with pkgs; [
    dragon-drop
  ];
  home.sessionVariables = {
    NIX_FLAKE = "${config.home.homeDirectory}/nix-config";
  };

  programs.yazi.keymap.mgr.prepend_keymap = lib.mkAfter [
    {
      on = [ "<c-n>" ];
      run = ''shell -- dragon-drop -x -i -T %h'';
      desc = "Dragon-drop";
    }
  ];

  services.pass-secret-service.enable = true;
}
