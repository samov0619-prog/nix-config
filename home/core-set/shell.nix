{ pkgsUnstable, ... }:
{
  programs.fish = {
    enable = true;
    interactiveShellInit = ''
      if test -f ~/.config/llm-secrets/env
        for line in (cat ~/.config/llm-secrets/env)
          set -gx (string split "=" $line)
        end
      end
    '';
    functions.vpn = ''
      set -x all_proxy socks5://127.0.0.1:20170
      $argv
    '';
  };
  programs.fzf = {
    enable = true;
    enableFishIntegration = true;
  };
  programs.atuin = {
    enable = true;
    enableFishIntegration = true;
  };
  programs.zoxide = {
    enable = true;
    enableFishIntegration = true;
  };
  programs.yazi = {
    enable = true;
    package = pkgsUnstable.yazi;
    plugins = {
      inherit (pkgsUnstable.yaziPlugins) compress;
    };
    keymap = {
      mgr.prepend_keymap = [
        {
          on = [
            "c"
            "a"
            "a"
          ];
          run = "plugin compress";
          desc = "Archive selected files";
        }
        {
          on = [
            "c"
            "a"
            "p"
          ];
          run = "plugin compress -p";
          desc = "Archive selected files (password)";
        }
      ];
    };
  };
}
