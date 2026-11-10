# Laptop names: Acer and Lenovo

The repository now assigns the names as agreed:

| Machine | NixOS output / hostname | Home Manager output | Source directories |
| --- | --- | --- | --- |
| Acer | `laptop-old` | `samov-laptop-old` | `hosts/laptop-old`, `home/linux/laptop-old` |
| Lenovo | `laptop` | `samov-laptop` | `hosts/laptop`, `home/linux/laptop` |

`laptop-next` and `samov-laptop-next` are removed, not compatibility aliases.
Historical audit records keep the names used at the time. Current Acer commands
use `laptop-old`; do not apply either Lenovo output on Acer.

## What changes and what does not

- Acer's hardware scan, root/swap UUID, resume offset, NVIDIA policy, xremap,
  stateVersion 25.11 and three-generation retention are preserved. Its hostname
  declaration becomes `laptop-old`; source edits do not change the running host.
- Lenovo keeps its separate hardware scan, fresh stateVersion 26.05, PRIME offload,
  ext4/48 GiB swap and ten-generation retention. Disko targets the live-observed
  UMIS NVMe topology path. Recheck identity immediately before wiping.
- The verifier and Fish completion accept `laptop-old`; `laptop` now selects Lenovo.
  An already installed verifier does not update until HM is applied. For this
  migration, use explicit reviewed commands rather than an old installed helper.
- Lenovo's install guard remains. No lock update, build, activation or partitioning
  is performed by this rename. Do not rebuild Acer merely to make the names agree.

## Verification and application

1. Review `flake.nix`, the moved leaves and the selected SSD in `hosts/laptop/disko.nix`.
2. Run the lightweight ownership/composition check, without building closures:
   `nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/profiles/test-laptop-roles.nix`.
   It covers selected declarations, not full builds or live boot/resume.
3. Continue the [Lenovo installation checklist](lenovo-checklist.md): full input
   update, compatibility review and the final Lenovo builds remain separate steps.
4. Acer does not need activation for Lenovo preparation. If its hostname/profile
   is later to be applied after personal review, use
   `sudo nixos-rebuild switch --flake .#laptop-old` and separately
   `home-manager switch --flake .#samov-laptop-old`. Do not run these just for this check.
5. Lenovo installation and later standalone HM use `laptop` / `samov-laptop` only
   on Lenovo, after its guard is resolved. Documentation changes need no activation.
