# Selected HM declarations and actual wrapper text only; no NVIDIA access or builds.
let
  flake = builtins.getFlake (toString ../../../..);
  lib = flake.inputs.nixpkgs.lib;
  count =
    name:
    builtins.length (
      builtins.filter (
        package: lib.getName package == "gpu-monitor"
      ) flake.homeConfigurations.${name}.config.home.packages
    );
  fixture = import ../default.nix {
    pkgs = {
      python3 = "/fixture/python";
      writeShellScriptBin = name: text: {
        outPath = "/fixture/${name}";
        inherit name text;
      };
    };
  };
  wrapper = builtins.head (
    builtins.filter (package: package.name == "gpu-monitor") (lib.take 2 fixture.home.packages)
  );
in
assert count "samov-laptop" == 1;
assert lib.all (name: count name == 0) [
  "samov-laptop-old"
  "samov-desktop"
  "samov-server"
  "samov-mac"
];
assert lib.hasInfix "/fixture/python/bin/python3" wrapper.text;
assert lib.hasInfix (builtins.unsafeDiscardStringContext "${../gpu-monitor.py}") wrapper.text;
assert lib.hasInfix ''"$@"'' wrapper.text;
{
  manualGpuMonitorOnlyOnLenovo = true;
  explicitPythonAndSourceReferences = true;
  declarationsOnlyNotBuiltOrLiveUi = true;
}
