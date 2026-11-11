# Selected HM declarations only: no builds, GTK or NVIDIA access.
# nix eval --impure --offline --json --file home/linux/laptop/waybar/tests/test-gpu.nix
let
  root = ../../../../..;
  f = builtins.getFlake (toString root);
  lib = f.inputs.nixpkgs.lib;
  configs = lib.genAttrs [ "laptop" "laptop-old" "desktop" ] (
    host: f.homeConfigurations."samov-${host}".config
  );
  path = "waybar/scripts/gpu-status";
  fixture = import ../../default.nix {
    pkgs = {
      python3 = "/fixture/python";
      hyprland = "/fixture/hyprland";
      writeShellScriptBin =
        name: text:
        assert lib.hasInfix "/fixture/python/bin/python3" text;
        assert lib.hasInfix (if name == "waybar-gpu-status" then "gpu-status.py" else "touchpad.py") text;
        assert lib.hasInfix ''"$@"'' text;
        {
          outPath = "/fixture/${name}";
          inherit text;
        };
    };
  };
in
assert configs.laptop.xdg.configFile ? ${path};
assert !(configs.laptop-old.xdg.configFile ? ${path});
assert !(configs.desktop.xdg.configFile ? ${path});
assert fixture.xdg.configFile.${path}.source == "/fixture/waybar-gpu-status/bin/waybar-gpu-status";
assert
  builtins.readFile configs.laptop.xdg.configFile."waybar/config.jsonc".source
  == builtins.readFile ../../waybar-config.jsonc;
assert
  builtins.readFile configs.laptop.xdg.configFile."waybar/style.css".source
  == builtins.readFile ../../../modules/waybar/style.css;
{
  manualGpuHelperOnlyOnLenovo = true;
  rawConfigAndSharedThemePreserved = true;
  declarationsOnlyNotBuiltOrLiveUi = true;
}
