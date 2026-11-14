# OpenCode V2: pinned upstream package, native config/audio and small local plugins.
{
  pkgs,
  lib,
  config,
  opencodePackage,
  ...
}:
let
  json = pkgs.formats.json { };
  settings = import ./config/v2-settings.nix { inherit lib; };
  # Static, local reminder: never inspect credentials or query GitHub at evaluation.
  quotaApiReminder = ''
    OPENCODE QUOTA API: percentages currently require Codex OAuth (legacy).
    Token sharing shows "Limits: not exposed by token sharing"; Active and manual checkpoints still work.
    When updating OpenCode, recheck https://github.com/openai/codex/issues/54219 and the OpenAI API docs.
    Remove this reminder only after real token-sharing window percentages/reset times,
    account switching and per-window warnings are verified. See home/apps/opencode/README.md.
  '';
  # Bun resolves imports relative to the real store path of tui.ts. Keep the
  # module and its dependencies together, not as separate HM file symlinks.
  modelRoutingPlugin = pkgs.runCommand "opencode-model-routing-plugin" { } ''
    mkdir -p "$out"
    cp ${./plugins/model-routing/tui.ts} "$out/tui.ts"
    cp ${./plugins/model-routing/model-routing.ts} "$out/model-routing.ts"
    cp ${./plugins/model-routing/routing-models.json} "$out/routing-models.json"
  '';
  limitsPlugin = pkgs.runCommand "opencode-limits-plugin" { } ''
    mkdir -p "$out"
    cp ${./plugins/limits/index.ts} "$out/index.ts"
    cp ${./plugins/limits/tui.tsx} "$out/tui.tsx"
    cp ${./plugins/limits/policy.ts} "$out/policy.ts"
    cp ${./plugins/limits/rpc.ts} "$out/rpc.ts"
    cp ${./plugins/limits/writer.ts} "$out/writer.ts"
  '';
  permissionsPlugin = pkgs.runCommand "opencode-permissions-plugin" { } ''
    mkdir -p "$out"
    cp ${./plugins/permissions/tui.ts} "$out/tui.ts"
    cp ${./plugins/permissions/state.ts} "$out/state.ts"
  '';
  # Keep runtime imports/assets in the plugin closure, not in the flake's
  # temporary source snapshot (replaceVars does not retain those references).
  quietUrgencyPlugin = pkgs.runCommand "opencode-quiet-urgency-plugin" { } ''
    mkdir -p "$out"
    cp ${./plugins/quiet-urgency.ts} "$out/tui.ts"
    cp ${./patches/session-attention.ts} "$out/session-attention.ts"
    cp ${./scripts/silent-attention.py} "$out/silent-attention.py"
  '';
  # V2 checks realpath(server entrypoint) is inside realpath(plugin root).
  # A directory symlink to ordinary store files passes; an index.ts symlink
  # escaping a real HM directory is silently filtered by native discovery.
  serverPlugin =
    name: source:
    pkgs.runCommand "opencode-${name}-plugin" { } ''
      mkdir -p "$out"
      cp ${source} "$out/index.ts"
    '';
  permissionSound =
    pkgs.runCommand "opencode-permission.wav"
      {
        nativeBuildInputs = [ pkgs.ffmpeg-headless ];
      }
      ''
        ffmpeg -v error -i ${pkgs.sound-theme-freedesktop}/share/sounds/freedesktop/stereo/bell.oga \
          -c:a pcm_s16le -f wav "$out"
      '';
  cliDefaults = json.generate "opencode-cli-defaults.json" {
    "$schema" = "https://opencode.ai/v2/cli.json";
    attention = {
      sound = true;
      volume = 0.4;
      sounds = {
        permission = "${config.xdg.configHome}/opencode/sounds/permission.wav";
        done = "${config.xdg.configHome}/opencode/sounds/completion.mp3";
        error = "${config.xdg.configHome}/opencode/sounds/error.mp3";
      };
    };
  };
in
{
  imports = [ ./decision-support.nix ];
  warnings = [ quotaApiReminder ];
  # Also show for a cached generation's activation; warnEcho uses yellow in a
  # color-capable terminal and respects NO_COLOR. No state change or network.
  home.activation.opencodeQuotaApiReminder = lib.hm.dag.entryBefore [ "writeBoundary" ] ''
    warnEcho ${lib.escapeShellArg quotaApiReminder}
  '';
  # Explicit home-only opt-in; set false to disable guidance and todo tools.
  programs.opencode.decisionSupport.enable = lib.mkDefault true;
  programs.opencode = {
    enable = true;
    package = opencodePackage;
    inherit settings;
    extraPackages = with pkgs; [
      python3
      ripgrep
      fd
    ];
    skills.discussion-map = ./skills/discussion-map/SKILL.md;
    skills.git-regression-rollback = ./skills/git-regression-rollback/SKILL.md;
    # V2 uses a mutable cli.json; the old tui.json/plugin option stays empty.
  };

  # Native /settings writes cli.json atomically. Seed it once rather than putting
  # an immutable Home Manager symlink in the way of sound/volume preferences.
  home.activation.opencodeCliDefaults = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    if [ ! -e "${config.xdg.configHome}/opencode/cli.json" ]; then
      run mkdir -p "${config.xdg.configHome}/opencode"
      run install -m 600 ${cliDefaults} "${config.xdg.configHome}/opencode/cli.json"
    fi
  '';

  xdg.configFile = {
    # Keep HM's merged settings/source; only rename the installed config path.
    "opencode/opencode.json".target = "opencode/opencode.jsonc";
    "opencode/AGENTS.md".source = ./config/AGENTS.md;
    "opencode/commands/delegated-review.md".source = ./commands/delegated-review.md;
    "opencode/commands/delegated-review-chrome.md".source = ./commands/delegated-review-chrome.md;
    "opencode/commands/problem-brief.md".source = ./commands/problem-brief.md;
    "opencode/problem-brief.README.md".source = ./problem-brief.README.md;
    "opencode/plugins/model-routing" = {
      source = modelRoutingPlugin;
      # Preserve the existing managed leaf paths during upgrades. Each link
      # resolves into the same store directory, so relative imports still work.
      recursive = true;
    };
    # New directory paths allow HM to clean the old managed leaf links without
    # colliding with their existing parent directories during upgrade.
    "opencode/plugins/git-offline-v2".source = serverPlugin "git-offline" ./plugins/git-offline.ts;
    "opencode/plugins/permission-stats-v2".source =
      serverPlugin "permission-stats" ./plugins/permission-stats.ts;
    "opencode/plugins/model-calls-v2" = {
      # Optional routing/effort/retry diagnostics. Set true to record future calls;
      # task-report works without it, and disabling does not delete old journals.
      enable = false;
      source = serverPlugin "model-calls" ./plugins/model-calls.ts;
    };
    "opencode/plugins/limits-v2".source = limitsPlugin;
    "opencode/plugins/permissions".source = permissionsPlugin;
    "opencode/plugins/skill-stats-v2".source = serverPlugin "skill-stats" ./plugins/skill-stats.ts;
    "opencode/sounds/permission.wav".source = permissionSound;
    "opencode/sounds/completion.mp3".source = ./sounds/completion-sound.mp3;
    "opencode/sounds/error.mp3".source = ./sounds/error-sound.mp3;
  }
  // lib.optionalAttrs pkgs.stdenv.isLinux {
    "opencode/plugins/workspace-context/tui.ts".source = ./plugins/workspace-context.ts;
    "opencode/plugins/quiet-urgency" = {
      source = quietUrgencyPlugin;
      recursive = true;
    };
  };

  home.packages = [
    (pkgs.writeShellApplication {
      name = "opencode-task-report";
      runtimeInputs = [ pkgs.python3 ];
      text = ''exec python3 ${./scripts/task-report.py} "$@"'';
    })
    (pkgs.writeShellApplication {
      name = "opencode-skill-stats";
      runtimeInputs = [ pkgs.python3 ];
      text = ''exec python3 ${./scripts/skill-stats.py} "$@"'';
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
