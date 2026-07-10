{ pkgs, ... }:
{
  imports = [
    ./opencode
    ./neovim.nix
  ];

  programs.git = {
    enable = true;
    settings = {
      core.editor = "nvim";
    };
  };
  programs.aider-chat = {
    enable = true;
    package = pkgs.aider-chat-full;
    settings = {
      chat-language = "ru";
      commit-language = "en";
    };
  };

  # programs.opencode = {
  #   enable = true;
  # };
}
