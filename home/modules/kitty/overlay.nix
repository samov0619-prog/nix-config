# Keep all HM Kitty consumers on the same fixed package, including launch helpers.
_final: prev:
prev.lib.optionalAttrs prev.stdenv.isLinux {
  kitty = prev.kitty.overrideAttrs (old: {
    patches = (old.patches or [ ]) ++ [ ./auto-theme-background-images.patch ];
  });
}
