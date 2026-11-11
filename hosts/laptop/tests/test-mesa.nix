# Narrow Mesa/userspace declaration regression; no builds, IFD, ELF/GPU checks.
# nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/tests/test-mesa.nix
let
  flake = builtins.getFlake (toString ../../..);
  target = flake.nixosConfigurations.laptop;
  cfg = target.config.hardware.graphics;
  stable = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
in
assert cfg.enable;
assert cfg.enable32Bit;
assert cfg.package.drvPath == stable.mesa.drvPath;
assert cfg.package32.drvPath == stable.pkgsi686Linux.mesa.drvPath;
# Mesa is loaded into host applications, not isolated in its own libc process.
assert cfg.package.stdenv.cc.libc.drvPath == target.pkgs.stdenv.cc.libc.drvPath;
assert cfg.package32.stdenv.cc.libc.drvPath == target.pkgs.pkgsi686Linux.stdenv.cc.libc.drvPath;
{
  mesa64 = cfg.package.version;
  mesa32 = cfg.package32.version;
  mesaLibc64 = cfg.package.stdenv.cc.libc.version;
  mesaLibc32 = cfg.package32.stdenv.cc.libc.version;
  mesaMatchesStableUserspaceLibc = true;
}
