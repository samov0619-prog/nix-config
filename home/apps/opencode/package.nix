{ upstream, pkgs }:
upstream.overrideAttrs (old: {
  patches = (old.patches or [ ]) ++ [
    ./patches/session-routing.patch
    ./patches/manual-model-routing.patch
    ./patches/model-variants.patch
    ./patches/session-attention.patch
    ./patches/question-location.patch
  ];
  postPatch = (old.postPatch or "") + ''
    cp ${./plugins/model-routing/model-routing.ts} packages/schema/src/local-model-routing.ts
    cp ${./plugins/model-routing/routing-models.json} packages/schema/src/routing-models.json
    cp ${./patches/session-attention.ts} packages/tui/src/session-attention.ts
  '';
  postInstall =
    (old.postInstall or "")
    + pkgs.lib.optionalString pkgs.stdenv.isLinux ''
      wrapProgram $out/bin/opencode \
        --prefix LD_LIBRARY_PATH : ${
          pkgs.lib.makeLibraryPath [
            pkgs.stdenv.cc.cc.lib
            pkgs.alsa-lib
            pkgs.libpulseaudio
          ]
        }
    '';
})
