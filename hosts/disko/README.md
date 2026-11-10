# Disko Installation

Disko is destructive only when its command is explicitly run. A normal
`nixos-rebuild switch --flake .#<host>` never partitions or formats disks.

## Remote VPS

Run the read-only preflight locally from the workstation checkout against the
candidate Linux or rescue host. It needs only `ip` and `lsblk`; all parsing,
interactive prompts, and the write to external `~/.config/nix-config/server/settings.nix` happen
on the workstation:

```bash
nix shell nixpkgs#jq nixpkgs#openssh --command \
  sh hosts/server/preflight.sh vps-bootstrap
```

First build the server and Disko closures with the external input as described
in `SERVER_AI_INSTRUCTIONS.md`, obtaining `$disko_script` and `$nixos_system`.
Use the documented `--out-link` paths under `~/.local/state/nix-config/deploy/server/`
so both results remain GC-rooted until installation succeeds; do not use
`--no-link` for this pair. Remove the links only after successful final boot.
Keep settings unchanged between verification and deployment. `hosts/server/settings.nix`
is an example only; the default input refuses server/installer evaluation.

Try the NixOS installer bootstrap first. This phase does not partition or
format the target disk:

```bash
nix run github:nix-community/nixos-anywhere -- \
  --store-paths "$disko_script" "$nixos_system" --phases kexec root@<vps-ip>
```

If kexec fails, build the settings-based provider ISO, upload local `result` in
the provider panel, and boot the VPS from it:

```bash
nix build --override-input server-settings "path:$HOME/.config/nix-config/server" .#nixosConfigurations.server-installer.config.system.build.isoImage
```

Once the target is running a NixOS installer, use the destructive phases:

```bash
nix run github:nix-community/nixos-anywhere -- \
  --store-paths "$disko_script" "$nixos_system" --phases disko,install,reboot root@<vps-ip>
```

`root@<vps-ip>` is SSH syntax for the temporary Linux or NixOS installer host.
See `SERVER_AI_INSTRUCTIONS.md` for identity checks and the complete provider
ISO workflow.

## Local Laptop Or Desktop

Boot a NixOS installer USB on the target machine. No IP address and no SSH are
required, though the user may operate the live system over SSH. Lenovo now uses
`laptop`; Acer is `laptop-old` and does not import Disko. Run from the reviewed
repository checkout, not from the Acer profile. First complete the
[Lenovo checklist](../../docs/laptop-audit/lenovo-checklist.md), update/review the
inputs (Lenovo's deliberate guard was removed after review on 11.11.2026).
Resolve live-store capacity/build placement first. Recheck the target disk against model,
capacity and mounts immediately before the explicitly approved destructive step.
The configured Lenovo path is a live-observed PCI topology path, not a disk serial.

The commands below still require **explicit destructive-stage consent and the
storage-aware installation plan**; passing evaluation is not permission to run them.
`--inputs-from .` resolves `disko` from this checkout's updated lock instead of
selecting an independent upstream revision; `--no-write-lock-file` prevents a
silent lock change during this installation step.

```fish
sudo nix --extra-experimental-features "nix-command flakes" run --inputs-from . --no-write-lock-file disko -- \
  --mode destroy,format,mount ./hosts/laptop/disko.nix
sudo nixos-install --flake .#laptop
```

For a future desktop, complete `hosts/desktop-next/disko.nix` first and replace
`laptop` with `desktop-next`. `destroy,format,mount` erases the selected
disk completely.
