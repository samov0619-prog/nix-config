{ lib }:
let
  routes = builtins.fromJSON (builtins.readFile ../plugins/model-routing/routing-models.json);
  model =
    role:
    let
      ref = routes.${role} or routes."*";
    in
    "${ref.providerID}/${ref.id}#${ref.variant}";
  deny = action: {
    inherit action;
    resource = "*";
    effect = "deny";
  };
  analysisPermissions = map deny [
    "edit"
    "subagent"
    "todowrite"
  ];
  limit = {
    context = 1050000;
    input = 244000;
    output = 128000;
  };
  reasoning = efforts: {
    inherit limit;
    capabilities.reasoning = {
      supported = true;
      effort = efforts;
    };
    variants = map (effort: {
      id = effort;
      body.reasoning.effort = effort;
    }) efforts;
  };
in
{
  "$schema" = "https://opencode.ai/config.json";
  update = "disable";
  share = "disabled";
  model = model "*";
  policies = [
    {
      action = "provider.use";
      resource = "*";
      effect = "deny";
    }
    {
      action = "provider.use";
      resource = "openai";
      effect = "allow";
    }
    {
      action = "provider.use";
      resource = "opencode";
      effect = "allow";
    }
  ]
  ++
    map
      (resource: {
        action = "tool.use";
        inherit resource;
        effect = "deny";
      })
      [
        "shell:git push*"
        "shell:git pull*"
        "shell:git fetch*"
        "shell:git clone*"
        "shell:git ls-remote*"
        "shell:git remote update*"
        "shell:git * push*"
        "shell:git * pull*"
        "shell:git * fetch*"
        "shell:git * clone*"
        "shell:git * ls-remote*"
        "shell:git * remote update*"
        "shell:git remote show*"
        "shell:git remote set-head*--auto*"
        "shell:git * remote show*"
        "shell:git * remote set-head*--auto*"
        "shell:git remote add -f*"
        "shell:git remote add --fetch*"
        "shell:git * remote add -f*"
        "shell:git * remote add --fetch*"
      ]
  ++
    map
      (resource: {
        action = "tool.use";
        inherit resource;
        effect = "allow";
      })
      [
        # `remote show -n` only reads the cached local configuration.
        "shell:git remote show -n*"
        "shell:git remote show * -n*"
        "shell:git * remote show -n*"
        "shell:git * remote show * -n*"
      ];
  # Other tools retain the native V2 permission baseline. The shell hook also
  # disables Git transports and lazy fetch, independently of remembered Always.
  providers.openai.models = {
    "gpt-6.1-sol" = reasoning [
      "high"
      "xhigh"
    ];
    "gpt-6-luna" = reasoning [
      "low"
      "max"
    ];
  };
  agents = {
    build.model = model "build";
    plan = {
      model = model "plan";
      permissions = [ (deny "edit") ];
    };
    general.model = model "general";
    research = {
      model = model "research";
      mode = "subagent";
      description = "Separate evidence-based analysis when synthesis across sources or competing hypotheses is justified.";
      permissions = analysisPermissions;
      system = ''
        Investigate only the delegated question. Use tools for mechanical extraction.
        Do not edit files or delegate further. Respect the requested source and time scope.
        Return findings with file:line or URL references, distinguish facts from inference,
        and state uncertainty, unexamined sources and unresolved questions explicitly.
      '';
    };
    review = {
      model = model "review";
      mode = "subagent";
      description = "Independent read-only review of delegated changes or claims, with evidence and explicit coverage.";
      permissions = analysisPermissions;
      system = builtins.readFile ./review-system.md;
    };
    explore = {
      model = model "explore";
      permissions = analysisPermissions ++ [ (deny "skill") ];
      description = "Bounded read-only fact collection: paths, line references and explicit coverage gaps. Specify the source scope and question.";
      system = ''
        Collect facts only within the delegated source scope. Prefer glob for filenames,
        grep for targeted searches and read for selected passages. Use mechanical tools
        for counts and extraction. Do not edit, delegate or perform open-ended research.
        Return concise findings with paths and line numbers, what was searched, and
        explicit gaps or truncation. Absence from a partial search is not proof of absence.
        Stop once the requested facts are established; do not repeat unchanged retrievals.
      '';
    };
    # Keep ordinary compaction inherited (the pre-existing local choice).
    # /switch-paid explicitly applies the shared role table, including compaction.
    summary.model = model "summary";
    title.model = model "title";
  };
  compaction = {
    auto = true;
    buffer = 32000;
    keep.tokens = 15000;
  };
}
