# Selected merged HM attributes only, without builds or microphone access.
let
  flake = builtins.getFlake (toString ../../../..);
  lib = flake.inputs.nixpkgs.lib;
  check =
    name: expected:
    let
      config = flake.homeConfigurations.${name}.config;
      packages = map lib.getName config.home.packages;
      count = builtins.length (builtins.filter (package: package == "voice-dictate") packages);
      helper = lib.findFirst (package: lib.getName package == "voice-dictate") null config.home.packages;
      whisperExpected = expected.whisper or expected.gui;
      script = if whisperExpected then helper.text else "";
      driverFile = expected.driverFile or null;
    in
    assert count == (if whisperExpected then 1 else 0);
    assert name != "samov-laptop" || !(builtins.hasAttr "voiceDictate" config);
    assert
      !whisperExpected
      || (
        config.voiceDictate.vulkan.enable == expected.vulkan
        && config.voiceDictate.vulkan.device == expected.device
        && config.voiceDictate.vulkan.driverFile == driverFile
        && config.voiceDictate.fastLocalInput == (expected.fastLocalInput or false)
        && (
          if driverFile == null then
            !(lib.hasInfix "VK_DRIVER_FILES=" script)
          else
            lib.hasInfix "VK_DRIVER_FILES=${lib.escapeShellArg driverFile} whisper-cli" script
        )
        && (
          if expected.vulkan then
            lib.hasInfix " -dev ${toString expected.device} -nt -np" script
          else
            !(lib.hasInfix " -dev " script)
        )
        && lib.hasInfix "bind = $mainMod SHIFT, R, exec, voice-dictate" (
          builtins.readFile config.xdg.configFile."hypr/hyprland.conf".source
        )
      );
    {
      voiceDictate = whisperExpected;
      vulkan = if whisperExpected then expected.vulkan else null;
      device = if whisperExpected then expected.device else null;
      driverFile = if whisperExpected then config.voiceDictate.vulkan.driverFile else null;
      fastLocalInput = if whisperExpected then config.voiceDictate.fastLocalInput else false;
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
    whisper = false;
  };
  samov-server.gui = false;
  samov-mac.gui = false;
}
