{ ... }:
{
  imports = [ ./neovim.nix ];

  programs.git = {
    enable = true;
    settings = {
      core.editor = "nvim";
      merge.conflictStyle = "zdiff3";
    };
  };

  # programs.opencode = {
  #   enable = true;
  # };
}
