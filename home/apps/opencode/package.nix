{ upstream, pkgs }:
assert pkgs.lib.assertMsg
  (upstream.version == "2.4.0" || pkgs.lib.hasPrefix "2.4.0+" upstream.version)
  ''
    OpenCode's local patches target upstream v2.4.0.
    Use the separate opencode input and its own nixpkgs; review patches and tests
    before changing the pinned release, not the shared nixpkgs-unstable input.
  '';
upstream.overrideAttrs (old: {
  # Upstream #65824 corrects stale v2.4.0 hashes without dependency/recipe changes.
  # Linux matches the user's failed build; Darwin is from the upstream bot run.
  # Remove this override once the pinned upstream provides these corrected hashes.
  node_modules = old.node_modules.override {
    hash =
      {
        x86_64-linux = "sha256-sdMjb/l8SIthDbBJO3VzpyoOL9auoFGjVb6HdlxkQGg=";
        aarch64-darwin = "sha256-3d3c6tnTD/fTefdrxUACkLLqKeXDDijLg2cp3yhz67Q=";
      }
      .${pkgs.stdenv.hostPlatform.system};
  };
  # Preserve the upstream prod channel and the existing TUI/service namespace.
  env = (old.env or { }) // {
    OPENCODE_CHANNEL = "prod";
  };
  patches = (old.patches or [ ]) ++ [
    ./patches/session-routing.patch
    ./patches/manual-model-routing.patch
    ./patches/model-variants.patch
    ./patches/session-attention.patch
    ./patches/question-location.patch
    # 2.3.0 already includes the theme-cache priority fix. Keep the original
    # patch and regression controls until native PTY/live acceptance is recorded.
  ];
  postPatch = (old.postPatch or "") + ''
    cp ${./plugins/model-routing/model-routing.ts} packages/schema/src/local-model-routing.ts
    cp ${./plugins/model-routing/routing-models.json} packages/schema/src/routing-models.json
    cp ${./patches/session-attention.ts} packages/tui/src/session-attention.ts
  '';
  postInstall =
    (old.postInstall or "")
    + pkgs.lib.optionalString pkgs.stdenv.hostPlatform.isLinux ''
      wrapProgram $out/bin/opencode \
        --prefix LD_LIBRARY_PATH : ${
          pkgs.lib.makeLibraryPath [
            # Upstream already wraps Wayland/PATH. Add the original local
            # native-module/audio dependencies from that same nixpkgs pin.
            pkgs.stdenv.cc.cc.lib
            pkgs.alsa-lib
            pkgs.libpulseaudio
          ]
        }
    '';
})
