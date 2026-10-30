{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.programs.opencode.decisionSupport;
  plugin = pkgs.runCommand "opencode-agent-todo-plugin" { } ''
    mkdir -p "$out"
    cp ${./plugins/agent-todo.ts} "$out/index.ts"
  '';
in
{
  options.programs.opencode.decisionSupport.enable =
    lib.mkEnableOption "quiet decision guidance and explicitly confirmed local agent-todo notes";

  config = lib.mkIf cfg.enable {
    programs.opencode = {
      skills.decision-check = ./skills/decision-check/SKILL.md;
      settings.instructions = [ "${config.xdg.configHome}/opencode/decision-support.md" ];
      extraPackages = [ pkgs.git ];
    };
    xdg.configFile = {
      "opencode/decision-support.md".source = ./config/decision-support.md;
      "opencode/plugins/agent-todo-v2".source = plugin;
    };
  };
}
