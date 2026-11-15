{ pkgs, ... }:
{
  # Neither pinned stable 1.6.6 nor unstable 1.6.9 includes this upstream fix.
  # Keep the stable ABI and clients; change only Lenovo's service package.
  # On updates, run test_pipewire_x11.py --check-upstream before removing it.
  services.pipewire.package = pkgs.pipewire.overrideAttrs (old: {
    patches = (old.patches or [ ]) ++ [ ./pipewire-x11-idempotent.patch ];
  });

  # Prefer the built-in input unless the user saves a different default.
  # Leave output selection to stock priorities and pwvucontrol; keep HFP manual.
  services.pipewire.wireplumber.extraConfig."60-lenovo-audio-defaults" = {
    "wireplumber.settings"."bluetooth.autoswitch-to-headset-profile" = false;
    "monitor.alsa.rules" = [
      {
        matches = [
          {
            "node.name" = "alsa_input.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__Mic1__source";
          }
        ];
        actions.update-props."priority.session" = 2500;
      }
    ];
  };
}
