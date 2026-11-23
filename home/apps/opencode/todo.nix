{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.programs.opencode.todo;
  plugin = pkgs.runCommand "opencode-agent-todo-plugin" { } ''
    mkdir -p "$out"
    cp ${./plugins/agent-todo.ts} "$out/index.ts"
    cp ${./plugins/agent-todo-instructions.ts} "$out/agent-todo-instructions.ts"
    cp ${./plugins/agent-todo-review.ts} "$out/agent-todo-review.ts"
    cp ${./plugins/agent-todo-tui.tsx} "$out/tui.tsx"
  '';
in
{
  imports = [
    (lib.mkRemovedOptionModule [ "programs" "opencode" "decisionSupport" "enable" ] ''
      Decision Support has been archived. Use programs.opencode.todo.enable for notes only.
    '')
  ];

  options.programs.opencode.todo.enable =
    lib.mkEnableOption "explicitly requested, natively confirmed local agent-todo notes for Build and Plan";

  config = lib.mkIf cfg.enable {
    programs.opencode = {
      # Tool scoping lives in the personal JSONC, not in the neutral base.
      extraPackages = [ pkgs.git ];
    };
    xdg.configFile."opencode-local/plugins/agent-todo".source = plugin;
  };
}
