# Home Environment Rules (Home Manager on Linux or macOS)

## Nix and Fish Environments

- For user-facing temporary Nix environments, preserve the user's normal Fish,
  config, history, Atuin and Zoxide. For interactive package environments, prefer
  `nsh <package> [package ...]` (stable) or `nsh unstable <package> [package ...]`.
  This HM-managed Fish function uses the local flake's nixpkgs inputs for the
  native Linux/Darwin platform, without host-specific overlays/settings. It reads
  `~/nix-config` by default; exported `NSH_FLAKE` selects another absolute flake path.
  If `nsh` is unavailable, use
  `nix shell nixpkgs#<package> --command (status fish-path) --interactive`;
  this fallback follows the registry, not necessarily the local flake's versions.
  `(status fish-path)` is expanded by the original user Fish before Nix runs.
- Do not clear the environment, disable shell configuration, or override HOME/XDG
  paths without a concrete need and an explanation. `nix shell` is not a security
  sandbox; use appropriate isolation when the task requires it.
- For one-shot commands, run the program directly with `--command`, without an
  unnecessary nested shell.
- `nsh` and the interactive Fish template are for user-facing interactive commands,
  not the agent's shell tool, which runs Bash, or non-interactive one-shot commands.
- Make Nix commands safe to copy from `~`: use an absolute flake path or explicitly
  set the working directory before relative flake references such as `./.`.

## Home Working Directories

- Put disposable files in one uniquely named task directory under `/tmp/opencode`;
  reuse it within the task. Respect tool-owned storage and project-required
  build/test directories instead of relocating them.
- Do not use `~/.opencode` as general scratch space. Use `~/.opencode/plan` only
  for explicitly requested plans/handoffs, subject to the active mode's rules.

## Home Git Convention

- ONLY ask for a task or ticket number when that history establishes it as the user's convention.
