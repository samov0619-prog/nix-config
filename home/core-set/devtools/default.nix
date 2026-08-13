{ ... }:
{
  imports = [ ./neovim.nix ];

  programs.git = {
    enable = true;
    settings = {
      core.editor = "nvim";
    };
  };
  programs.gh.enable = true;

  # programs.opencode = {
  #   enable = true;
  # };
}
