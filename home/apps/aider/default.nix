{ pkgs, ... }:
{
  programs.aider-chat = {
    enable = true;
    package = pkgs.aider-chat-full;
    settings = {
      chat-language = "ru";
      commit-language = "en";
    };
  };
}
