let
  guiApplications = [
    "/(?i)^(google-chrome(-stable)?|firefox|blender|ardour(-?[0-9]+)?|org\\.ardour\\.Ardour)$/"
    "/(?i)^(nomacs|org\\.nomacs\\.ImageLounge|qbittorrent|org\\.qbittorrent\\.qBittorrent|FreeFileSync|FreesmLauncher|AmneziaVPN)$/"
  ];
in
{
  keypress_delay_ms = 0;
  throttle_ms = 0;
  modmap = [
    {
      name = "Lenovo left modifiers only";
      remap = {
        Alt_L = "Super_L";
        Super_L = "Alt_L";
      };
    }
  ];
  keymap = [
    {
      name = "Command editing in explicitly selected GUI apps";
      # No catch-all, terminals, games, launchers, password dialogs or empty context.
      application.only = guiApplications;
      remap = {
        "Super-c" = "Ctrl-c";
        "Super-v" = "Ctrl-v";
        "Super-x" = "Ctrl-x";
        "Super-a" = "Ctrl-a";
        "Super-z" = "Ctrl-z";
        "Super-Shift-z" = "Ctrl-Shift-z";
      };
    }
    {
      name = "Command find in explicitly selected GUI apps";
      application.only = guiApplications;
      # Do not inherit Shift/Ctrl/Alt into an unrequested find variant.
      exact_match = true;
      remap."Super-f" = "Ctrl-f";
    }
  ];
}
