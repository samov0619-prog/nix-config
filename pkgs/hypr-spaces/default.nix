{
  stdenv,
  hyprland,
  meson,
  ninja,
  pkg-config,
}:
stdenv.mkDerivation {
  pname = "hypr-spaces";
  version = "0.0.0";
  src = ./.;

  nativeBuildInputs = hyprland.nativeBuildInputs ++ [
    meson
    ninja
    pkg-config
  ];
  buildInputs = hyprland.buildInputs ++ [ hyprland ];
  dontUseCmakeConfigure = true;
  doCheck = true;

  meta = {
    description = "Live workspace canvas plugin for Hyprland";
    platforms = [ "x86_64-linux" ];
  };
}
