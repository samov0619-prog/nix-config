{
  lib,
  stdenv,
  fetchFromGitHub,
  makeWrapper,
  bash,
  procps,
  iproute2,
  iptables,
  openresolv,
  amneziawg-go,
}:
stdenv.mkDerivation (finalAttrs: {
  pname = "amneziawg-tools";
  version = "3.1.20260812";

  src = fetchFromGitHub {
    owner = "amnezia-vpn";
    repo = "amneziawg-tools";
    rev = "ee0f0a9aa34ff0a0da4b3433b9512781cfe02843";
    hash = "sha256-6GEb41ERhR0Hg3RbSyIHdXPSKaxugoFCmFS5S0UiZso=";
  };

  sourceRoot = "${finalAttrs.src.name}/src";
  outputs = [
    "out"
    "man"
  ];
  nativeBuildInputs = [ makeWrapper ];
  buildInputs = [ bash ];
  makeFlags = [
    "DESTDIR=${placeholder "out"}"
    "PREFIX=/"
    "WITH_BASHCOMPLETION=yes"
    "WITH_SYSTEMDUNITS=yes"
    "WITH_WGQUICK=yes"
  ];

  postFixup = ''
    substituteInPlace $out/lib/systemd/system/awg-quick@.service \
      --replace-fail /usr/bin $out/bin
  ''
  + lib.optionalString stdenv.hostPlatform.isLinux ''
    for file in $out/bin/*; do
      wrapProgram "$file" \
        --prefix PATH : ${
          lib.makeBinPath [
            procps
            iproute2
          ]
        } \
        --suffix PATH : ${
          lib.makeBinPath [
            iptables
            openresolv
          ]
        }
    done
  ''
  + lib.optionalString stdenv.hostPlatform.isDarwin ''
    for file in $out/bin/*; do
      wrapProgram "$file" --prefix PATH : ${lib.makeBinPath [ amneziawg-go ]}
    done
  '';

  strictDeps = true;

  meta = {
    description = "AmneziaWG 3.1 configuration tools";
    homepage = "https://amnezia.org";
    license = lib.licenses.gpl2Only;
    platforms = lib.platforms.unix;
    mainProgram = "awg";
  };
})
