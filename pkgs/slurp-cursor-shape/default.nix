{ upstream, python3 }:
upstream.overrideAttrs (old: {
  # Released 1.5.0 has the cursor-shape code but never binds its global.
  # Removal contract and retained scenarios: README.md and the backport registry.
  patches = (old.patches or [ ]) ++ [ ./cursor-shape.patch ];

  doInstallCheck = true;
  installCheckPhase = ''
    runHook preInstallCheck
    # Meson's setup hook leaves PWD in source/build, not the source root.
    ${python3}/bin/python3 ${./tests/test_cursor_shape.py} "$NIX_BUILD_TOP/$sourceRoot" --check-upstream
    runHook postInstallCheck
  '';
})
