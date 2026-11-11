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

On 10 November 2026, the user successfully built and switched Acer's NixOS
`laptop-old` and standalone HM `samov-laptop-old`, then confirmed normal operation.
The installed verifier's help lists `laptop-old`. Read-only agent checks confirmed
the current system is the `laptop-old` closure and `/etc/hostname` is `laptop-old`.
The old transient hostname initially remained `laptop`; after the suggested
`sudo hostnamectl --transient set-hostname laptop-old`, the user confirmed success.
Reboot and suspend/hibernate have not been rechecked for this rename. This is not
acceptance of Lenovo's uninstalled configuration or compatibility after an input update.

Review confirmed Acer's hardware scan and three HM files are byte-identical to
their pre-rename versions; its NixOS module changes only the hostname. Earlier
role/declaration/graphics/mDNS checks and targeted source-path tests passed;
verifier/settings tests ran 13 cases with 3 skips and mocked build/update calls.
The separate Blueman declaration evaluation timed out after 25 seconds, so the
following voice declaration evaluation was not reached. No further builds were
run by the agent. Python syntax and laptop-related documentation links were checked.
Git's whitespace check flags three pre-existing trailing-space lines in the
byte-preserved Acer Hyprland file; they were not rewritten. Prettier/Ruff/Beautysh
were unavailable, so no replacement formatter was used for Markdown/Python.

1. Review `flake.nix`, the moved leaves and the selected SSD in `hosts/laptop/disko.nix`.
2. Run the lightweight ownership/composition check, without building closures:
   `nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/profiles/tests/test-laptop-roles.nix`.
   It covers selected declarations, not full builds or live boot/resume.
3. For a fresh installation, use the current [Lenovo guide](../../hosts/laptop/README.md).
   The original full-input update is historical, not a mandatory new update each time.
4. Acer activation is complete; do not repeat it just for Lenovo preparation.
   Future Acer applications after personal review use
   `sudo nixos-rebuild switch --flake .#laptop-old` and separately
   `home-manager switch --flake .#samov-laptop-old`.
5. Lenovo installation and later standalone HM use `laptop` / `samov-laptop` only
   on Lenovo. Its guard was removed after review and installation is complete;
   do not rerun destructive setup for this rename. Documentation needs no activation.
