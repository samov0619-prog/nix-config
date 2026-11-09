# Selected merged declarations and generated desktop text, no builds or activation.
let
  flake = builtins.getFlake (toString ../../..);
  lib = flake.inputs.nixpkgs.lib;
  check =
    name: gui:
    let
      config = flake.homeConfigurations.${name}.config;
      entry = config.xdg.desktopEntries.nvim-xdg or null;
      handlers = builtins.filter (
        package: lib.getName package == "nvim-xdg.desktop"
      ) config.home.packages;
      packages = map lib.getName config.home.packages;
    in
    assert builtins.length handlers == (if gui then 1 else 0);
    assert config.home.sessionVariables.EDITOR == "nvim";
    assert builtins.elem "neovim-unwrapped" packages;
    assert !(config.xdg.desktopEntries ? nvim);
    assert
      if gui then
        config.xdg.mimeApps.defaultApplications."text/plain" == [ "nvim-xdg.desktop" ]
        && entry.exec == "kitty -- nvim -- %F"
        && entry.terminal == false
        && entry.noDisplay
        && entry.mimeType == [ "text/plain" ]
        && builtins.elem "kitty" packages
        && config.xdg.desktopEntries.yazi-xdg.exec == "kitty -- yazi %f"
        && config.xdg.mimeApps.defaultApplications."text/html" == [ "google-chrome.desktop" ]
      else
        entry == null && !(config.xdg.mimeApps.defaultApplications ? "text/plain");
    {
      textHandler = gui;
      upstreamNeovimEntryUnchanged = true;
      # makeDesktopItem/writeTextFile text is available without realizing output.
      desktopText = if gui then (builtins.head handlers).text else null;
    };
in
lib.mapAttrs check {
  samov-laptop = true;
  samov-desktop = true;
  samov-laptop-next = true;
  samov-server = false;
  samov-mac = false;
}
