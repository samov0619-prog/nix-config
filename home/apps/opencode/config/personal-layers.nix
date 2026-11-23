# Build-time file/settings definitions, not a runtime loader or an installer.
{
  todoEnabled ? true,
  personalDirectory ? "~/.config/opencode-local",
  todoDirectory ? "~/agent-todo",
}:
let
  read = builtins.readFile;
  instructions = import ./instructions.nix;
  home = import ./v2-settings.nix { };
  replaceRequired =
    before: after: text:
    let
      result = builtins.replaceStrings [ before ] [ after ] text;
    in
    assert result != text;
    result;
  commandDescriptions = {
    problem-brief = "Turn technical reports into clear, actionable issue briefs";
    delegated-review = "Delegate an independent read-only review with bounded native session recovery";
    delegated-review-chrome = "Independently audit Chrome-MCP test claims against recorded evidence and interventions";
    task-analysis = "Map task requirements to a minimal change plan and concrete checks";
    browser-verification = "Verify requested browser behavior against requirements with traceable evidence";
  };
  # These sources have one deliberately fixed header. Fail if metadata changes;
  # never inject YAML into a prompt or silently introduce a generic YAML parser.
  commandBody =
    name: description:
    let
      text = read (../commands + "/${name}.md");
      header = "---\ndescription: ${description}\nsubagent: false\n---\n\n";
      length = builtins.stringLength header;
    in
    assert builtins.substring 0 length text == header;
    builtins.substring length (-1) text;
  commandSettings = builtins.mapAttrs (name: description: {
    inherit description;
    subagent = false;
    template = "{file:commands/${name}.md}";
  }) commandDescriptions;
  reviewCommand =
    replaceRequired
      "Before the initial reviewer launch, read `review-analysis.md` from OpenCode's\nactive global config directory (normally `~/.config/opencode`; respect\n`XDG_CONFIG_HOME`), unless already loaded and unchanged."
      "Before the initial reviewer launch, read\n`~/.config/opencode-local/review-analysis.md` directly from the personal layer,\nunless already loaded and unchanged."
      (commandBody "delegated-review" commandDescriptions.delegated-review);
  commandFiles = builtins.listToAttrs (
    map (name: {
      name = "commands/${name}.md";
      value.text =
        if name == "delegated-review" then reviewCommand else commandBody name commandDescriptions.${name};
    }) (builtins.attrNames commandDescriptions)
  );
  manualDiscussion =
    replaceRequired "\n---\n\n# Discussion Map"
      "\nmetadata:\n  opencode/autoinvoke: false\n---\n\n# Discussion Map"
      (read ../skills/discussion-map/SKILL.md);
  sharedFiles = commandFiles // {
    "review-analysis.md".source = ./review-analysis.md;
    "review-system.md".source = ./review-system.md;
    "agents/research.md".text = home.agents.research.system;
    "skills/discussion-map/SKILL.md".text = manualDiscussion;
    "task-analysis.README.md".source = ../task-analysis.README.md;
    "browser-verification.README.md".source = ../browser-verification.README.md;
    "problem-brief.README.md".source = ../problem-brief.README.md;
  };
  sharedSettings = {
    "$schema" = "https://opencode.ai/config.json";
    instructions = [ "${personalDirectory}/AGENTS-personal.md" ];
    commands = commandSettings;
    skills = [ "${personalDirectory}/skills" ];
  };
  todo =
    if todoEnabled then
      import ./todo-settings.nix { inherit todoDirectory; }
    else
      {
        permissions = [ ];
        agents = { };
      };
  homeAgents = builtins.mapAttrs (
    name: agent:
    let
      localSystem =
        if
          builtins.elem name [
            "review"
            "research"
            "explore"
          ]
        then
          { system = "{file:agents/${name}.md}"; }
        else
          { };
    in
    agent
    // localSystem
    // (
      if builtins.hasAttr name todo.agents then
        {
          permissions = (agent.permissions or [ ]) ++ todo.agents.${name}.permissions;
        }
      else
        { }
    )
  ) home.agents;
  homeSettings =
    sharedSettings
    // {
      model = home.model;
      agents = homeAgents;
    }
    // (
      if todoEnabled then
        {
          permissions = todo.permissions;
          plugins = [ "./plugins/agent-todo" ];
        }
      else
        { }
    );
  corporateSettings = sharedSettings // {
    agents = {
      review = (builtins.removeAttrs home.agents.review [ "model" ]) // {
        system = "{file:agents/review.md}";
      };
      research = (builtins.removeAttrs home.agents.research [ "model" ]) // {
        system = "{file:agents/research.md}";
      };
    };
  };
  make = settings: files: {
    inherit settings;
    files =
      builtins.mapAttrs (
        _: file:
        if file ? text then
          file
          // {
            text = builtins.replaceStrings [ "~/.config/opencode-local" ] [ personalDirectory ] file.text;
          }
        else
          file
      ) files
      // {
        "opencode.jsonc".text = builtins.toJSON settings + "\n";
      };
  };
in
{
  home = make homeSettings (
    sharedFiles
    // {
      "AGENTS-personal.md".text = instructions.homePersonal;
      "agents/review.md".text = home.agents.review.system;
      "agents/explore.md".text = home.agents.explore.system;
    }
    // (
      if todoEnabled then
        {
          "plugins/agent-todo/index.ts".source = ../plugins/agent-todo.ts;
          "plugins/agent-todo/agent-todo-instructions.ts".source = ../plugins/agent-todo-instructions.ts;
          "plugins/agent-todo/agent-todo-review.ts".source = ../plugins/agent-todo-review.ts;
          "plugins/agent-todo/tui.tsx".source = ../plugins/agent-todo-tui.tsx;
        }
      else
        { }
    )
  );
  corporate = make corporateSettings (
    sharedFiles
    // {
      "AGENTS-personal.md".text = instructions.corporatePersonal;
      "agents/review.md".text = read ./review-agent.corporate.md;
    }
  );
}
