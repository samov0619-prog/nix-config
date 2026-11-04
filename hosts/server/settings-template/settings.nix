# A safe default for non-server hosts, not a deployable VPS configuration.
throw ''
  Server settings were not selected. Keep real settings outside this repository:
    ~/.config/nix-config/server/settings.nix
  Pass --override-input server-settings path:/absolute/path/to/server-settings
  to server evaluation/build/deploy commands. The directory must contain settings.nix.
  hosts/server/settings.nix is an example only. Never put private keys in this input.
''
