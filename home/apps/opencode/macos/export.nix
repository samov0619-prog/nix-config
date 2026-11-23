# Pure, explicit export definition. No derivations, runtime loader or installer.
{
  personalDirectory ? "~/.config/opencode-local",
}:
let
  instructions = import ../config/instructions.nix;
  personal = (import ../config/personal-layers.nix { inherit personalDirectory; }).corporate;
  commonPaths = [
    "opencode.jsonc"
    ".gitignore"
    "package.json"
    "package-lock.json"
    "agent-skills-review-checklist.md"
    "plugins/git-offline/index.ts"
    "plugins/permission-stats/index.ts"
    "plugins/permissions/state.ts"
    "plugins/permissions/tui.ts"
    "scripts/task-report.py"
    "skills/git-regression-rollback/SKILL.md"
    "skills/code-patterns-skill-generator/SKILL.md"
  ];
  historyPaths = [
    "INSTALL.md"
    "acceptance/goals-and-approach.md"
    "acceptance/requirements/candidate.mjs"
    "acceptance/requirements/SPEC.md"
    "acceptance/requirements/EVALUATION.md"
  ];
  sources =
    prefix: root: paths:
    builtins.listToAttrs (
      map (name: {
        name = "${prefix}/${name}";
        value.source = root + "/${name}";
      }) paths
    );
in
{
  files =
    (sources "opencode" ./sources/common commonPaths)
    // (sources "opencode-local/update-2026-11-16" ./sources/personal-history/update-2026-11-16
      historyPaths
    )
    // builtins.listToAttrs (
      map (name: {
        name = "opencode-local/${name}";
        value = personal.files.${name};
      }) (builtins.attrNames personal.files)
    )
    // {
      "opencode/AGENTS.md".text = instructions.corporate;
      "opencode/README.md".source = ./COMMON.md;
      "opencode/agents.README.md".source = ./agents.README.md;
      "opencode/skills/task-summary-log/SKILL.md".source = ../skills/task-summary-log/SKILL.md;
      "opencode-local/README.md".source = ./PERSONAL.md;
      "opencode-local/delegated-review.README.md".source = ./DELEGATED-REVIEW.md;
      "opencode-local/delegated-review-chrome.README.md".source = ./DELEGATED-REVIEW-CHROME.md;
      "INSTALL.md".source = ./INSTALL.md;
      "UPGRADE-240.md".source = ../UPGRADE-240.md;
    };
}
