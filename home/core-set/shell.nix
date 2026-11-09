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
      # Optional trusted Fish code, intentionally not managed by Nix/Home Manager.
      # Manual setup (preserves existing content):
      #   mkdir -p ~/.config/fish
      #   touch ~/.config/fish/local-env.fish
      #   chmod 600 ~/.config/fish/local-env.fish
      # In ~/.config/fish/local-env.fish (permissions 600), add lines such as:
      #   set -gx EXAMPLE_API_KEY 'replace-with-your-key'
      # __fish_config_dir also respects a custom XDG_CONFIG_HOME.
      if test -f "$__fish_config_dir/local-env.fish"
        source "$__fish_config_dir/local-env.fish"
      end
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
    # nomacs подключается только в home/linux/modules/nomacs через Linux GUI.
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
