{
  pkgs,
  # nvim-config,
  ...
}:

{
  home.packages = [ pkgs.neovim-unwrapped ];

  home.sessionVariables.EDITOR = "nvim";
  home.shellAliases = {
    vi = "nvim";
    vim = "nvim";
  };

  # programs.neovim = {
  #   enable = true;
  #   defaultEditor = true;
  #   viAlias = true;
  #   vimAlias = true;
  # plugins = [
  #   {
  #     plugin = pkgs.vimPlugins.nvim-treesitter.withPlugins (p: [
  #       p.bash
  #       p.comment
  #       p.go
  #       p.gomod
  #       p.gosum
  #       p.java
  #       p.javascript
  #       p.lua
  #       p.python
  #       p.scheme
  #       p.sql
  #       p.tsx
  #       p.typescript
  #       p.vue
  #       p.vim
  #       p.vimdoc
  #       p.css
  #       p.html
  #       p.markdown
  #       p.markdown_inline
  #       p.xml
  #       p.toml
  #       p.yaml
  #       p.csv
  #       p.json
  #       p.json5
  #       p.diff
  #       p.ssh_config
  #       p.printf
  #       p.dockerfile
  #       p.git_config
  #       p.git_rebase
  #       p.gitcommit
  #       p.gitignore
  #       p.http
  #       p.query
  #     ]);
  #   }
  #   pkgs.vimPlugins.nvim-treesitter-textobjects
  # ];
  # extraPackages = with pkgs; [
  #   bash-language-server
  #   vscode-langservers-extracted
  #   gopls
  #   hyprls
  #   lua-language-server
  #   stylelint-lsp
  #   marksman
  #   lemminx
  #   beautysh
  #   jdt-language-server
  #   vtsls
  #   vue-language-server
  #   prettier
  #   eslint_d
  #   biome
  #   stylelint
  #   shfmt
  #   mdformat
  #   vscode-js-debug
  # ];
  # };

  # xdg.configFile."nvim" = {
  #   source = nvim-config.neovimConfig;
  #   recursive = true;
  # };
}
