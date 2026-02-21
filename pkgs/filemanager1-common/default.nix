{
  lib,
  stdenv,
  fetchFromGitHub,
  meson,
  ninja,
  pkg-config,
  dbus,
  systemd,
  glib,
}:

stdenv.mkDerivation {
  pname = "filemanager1-common";
  version = "unstable-2026-02-04";

  src = fetchFromGitHub {
    owner = "boydaihungst";
    repo = "org.freedesktop.FileManager1.common";
    rev = "900fccc13dc57e45b527b9acace47ea79c0d9c01";
    hash = "sha256-FCmNqz8JaP6XUaJOoWw5Lfls3ThdY+Yv2kRdk8XIRic=";
  };

  nativeBuildInputs = [
    meson
    ninja
    pkg-config
  ];

  buildInputs = [
    dbus
    systemd
    glib
  ];

  mesonFlags = [
    "-Dsystemd=enabled"
  ];

  # Patch wrapper scripts to use Nix store paths
  postPatch = ''
    for wrapper in config/*-wrapper.sh; do
      echo "Patching $wrapper"

      substituteInPlace "$wrapper" \
        --replace-fail "/usr/bin/" ""

      substituteInPlace "$wrapper" \
        --replace 'eval "$termcmd -- ' 'eval "$termcmd ' || true

      chmod +x "$wrapper"
    done
  '';

  meta = with lib; {
    description = "D-Bus service implementing org.freedesktop.FileManager1 interface";
    longDescription = ''
      A D-Bus service that allows applications (especially browsers) to open
      file managers and highlight specific files using the FreeDesktop
      FileManager1 interface specification.

      Supports terminal file managers like yazi, ranger, nnn, and lf.
    '';
    homepage = "https://github.com/boydaihungst/org.freedesktop.FileManager1.common";
    license = licenses.mit;
    maintainers = [ ];
    platforms = platforms.linux;
    mainProgram = "file_manager_dbus";
  };
}
