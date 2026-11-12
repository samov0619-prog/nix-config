# Actual theme generation and selected host delivery; no builds or live GTK.
let
  f = builtins.getFlake (toString ../../../../..);
  lib = f.inputs.nixpkgs.lib;
  fixture = import ../../default.nix {
    pkgs.writeText = name: text: {
      outPath = "/fixture/${name}";
      inherit text;
    };
  };
  check =
    mode:
    let
      key = "waybar/style-${mode}.css";
      css = fixture.xdg.configFile.${key}.source.text;
      shared = ../../../modules/waybar;
      expected =
        builtins.replaceStrings
          [ ''@import url("./style.css");'' ]
          [ (builtins.readFile (shared + "/style.css")) ]
          (builtins.readFile (shared + "/style-${mode}.css"))
        + builtins.readFile (../. + "/palette-${mode}.css")
        + builtins.readFile ../appearance.css;
    in
    assert css == expected;
    assert !lib.hasInfix "@import" css;
    assert lib.hasInfix "@define-color lenovo_startup_yellow" css;
    assert lib.hasInfix "color: inherit" css;
    assert lib.hasInfix "padding: 0 6px" css;
    assert lib.hasInfix "#power-profiles-daemon.performance" css;
    assert lib.hasInfix "#custom-gpu-manual:hover" css;
    assert lib.hasInfix "lenovo-waybar-${mode}.css" (
      toString f.homeConfigurations.samov-laptop.config.xdg.configFile.${key}.source
    );
    assert lib.all
      (
        name:
        toString f.homeConfigurations.${name}.config.xdg.configFile.${key}.source
        # getFlake evaluates the Git snapshot in the store, not this worktree path.
        == f.outPath + "/home/linux/modules/waybar/style-${mode}.css"
      )
      [
        "samov-laptop-old"
        "samov-desktop"
      ];
    true;
in
assert lib.all check [
  "dark"
  "light"
];
{
  lenovoOnlyPastelForegroundsAndSpacing = true;
  selfContainedGeneratedThemes = true;
  otherHostsKeepSharedThemes = true;
  declarationsOnlyNotLiveAppearance = true;
}
