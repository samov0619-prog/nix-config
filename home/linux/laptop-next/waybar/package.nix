{ waybar }:
waybar.overrideAttrs (old: {
  patches = (old.patches or [ ]) ++ [ ./power-profile-tooltip.patch ];
  postPatch = (old.postPatch or "") + ''
    cp ${./power-profile-cycle.hpp} src/modules/power-profile-cycle.hpp
  '';
})
