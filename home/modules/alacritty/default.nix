{
  pkgs,
  lib,
  config,
  ...
}:
let
  themesDir = "${config.xdg.configHome}/alacritty/themes";
  themesAllDir = "${config.xdg.configHome}/alacritty/themes-all";
  themeFile = "${config.xdg.configHome}/alacritty/current-theme.toml";

  alacrittyPreview = pkgs.writeShellScriptBin "alacritty-preview" ''
    THEMES_DIR="${themesDir}"
    THEMES_ALL="${themesAllDir}"

    if [ $# -eq 0 ]; then
      for t in "$THEMES_ALL"/*.toml; do
        ln -sf "$t" "$THEMES_DIR/dark.toml"
        printf 'Тема: %s — Enter для следующей, Ctrl+C чтобы оставить\n' "$(basename "$t")"
        read -r _
      done
      echo "Перебор завершён, дефолт вернётся после home-manager switch"
    else
      mode="$1"
      theme="$2"
      ln -sf "${themesAllDir}/$theme" "${themesDir}/$mode.toml"
      echo "Установлено: $mode -> $theme"
    fi
  '';
in
{
  home.packages = [ alacrittyPreview ];

  # Весь каталог тем — симлинк на store, read-only, никто не трогает
  home.file.".config/alacritty/themes-all".source = "${pkgs.alacritty-theme}/share/alacritty-theme";

  # dark.toml и light.toml — создаём через activation в мутабельном каталоге
  # entryAfter writeBoundary гарантирует что themes-all симлинк уже создан
  home.activation.alacrittyThemeDefaults = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    mkdir -p "${themesDir}"
    # [ -e "${themesDir}/dark.toml" ] || \ # Создаём только если не существуют — чтобы не затирать примерку
      ln -sf "${pkgs.alacritty-theme}/share/alacritty-theme/alacritty_0_12.toml" \
        "${themesDir}/dark.toml"
    # [ -e "${themesDir}/light.toml" ] || \ # Создаём только если не существуют — чтобы не затирать примерку
      ln -sf "${pkgs.alacritty-theme}/share/alacritty-theme/github_light_default.toml" \
        "${themesDir}/light.toml"
  '';

  programs.alacritty = {
    enable = true;
    settings = {
      general.import = [ themeFile ];
      terminal.shell = {
        program = "${pkgs.fish}/bin/fish";
        args = [ "-l" ];
      };
      font = {
        normal = {
          family = "NotoSansM Nerd Font Mono";
          style = "Medium";
        };
        bold = {
          family = "NotoSansM Nerd Font Mono";
          style = "Medium";
        };
        italic = {
          family = "NotoSansM Nerd Font Mono";
          style = "Medium";
        };
        size = 14;
      };
    };
  };
}
