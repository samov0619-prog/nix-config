# Disko Installation

Disko is destructive only when its command is explicitly run. A normal
`nixos-rebuild switch --flake .#<host>` never partitions or formats disks.

## Remote VPS

Run the read-only preflight locally from the workstation checkout against the
candidate Linux or rescue host. It needs only `ip` and `lsblk`; all parsing,
interactive prompts, and the write to local `hosts/server/settings.nix` happen
on the workstation:

```bash
nix shell nixpkgs#jq nixpkgs#openssh --command \
  sh hosts/server/preflight.sh vps-bootstrap
```

Try the NixOS installer bootstrap first. This phase does not partition or
format the target disk:

```bash
nix run github:nix-community/nixos-anywhere -- \
  --flake .#server --phases kexec root@<vps-ip>
```

If kexec fails, build the settings-based provider ISO, upload local `result` in
the provider panel, and boot the VPS from it:

```bash
nix build .#nixosConfigurations.server-installer.config.system.build.isoImage
```

Once the target is running a NixOS installer, use the destructive phases:

```bash
nix run github:nix-community/nixos-anywhere -- \
  --flake .#server --phases disko,install,reboot root@<vps-ip>
```

`root@<vps-ip>` is SSH syntax for the temporary Linux or NixOS installer host.
See `SERVER_AI_INSTRUCTIONS.md` for identity checks and the complete provider
ISO workflow.

## Local Laptop Or Desktop

Boot a NixOS installer USB on the target machine. No IP address and no SSH are
needed: run these commands locally in the installer after replacing every
`REPLACE_ME` in the target Disko module.

```bash
sudo nix run github:nix-community/disko -- \
  --mode destroy,format,mount ./hosts/laptop-next/disko.nix
sudo nixos-install --flake .#laptop-next
```

For a future desktop, complete `hosts/desktop-next/disko.nix` first and replace
`laptop-next` with `desktop-next`. `destroy,format,mount` erases the selected
disk completely.
