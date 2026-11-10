# Native HM agent lifecycle; no agent startup, prompts or D-Bus calls.
let
  flake = builtins.getFlake (toString ../../..);
in
builtins.mapAttrs (
  name: home:
  let
    config = home.config;
    gui = builtins.elem name [
      "samov-laptop-old"
      "samov-desktop"
      "samov-laptop"
    ];
    agent = config.services.hyprpolkitagent;
    unit = config.systemd.user.services.hyprpolkitagent or null;
  in
  assert agent.enable == gui;
  assert !config.services.polkit-gnome.enable;
  assert
    if gui then
      config.wayland.systemd.target == "graphical-session.target"
      && unit.Unit.PartOf == [ "graphical-session.target" ]
      && unit.Unit.After == [ "graphical-session.target" ]
      && unit.Install.WantedBy == [ "graphical-session.target" ]
      && unit.Service.ExecStart == [ "${agent.package}/libexec/hyprpolkitagent" ]
      && !config.wayland.windowManager.hyprland.systemd.enable
    else
      unit == null;
  {
    agentEnabled = gui;
    graphicalSessionLifecycle = gui;
    competingGnomeAgent = false;
  }
) flake.homeConfigurations
