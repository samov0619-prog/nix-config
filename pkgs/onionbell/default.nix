{
  lib,
  rustPlatform,
  fetchFromGitHub,
  pkg-config,
  alsa-lib,
  sound-theme-freedesktop,
}:
rustPlatform.buildRustPackage {
  pname = "onionbell";
  version = "0.2.0";

  src = fetchFromGitHub {
    owner = "onion108";
    repo = "onionbell";
    rev = "1bd6d6f7527c213452b8da4b3be3074cc0c06841";
    hash = "sha256-dBY5qc+/q7HrJc9OiYMRkrDjwOWkWAd+dZDbJDEy5kk=";
  };

  cargoHash = "sha256-FBvNs6dv6COSOKIA+cpwJXyYTSgwxr+SFHDvwqFbM2M=";

  nativeBuildInputs = [ pkg-config ];
  buildInputs = [ alsa-lib ];

  # Rodio 0.21 drops Vorbis clips whose initial decoded span is empty. Decode
  # short bell clips to PCM first; exercise the real configured sound in tests.
  patches = [ ./ogg-first-span.patch ];
  env.ONIONBELL_TEST_SOUND = "${sound-theme-freedesktop}/share/sounds/freedesktop/stereo/bell.oga";

  # Current Hyprland omits this client field. Retain compatibility with older
  # JSON while allowing the current schema (otherwise every bell logs a warning).
  postPatch = ''
    substituteInPlace src/hypr.rs \
      --replace-fail '    pub pseudo: bool,' '    #[serde(default)]
        pub pseudo: bool,'
  '';

  meta = {
    description = "System bell player for Hyprland";
    homepage = "https://github.com/onion108/onionbell";
    license = lib.licenses.wtfpl;
    platforms = lib.platforms.linux;
    mainProgram = "onionbell";
  };
}
