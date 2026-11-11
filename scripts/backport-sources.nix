# Only source paths, no package builds/IFD or Home Manager closure evaluation.
# The caller uses offline/read-only lock flags; this is not a network sandbox.
{ root, names }:
let
  f = builtins.getFlake root;
  system = builtins.currentSystem;
  stable = import f.inputs.nixpkgs { inherit system; };
  unstable = import f.inputs.nixpkgs-unstable { inherit system; };
  sources = {
    kernel = f.nixosConfigurations.laptop.config.boot.kernelPackages.kernel.src;
    nvidia = f.nixosConfigurations.laptop.config.boot.kernelPackages.nvidiaPackages.latest.open.src;
    pipewire = stable.pipewire.src;
    filemanager = (stable.callPackage ../pkgs/filemanager1-common { }).src;
    amnezia = (stable.callPackage ../pkgs/amnezia-vpn { }).src;
    onionbell = (stable.callPackage ../pkgs/onionbell { }).src;
    yazi-compress = unstable.yaziPlugins.compress.src;
    opencode = f.inputs.opencode;
    waybar = stable.waybar.src;
    bluez-stable = stable.bluez.src;
    portal-stable = stable.xdg-desktop-portal.src;
  };
in
builtins.listToAttrs (
  map (name: {
    inherit name;
    value = toString sources.${name};
  }) names
)
