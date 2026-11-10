{
  lib,
  callPackage,
  runCommand,
  makeWrapper,
  replaceVars,
  writeShellApplication,
  bash,
  coreutils,
  iproute2,
  iptables,
  openresolv,
  procps,
  python3,
}:
let
  backend = callPackage ../amneziawg-3.1/go.nix { };
  tools = callPackage ../amneziawg-3.1/tools.nix { };
  # A separate quick script: the server's kernel-oriented tools stay unchanged.
  quick = runCommand "installer-vpn-quick" { nativeBuildInputs = [ makeWrapper ]; } ''
    install -Dm755 ${tools.src}/src/wg-quick/linux.bash "$out/bin/installer-vpn-quick"
    substituteInPlace "$out/bin/installer-vpn-quick" \
      --replace-fail '#!/bin/bash' '#!${bash}/bin/bash' \
      --replace-fail '# ~~ function override insertion point ~~' "$(cat ${./userspace-only.bash})"
    wrapProgram "$out/bin/installer-vpn-quick" \
      --set WG_QUICK_USERSPACE_IMPLEMENTATION ${backend}/bin/amneziawg-go \
      --set LOG_LEVEL silent \
      --prefix PATH : ${
        lib.makeBinPath [
          bash
          coreutils
          iproute2
          iptables
          openresolv
          procps
          tools
        ]
      }
  '';
  script = replaceVars ./installer-vpn.py {
    inherit
      quick
      tools
      iproute2
      python3
      ;
    runtimePath = lib.makeBinPath [
      bash
      coreutils
      iproute2
      iptables
      openresolv
      procps
      tools
    ];
  };
in
writeShellApplication {
  name = "installer-vpn";
  text = ''
    exec ${python3}/bin/python3 -I ${script} "$@"
  '';
  passthru = { inherit backend tools quick; };
  meta = {
    description = "Temporary AWG 3.1 full tunnel for a NixOS live installer";
    license = lib.licenses.mit;
    platforms = lib.platforms.linux;
    mainProgram = "installer-vpn";
  };
}
