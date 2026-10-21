# Home OpenCode: native OpenAI routing, compaction, skills and manual accounting.
# Verified against OpenCode 1.19.3; see BENCHMARK.md for runtime checks.
{
  pkgs,
  pkgsUnstable,
  lib,
  config,
  ...
}:
let
  # Independent role defaults; each accepts high / xhigh / max. See README.md.
  workEffort = "high"; # build / general / research / review
  planEffort = "xhigh";
  workAgent = {
    model = "openai/gpt-6.1-sol";
    variant = workEffort;
  };
  planAgent = {
    model = "openai/gpt-6.1-sol-plan";
    variant = planEffort;
  };
  summaryAgent = {
    # Native alias of the same API model, isolated from the primary variant.
    model = "openai/gpt-6.1-sol-high";
    variant = "high";
  };
  solModel = effort: {
    limit = compactionLimit;
    options.reasoningEffort = effort;
    reasoning_options = [
      {
        type = "effort";
        values = [ effort ];
      }
    ];
  };
  analysisPermission = {
    edit = "deny";
    task = "deny";
    todowrite = "deny";
  };
  # A soft input ceiling for native overflow, not the provider's physical limit.
  # overflow.ts: 244000 - compaction.reserved (32000) = 212000 tokens.
  compactionLimit = {
    context = 1050000;
    input = 244000;
    output = 128000;
  };
in
{
  assertions = [
    {
      assertion =
        builtins.all
          (
            effort:
            builtins.elem effort [
              "high"
              "xhigh"
              "max"
            ]
          )
          [
            workEffort
            planEffort
          ];
      message = "Home OpenCode workEffort and planEffort must be high, xhigh or max.";
    }
  ];

  programs.opencode = {
    enable = true;
    # The native file-watcher addon needs libstdc++ at dlopen time. nix-ld cannot
    # fix an already patched Nix binary; keep the library path in its wrapper.
    package = pkgsUnstable.opencode.overrideAttrs (old: {
      nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [ pkgs.makeWrapper ];
      postFixup = (old.postFixup or "") + ''
        for b in $out/bin/.opencode-wrapped__ $out/bin/opencode; do
          [ -e "$b" ] && wrapProgram "$b" \
            --prefix LD_LIBRARY_PATH : ${lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib ]}
        done
      '';
    });

    settings = {
      "$schema" = "https://opencode.ai/config.json";
      autoupdate = false;
      share = "disabled";
      # enabled_providers = [ "openai" ];
      model = workAgent.model;
      small_model = "openai/gpt-6-luna";
      provider.openai.models = {
        "gpt-6.1-sol" = solModel workEffort;
        # The TUI remembers a selected variant per model ID, not per agent.
        # A native alias keeps plan and work defaults independent.
        "gpt-6.1-sol-plan" = solModel planEffort // {
          id = "gpt-6.1-sol";
          name = "GPT-6.1 Sol (plan)";
        };
        # Compaction inherits the source variant in 1.19.3. This alias exposes
        # only High, so a source XHigh/Max cannot override it.
        "gpt-6.1-sol-high" = solModel "high" // {
          id = "gpt-6.1-sol";
          name = "GPT-6.1 Sol High (compaction/summary)";
        };
        "gpt-6-luna" = {
          limit = compactionLimit;
          options.reasoningEffort = "low";
          reasoning_options = [
            {
              type = "effort";
              values = [ "low" ];
            }
          ];
        };

        "gpt-6-luna-max" = {
          id = "gpt-6-luna";
          name = "GPT-6 Luna Max (explore)";
          limit = compactionLimit;
          options.reasoningEffort = "max";
          reasoning_options = [
            {
              type = "effort";
              values = [ "max" ];
            }
          ];
        };
      };
      agent = {
        build = workAgent;
        plan = planAgent // {
          permission.edit = "deny";
        };
        general = workAgent;
        research = workAgent // {
          mode = "subagent";
          description = "Separate evidence-based analysis when synthesis across sources or competing hypotheses is justified.";
          permission = analysisPermission;
          prompt = ''
            Investigate only the delegated question. Use tools for mechanical extraction.
            Do not edit files or delegate further. Respect the requested source and time scope.
            Return findings with file:line or URL references, distinguish facts from inference,
            and state uncertainty, unexamined sources and unresolved questions explicitly.
          '';
        };
        review = workAgent // {
          mode = "subagent";
          description = "Independent read-only review when a separate correctness or regression analysis is justified.";
          permission = analysisPermission;
          prompt = ''
            Review only the delegated change or claim. Do not edit files or delegate further.
            Prioritize concrete correctness issues and regressions, with file:line evidence,
            impact and a reproducible check where possible. Separate verified findings from
            hypotheses; report coverage gaps and say explicitly when no issue was found.
          '';
        };
        explore = {
          model = "openai/gpt-6-luna-max";
          variant = "max";
          permission = analysisPermission // {
            skill = "deny";
          };
          description = "Bounded read-only fact collection: paths, line references and explicit coverage gaps. Specify the source scope and question.";
          prompt = ''
            Collect facts only within the delegated source scope. Prefer glob for filenames,
            grep for targeted searches and read for selected passages. Use mechanical tools
            for counts and extraction. Do not edit, delegate or perform open-ended research.
            Return concise findings with paths and line numbers, what was searched, and
            explicit gaps or truncation. Absence from a partial search is not proof of absence.
            Stop once the requested facts are established; do not repeat unchanged retrievals.
          '';
        };
        compaction = summaryAgent;
        summary = summaryAgent;
        title = {
          model = "openai/gpt-6-luna";
          variant = "low";
        };
      };
      compaction = {
        auto = true;
        prune = false;
        reserved = 32000;
        preserve_recent_tokens = 15000;
      };
      permission = {
        # Access outside the current project remains guarded independently.
        read = "allow";
        glob = "allow";
        grep = "allow";
        list = "allow";
        external_directory = "ask";
        edit = "ask";
        bash = {
          "*" = "ask";
          "git status*" = "allow";
          "git log*" = "allow";
          "git diff*" = "allow";
          "git show*" = "allow";
          "git branch --show-current*" = "allow";
          "git remote*" = "allow";
          "git merge-base*" = "allow";
          "git rev-list*" = "allow";
          "git rev-parse*" = "allow";
          "git ls-files*" = "allow";
          "git config --get*" = "allow";
        };
      };
    };

    extraPackages = with pkgs; [
      python3
      ripgrep
      fd
    ];
    skills.discussion-map = ./discussion-map-skill.md;
    skills.git-regression-rollback = ./git-regression-rollback-skill.md;
  };

  xdg.configFile."opencode/AGENTS.md".source = ./AGENTS.md;
  xdg.configFile."opencode/plugin/permission-stats.ts".source = ./permission-stats.ts;
  xdg.configFile."opencode/plugin/completion-sound.ts".source = pkgs.replaceVars ./completion-sound.ts {
    player = "${pkgs.pipewire}/bin/pw-play";
    sound = ./completion-sound.mp3;
    errorSound = ./error-sound.mp3;
  };
  xdg.configFile."opencode/sounds/completion.mp3".source = ./completion-sound.mp3;
  xdg.configFile."opencode/sounds/error.mp3".source = ./error-sound.mp3;

  home.packages = [
    (pkgs.writeShellApplication {
      name = "opencode-task-report";
      runtimeInputs = [ pkgs.python3 ];
      text = ''
        exec python3 ${./task-report.py} "$@"
      '';
    })
    (pkgs.writeShellApplication {
      name = "opencode-permission-stats";
      runtimeInputs = with pkgs; [
        coreutils
        gawk
        jq
      ];
      text = ''
        history="${config.xdg.stateHome}/opencode/permission-history.jsonl"
        if test ! -s "$history"; then
          printf '%s\n' "No recorded permission decisions yet."
          exit 0
        fi

        printf '%s\n' "Permission decisions by operation, pattern, and response:"
        jq -rs '
          group_by([.permission, (.patterns | join("\u001f")), .response])[]
          | [.[0].permission, (.[0].patterns | join(", ")), .[0].response, length]
          | @tsv
        ' "$history" | sort -t $'\t' -k1,1 -k2,2 -k4,4nr \
          | awk -F '\t' 'BEGIN { print "PERMISSION\tPATTERNS\tRESPONSE\tCOUNT" } { print }'
      '';
    })
  ];
}
