# Selected merged HM attributes only, without builds or microphone access.
let
  flake = builtins.getFlake (toString ../../..);
  lib = flake.inputs.nixpkgs.lib;
  check =
    name: expected:
    let
      config = flake.homeConfigurations.${name}.config;
      packages = map lib.getName config.home.packages;
      count = builtins.length (builtins.filter (package: package == "voice-dictate") packages);
    in
    assert count == (if expected.gui then 1 else 0);
    assert
      !expected.gui
      || (
        config.voiceDictate.vulkan.enable == expected.vulkan
        && config.voiceDictate.vulkan.device == expected.device
        && lib.hasInfix "bind = $mainMod SHIFT, R, exec, voice-dictate" (
          builtins.readFile config.xdg.configFile."hypr/hyprland.conf".source
        )
      );
    {
      voiceDictate = expected.gui;
      vulkan = if expected.gui then expected.vulkan else null;
      device = if expected.gui then expected.device else null;
    };
in
lib.mapAttrs check {
  samov-laptop-old = {
    gui = true;
    vulkan = true;
    device = 1;
  };
  samov-desktop = {
    gui = true;
    vulkan = false;
    device = 0;
  };
  samov-laptop = {
    gui = true;
    vulkan = false;
    device = 0;
  };
  samov-server.gui = false;
  samov-mac.gui = false;
}
