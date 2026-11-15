# Archived Lenovo alternative, not imported by the active leaf.
# Shared Whisper implementation/tests remain active on Acer and desktop.
{
  imports = [ ../../../modules/voice-dictate ];
  voiceDictate.fastLocalInput = true;
  voiceDictate.vulkan = {
    enable = true;
    device = 0;
    driverFile = "/run/opengl-driver/share/vulkan/icd.d/intel_icd.x86_64.json";
  };
  # To restore, also remove Handy's import/bindings and restore the former
  # Super+Shift+R -> voice-dictate binding. See the archived audit.
}
