{
  upstream,
  polkit,
  python3,
}:
upstream.overrideAttrs (old: {
  patches = (old.patches or [ ]) ++ [ ./notification-timeout.patch ];
  buildInputs = (old.buildInputs or [ ]) ++ [ polkit ];
  configureFlags = (old.configureFlags or [ ]) ++ [ "--enable-polkit" ];

  # Upstream configure silently disables support if pkg-config cannot find Polkit,
  # even with --enable-polkit. Check the result, without running the root helper.
  doInstallCheck = true;
  installCheckPhase = ''
    runHook preInstallCheck
    ${python3}/bin/python3 ${./verify.py} --package "$out" --source "$PWD"
    ${python3}/bin/python3 ${./tests/test_notification_timeout.py} "$PWD" --check-upstream
    runHook postInstallCheck
  '';
})
