{ xremap-flake, ... }:
# Мак-модель модификаторов на Acer. Всё живёт в одном источнике правды —
# xremap на уровне evdev (ниже XKB), поэтому правила слой-независимы: русская
# раскладка отдельных правил не требует, matching идёт по keycode (KEY_C и т.п.).
#
# Физические свитчи (не колпачки!) → целевое поведение:
#   LeftMeta  (pos3, слева от пробела-2)        → Alt   (Option)
#   LeftAlt   (pos4, слева у пробела)            → Super (Command)
#   RightAlt  (pos6, справа у пробела)           → Super (Command)
#   Compose   (pos7, Menu/Application)           → Alt   (Option)
#   LeftCtrl / RightCtrl / Fn                    → без изменений
#
# ВАЖНО: имена KEY_COMPOSE / KEY_MENU для клавиши Application зависят от железа.
# Проверь `wev` (нажми Menu-клавишу) или лог сервиса; при "unknown key" поправь токен.
{
  imports = [ xremap-flake.homeManagerModules.default ];

  services.xremap = {
    enable = true;
    withWlroots = true; # оконный контекст через Hyprland IPC (нужно для терминального правила)

    config = {
      # --- Слой 1: статическая перестановка модификаторов ---
      modmap = [
        {
          name = "mac-modifier-positions";
          remap = {
            "Super_L" = "Alt_L"; # физ. Super → Option
            "Alt_L" = "Super_L"; # физ. Alt (у пробела) → Command
            "Alt_R" = "Super_L"; # физ. AltGr (у пробела справа) → Command
            "KEY_COMPOSE" = "Alt_L"; # Menu/Application → Option
          };
        }
      ];

      # --- Слой 2: смысл Command по приложению ---
      keymap = [
        {
          # GUI: Command = Ctrl-эквивалент (copy/paste/cut/undo/redo/select-all)
          name = "cmd-gui";
          application.not = [ "Alacritty" "kitty" "foot" ];
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
          # Терминал: только copy/paste → Ctrl-Shift-*.
          # Ctrl НЕ трогаем нигде → настоящий Ctrl-C = SIGINT цел.
          # Z/A/X здесь НЕ мапим специально (Ctrl-Z=SIGTSTP, Ctrl-A=начало строки).
          name = "cmd-terminal";
          application.only = [ "Alacritty" "kitty" "foot" ];
          remap = {
            "Super-c" = "Ctrl-Shift-c";
            "Super-v" = "Ctrl-Shift-v";
          };
        }
      ];
    };
  };
}
