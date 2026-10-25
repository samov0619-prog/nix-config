{
  pkgsUnstable,
  lib,
  config,
  ...
}:
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
    # macOS: для язи просмотрщиком изображений использовать дефолтный
    # мак-просмотрщик (Quick Look через `open`). Linux-специфичный opener на
    # swayimg подключается только в home/linux/modules/swayimg.
    plugins = {
      compress = pkgsUnstable.yaziPlugins.compress.overrideAttrs (old: {
        postPatch = (old.postPatch or "") + ''
          substituteInPlace main.lua \
            --replace-fail 'tostring(u.parent)' 'tostring(u.url.parent)' \
            --replace-fail 'fs.unique_name(Url(temp_dir))' 'fs.unique("dir", Url(temp_dir))' \
            --replace-fail 'fs.unique_name(Url(final_output_url))' 'fs.unique("file", Url(final_output_url))'
        '';
      });
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
    initLua = ''
      -- show disk in status bar
      Status:children_add(function()
          local command = "df -kh .|awk '!/^Filesystem/{printf \" %s FREE \", $(NF-2)}'"
          local info = ui.Span(io.popen(command):read('*a')):fg("green")
          return info
      end, 1500, Header.RIGHT)
    '';
    # Archive extensions must extract even when `file` reports a MIME that
    # misses Yazi's built-in archive rule. Otherwise xdg-open reopens Yazi.
    settings.open.prepend_rules = [
      {
        url = "*.{zip,7z,rar,tar,gz,gzip,tgz,xz,txz,zst,zstd,tzst,bz,bz2,bzip,bzip2,tbz,tbz2,lzma,tlz,Z,taz,ar,a,cpio,arj,xar,cab}";
        use = [
          "extract"
          "reveal"
        ];
      }
    ];
    shellWrapperName = lib.mkIf (lib.versionOlder config.home.stateVersion "26.05") "yy";
  };
  programs.direnv = {
    enable = true;
    nix-direnv.enable = true;
  };
}
