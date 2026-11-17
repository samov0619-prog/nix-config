# Selected actual merged NixOS attributes; no build, activation or packet probe.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/tests/test-aina-lan.nix
let
  flake = builtins.getFlake (toString ../../..);
  lib = flake.inputs.nixpkgs.lib;
  firewall = flake.nixosConfigurations.laptop.config.networking.firewall;
  rules = lib.filter (lib.hasPrefix "iptables ") (
    lib.splitString "\n" (lib.replaceStrings [ "\\\n" ] [ "" ] firewall.extraCommands)
  );
  gameTcpPorts = [
    8443
    8444
  ];
  gameUdpPorts = [
    4433
    4434
  ];
in
assert firewall.enable;
assert firewall.backend == "iptables";
assert builtins.length rules == 2;
assert lib.all (
  rule:
  lib.hasPrefix "iptables -w -A nixos-fw -i wlp0s20f3 " rule
  && lib.hasInfix "-s 192.168.0.0/24 -d 192.168.0.101 " rule
  && lib.hasSuffix "-j nixos-fw-accept" rule
) rules;
assert
  builtins.length (lib.filter (lib.hasInfix "-p tcp -m multiport --dports 8443,8444 ") rules) == 1;
assert
  builtins.length (lib.filter (lib.hasInfix "-p udp -m multiport --dports 4433,4434 ") rules) == 1;
assert !(builtins.elem "wlp0s20f3" firewall.trustedInterfaces);
assert lib.all (
  iface:
  !(lib.any (port: builtins.elem port iface.allowedTCPPorts) gameTcpPorts)
  && !(lib.any (port: builtins.elem port iface.allowedUDPPorts) gameUdpPorts)
  && !(lib.any (
    range: lib.any (port: range.from <= port && port <= range.to) gameTcpPorts
  ) iface.allowedTCPPortRanges)
  && !(lib.any (
    range: lib.any (port: range.from <= port && port <= range.to) gameUdpPorts
  ) iface.allowedUDPPortRanges)
) (builtins.attrValues firewall.allInterfaces);
{
  enabledIptablesFirewall = true;
  onlyWifiSourceSubnetDestinationAndFourPorts = true;
  noBroaderGamePortAllowances = true;
  inherit rules;
}
