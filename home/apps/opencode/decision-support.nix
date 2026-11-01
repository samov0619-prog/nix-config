{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.programs.opencode.decisionSupport;
  todoDirectory = "${config.home.homeDirectory}/agent-todo";
  plugin = pkgs.runCommand "opencode-agent-todo-plugin" { } ''
    mkdir -p "$out"
    cp ${./plugins/agent-todo.ts} "$out/index.ts"
    cp ${./plugins/agent-todo-review.ts} "$out/agent-todo-review.ts"
    cp ${./plugins/agent-todo-tui.tsx} "$out/tui.tsx"
  '';
in
{
  options.programs.opencode.decisionSupport.enable =
    lib.mkEnableOption "quiet decision guidance and explicitly confirmed local agent-todo notes";

  config = lib.mkIf cfg.enable {
    programs.opencode = {
      skills.decision-check = ./skills/decision-check/SKILL.md;
      settings.instructions = [ "${config.xdg.configHome}/opencode/decision-support.md" ];
      settings.permissions =
        map
          (resource: {
            action = "read";
            inherit resource;
            effect = "allow";
          })
          [
            todoDirectory
            "${todoDirectory}/*"
          ];
      extraPackages = [ pkgs.git ];
    };
    xdg.configFile = {
      "opencode/decision-support.md".source = ./config/decision-support.md;
      "opencode/plugins/agent-todo-v2".source = plugin;
    };
  };
}
