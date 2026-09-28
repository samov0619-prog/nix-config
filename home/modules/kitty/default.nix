{ pkgs, ... }:
let
  # Build-time трансформация langmap: (kitty.conf + map.txt) -> новый kitty.conf.
  # Раньше это делал kitten на живой машине, мутируя файл на месте — отсюда
  # и был мутабельный костыль. Логика чисто функциональная, поэтому её место
  # в деривации: на выходе обычный read-only store-путь.
  kittyConf = pkgs.runCommand "kitty.conf" { } ''
    templates=(${pkgs.kitty}/share/doc/kitty/html/_downloads/*/kitty.conf)
    test "''${#templates[@]}" -eq 1
    ${
      if pkgs.stdenv.isDarwin then
        ''cat ${./darwin-prelude.conf} "''${templates[0]}" ${./common.conf} ${./darwin.conf} > source.conf''
      else
        ''cat "''${templates[0]}" ${./common.conf} > source.conf''
    }
    ${pkgs.python3}/bin/python3 ${./kitty-langmap/build.py} \
      source.conf ${./kitty-langmap/map.txt} > "$out"
  '';
in
{
  home.packages = [ pkgs.kitty pkgs.nerd-fonts.noto ];

  # Всё декларативно и read-only. Обновления из репы доезжают сами,
  # результат воспроизводим на любой машине.
  xdg.configFile = {
    "kitty/kitty.conf".source = kittyConf;
    "kitty/dark-theme.auto.conf".source = ./dark-theme.auto.conf;
    "kitty/light-theme.auto.conf".source = ./light-theme.auto.conf;
    "kitty/themes".source = ./themes;
  };
}
