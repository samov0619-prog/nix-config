{
  python3,
  mako,
  writeShellScriptBin,
}:
writeShellScriptBin "notification-close" ''
  exec ${python3}/bin/python3 ${./close.py} --makoctl ${mako}/bin/makoctl "$@"
''
