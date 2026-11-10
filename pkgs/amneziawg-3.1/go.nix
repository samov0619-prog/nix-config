{ amneziawg-go, fetchFromGitHub }:
# Shared with the installed Amnezia 5.0.1.5 client and the live installer helper.
amneziawg-go.overrideAttrs (
  finalAttrs: _: {
    version = "3.1.20260814";

    src = fetchFromGitHub {
      owner = "amnezia-vpn";
      repo = "amneziawg-go";
      tag = "v${finalAttrs.version}";
      hash = "sha256-HMmbKd1wYzotB+GAZ8GulyJmX7+XUnXOEerab0OCPO8=";
    };

    vendorHash = "sha256-Y2dCwlKMVLrkzDcNKyCPxFJwMbCA2mQKkakvzwbamCY=";
  }
)
