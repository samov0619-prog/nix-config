{ upstream, pkgs }:
upstream.overrideAttrs (old: {
  patches = (old.patches or [ ]) ++ [ ./session-routing.patch ./session-attention.patch ];
  postPatch = (old.postPatch or "") + ''
    cp ${./model-routing.ts} packages/schema/src/local-model-routing.ts
    cp ${./routing-models.json} packages/schema/src/routing-models.json
    cp ${./session-attention.ts} packages/tui/src/session-attention.ts
  '';
  postInstall = (old.postInstall or "") + pkgs.lib.optionalString pkgs.stdenv.isLinux ''
    wrapProgram $out/bin/opencode \
      --prefix LD_LIBRARY_PATH : ${pkgs.lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib pkgs.alsa-lib pkgs.libpulseaudio ]}
  '';
})
