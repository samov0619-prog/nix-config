# Disko Installation

Disko is destructive only when its command is explicitly run. A normal
`nixos-rebuild switch --flake .#<host>` never partitions or formats disks.

## Remote VPS

Boot the provider rescue system, confirm the target disk with `lsblk`, set
`hosts/server/settings.nix`, then run from this repository on another machine:

```bash
nix run github:nix-community/nixos-anywhere -- \
  --flake .#server root@<vps-ip>
```

`root@<vps-ip>` is SSH syntax for the remote rescue machine. It is needed only
because the command is controlling a different computer.

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
