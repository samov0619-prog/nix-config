{ pkgs, ... }:
{
  # Neither pinned stable 1.6.6 nor unstable 1.6.9 includes this upstream fix.
  # Keep the stable ABI and clients; change only Lenovo's service package.
  # On updates, run test_pipewire_x11.py --check-upstream before removing it.
  services.pipewire.package = pkgs.pipewire.overrideAttrs (old: {
    patches = (old.patches or [ ]) ++ [ ./pipewire-x11-idempotent.patch ];
  });
}
