{ ... }:
{
  imports = [ ./neovim.nix ];

  programs.git = {
    enable = true;
    settings = {
      core.editor = "nvim";
    };
  };

  # programs.opencode = {
  #   enable = true;
  # };
}
