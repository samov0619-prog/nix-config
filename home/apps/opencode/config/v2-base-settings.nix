# The maintained home provider/safety configuration, without Samov's role routing.
{ ... }:
builtins.removeAttrs (import ./v2-settings.nix { }) [
  "model"
  "agents"
]
