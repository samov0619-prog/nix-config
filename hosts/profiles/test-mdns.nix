# Selected merged attributes and actual output composition; no builds or network probes.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/profiles/test-mdns.nix
let
  flake = builtins.getFlake (toString ../..);
  lib = flake.inputs.nixpkgs.lib;
  # Capture actual flake module lists without evaluating external VPS settings.
  composition = (import ../../flake.nix).outputs (
    flake.inputs
    // {
      self = composition;
      nixpkgs = flake.inputs.nixpkgs // {
        lib = lib // {
          nixosSystem = args: args;
        };
      };
    }
  );
  workstations = [
    "laptop"
    "desktop"
    "laptop-next"
    "desktop-next"
  ];
  check =
    host:
    let
      config = flake.nixosConfigurations.${host}.config;
      avahi = config.services.avahi;
    in
    assert builtins.elem ./mdns.nix composition.nixosConfigurations.${host}.modules;
    assert avahi.enable;
    assert avahi.nssmdns4;
    assert !avahi.nssmdns6;
    assert avahi.openFirewall;
    assert builtins.elem 5353 config.networking.firewall.allowedUDPPorts;
    assert builtins.elem "mdns4_minimal [NOTFOUND=return]" config.system.nssDatabases.hosts;
    assert !avahi.publish.enable;
    assert !avahi.reflector;
    assert !avahi.wideArea;
    assert !avahi.allowPointToPoint;
    assert builtins.elem "multi-user.target" config.systemd.services.avahi-daemon.wantedBy;
    {
      ipv4LocalNameResolution = true;
      mdnsFirewallOpen = true;
      publishingDisabled = true;
    };
in
assert lib.all (host: !(builtins.elem ./mdns.nix composition.nixosConfigurations.${host}.modules)) [
  "server"
  "server-installer"
];
{
  workstations = lib.genAttrs workstations check;
  serverAndInstallerDoNotImportMdns = true;
}
