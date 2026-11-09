{
  lib,
  ardour,
  dconf,
  python3,
  symlinkJoin,
  writeShellScript,
}:
let
  major = lib.versions.major ardour.version;
  command = ardour.meta.mainProgram;
  launcher = writeShellScript command ''
    exec ${python3}/bin/python3 ${./launch.py} \
      --major ${lib.escapeShellArg major} \
      --dconf ${dconf}/bin/dconf \
      -- ${ardour}/bin/${command} "$@"
  '';
in
symlinkJoin {
  name = "ardour-system-theme-${ardour.version}";
  paths = [ ardour ];
  postBuild = ''
    rm "$out/bin/${command}"
    ln -s ${launcher} "$out/bin/${command}"
    # Do not edit a symlink into the upstream package's immutable desktop file.
    rm "$out/share/applications/${command}.desktop"
    cp ${ardour}/share/applications/${command}.desktop "$out/share/applications/${command}.desktop"
    substituteInPlace "$out/share/applications/${command}.desktop" \
      --replace-fail 'Exec=${command}' "Exec=$out/bin/${command}"
  '';
  meta = ardour.meta;
  passthru = {
    unwrapped = ardour;
    inherit major launcher;
  };
}
