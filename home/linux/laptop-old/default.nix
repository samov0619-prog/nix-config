{
  ...
}:
{
  imports = [
    ../core-set
    ../gui-set
    ../modules/xremap
    ../../modules/voice-dictate
  ];

  xdg.configFile."hypr/hyprland.conf".source = ./hyprland.conf;
  xdg.configFile."waybar/config.jsonc".source = ./waybar-config.jsonc;

  # Vulkan index 0 is Intel HD 520; 1 is the NVIDIA 940MX.
  voiceDictate.vulkan = {
    enable = true;
    device = 1;
  };
}
