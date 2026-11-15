# Selected declarations only: no builds, service changes, audio or GPU probes.
let
  flake = builtins.getFlake (toString ../../../../..);
  lib = flake.inputs.nixpkgs.lib;
  configs = lib.mapAttrs (_: home: home.config) flake.homeConfigurations;
  config = configs.samov-laptop;
  packages = map lib.getName config.home.packages;
  handyPackages = builtins.filter (p: lib.getName p == "handy") config.home.packages;
  handy = builtins.head handyPackages;
  upstream = flake.inputs.nixpkgs-unstable.legacyPackages.x86_64-linux.handy;
  settings = (import ../initial-settings.nix).settings;
  seed = config.home.activation.handyInitialSettings.data;
  source = builtins.head (
    builtins.match ".*install -m 600 ([^ ]+) .*" (lib.replaceStrings [ "\n" ] [ " " ] seed)
  );
  service = config.systemd.user.services.handy;
  hyprland = builtins.readFile config.xdg.configFile."hypr/hyprland.conf".source;
  archived = import ../../archive/whisper.nix;
  modelFile = "com.pais.handy/models/parakeet-tdt-0.6b-v3-Q4_K_M.gguf";
in
assert builtins.length handyPackages == 1;
assert !(builtins.elem "voice-dictate" packages);
assert !(config ? voiceDictate);
assert builtins.elem "wtype" packages;
assert handy.unwrapped.version == upstream.version;
assert handy.unwrapped.src.outPath == upstream.src.outPath;
assert lib.hasInfix "--set VK_DRIVER_FILES" handy.buildCommand;
assert lib.hasInfix "/run/opengl-driver/share/vulkan/icd.d/intel_icd.x86_64.json"
  handy.buildCommand;
assert lib.hasInfix "--prefix PATH" handy.buildCommand;
assert lib.any (lib.hasInfix "--start-hidden") (lib.toList service.Service.ExecStart);
assert service.Service.Restart == "on-failure";
assert service.Install.WantedBy == [ "graphical-session.target" ];
assert service.Unit.PartOf == [ "graphical-session.target" ];
assert service.Unit.ConditionEnvironment == "HYPRLAND_INSTANCE_SIGNATURE";
assert !(builtins.hasAttr "com.pais.handy/settings_store.json" config.xdg.dataFile);
assert lib.hasInfix "! -e" seed && lib.hasInfix "! -L" seed;
assert lib.hasInfix "run install -m 600" seed;
assert builtins.elem "reloadSystemd" config.home.activation.handyInitialSettings.before;
assert builtins.elem "writeBoundary" config.home.activation.handyInitialSettings.after;
assert lib.hasSuffix "-parakeet-tdt-0.6b-v3-Q4_K_M.gguf" (
  toString config.xdg.dataFile.${modelFile}.source
);
assert !config.xdg.dataFile.${modelFile}.force;
assert
  settings.selected_model
  == "handy-computer/parakeet-tdt-0.6b-v3-gguf/parakeet-tdt-0.6b-v3-Q4_K_M.gguf";
assert settings.transcribe_accelerator == "gpu";
assert settings.transcribe_gpu_device == ''["vulkan","id","0000:00:02.0"]'';
assert settings.model_unload_timeout == "min5";
assert !settings.always_on_microphone && !settings.lazy_stream_close;
assert !settings.autostart_enabled && settings.start_hidden && settings.show_tray_icon;
assert !settings.post_process_enabled && !settings.auto_submit;
assert settings.overlay_style == "none" && settings.overlay_position == "bottom";
assert settings.audio_feedback;
assert settings.selected_microphone == null;
assert settings.paste_method == "direct" && settings.typing_tool == "wtype";
assert settings.bindings.transcribe.current_binding == "super+shift+r";
assert settings.bindings.cancel.current_binding == "super+shift+t";
assert lib.hasInfix "bind = $mainMod SHIFT, R, exec, handy --toggle-transcription" hyprland;
assert lib.hasInfix "bind = $mainMod SHIFT, T, exec, handy --cancel" hyprland;
assert !(lib.hasInfix "bind = $mainMod CTRL SHIFT, Escape, exec, handy --cancel" hyprland);
assert !(lib.hasInfix "voice-dictate" hyprland);
assert !(lib.hasInfix "CTRL, SPACE" hyprland);
assert lib.hasInfix "name = hl-virtual-keyboard-wtype\n    keybinds = false" hyprland;
assert archived.voiceDictate.fastLocalInput && archived.voiceDictate.vulkan.enable;
assert archived.voiceDictate.vulkan.device == 0;
assert
  archived.voiceDictate.vulkan.driverFile
  == "/run/opengl-driver/share/vulkan/icd.d/intel_icd.x86_64.json";
assert lib.all
  (
    name:
    let
      other = configs.${name};
    in
    !(other.systemd.user.services ? handy)
    && !(builtins.hasAttr modelFile other.xdg.dataFile)
    && !(builtins.any (p: lib.getName p == "handy") other.home.packages)
    && !(other.home.activation ? handyInitialSettings)
  )
  [
    "samov-laptop-old"
    "samov-desktop"
    "samov-server"
    "samov-mac"
  ];
{
  lenovoOnly = true;
  nativeGraphicalService = true;
  wrappedUnstableHandy = upstream.version;
  whisperArchivedOnLenovo = true;
  ctrlSpaceNotGrabbedByHyprland = true;
  wtypeCannotTriggerCompositorBinds = true;
  # Data for a small execution test of the actual generated activation snippet.
  activationFixture = {
    script = seed;
    inherit source;
    settings = import ../initial-settings.nix;
    dataHome = config.xdg.dataHome;
  };
}
